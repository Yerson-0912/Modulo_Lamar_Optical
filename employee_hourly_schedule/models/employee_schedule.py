# -*- coding: utf-8 -*-
"""
Planeación Operativa - Employee Hourly Schedule Models

Modelos para gestión de actividades y horarios por empleado.
Incluye control de estados, cálculo de horas, recurrencia semanal
y soporte de integración con proyectos/tareas.

Desarrollador:
- Nombre: Yerson Vargas Vargas
- Teléfono: 3122919236
- Correo: yervargas@gmail.com

@module employee_hourly_schedule
@version 17.0.1.0.1
@license LGPL-3
"""

from datetime import timedelta
import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_time


_logger = logging.getLogger(__name__)


class EmployeeHourlySchedule(models.Model):
    """Cabecera del plan diario por empleado.

    Representa un día de trabajo para un empleado y agrupa sus
    actividades horarias (líneas).
    """

    _name = "x_employee_hourly_schedule"
    _description = "Planeación Operativa"
    _order = "date desc, employee_id"

    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        required=True,
        ondelete="cascade",
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Departamento",
        related="employee_id.department_id",
        store=True,
        readonly=True,
    )
    job_id = fields.Many2one(
        "hr.job",
        string="Puesto de Trabajo",
        related="employee_id.job_id",
        store=True,
        readonly=True,
    )
    date = fields.Date(
        string="Fecha",
        required=True,
        default=fields.Date.context_today,
    )
    line_ids = fields.One2many(
        "x_employee_hourly_schedule_line",
        "schedule_id",
        string="Horas",
    )
    name = fields.Char(
        string="Nombre",
        compute="_compute_name",
        store=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        related="employee_id.company_id",
        store=True,
        readonly=True,
    )
    is_recurrent = fields.Boolean(
        string="Plantilla Semanal Recurrente",
        default=False,
        help="Si está marcado, este horario se replicará automáticamente cada semana",
    )

    _sql_constraints = [
        (
            "employee_date_unique",
            "unique(employee_id, date)",
            "Solo se permite un plan por empleado y fecha.",
        )
    ]

    @api.depends("employee_id", "date")
    def _compute_name(self):
        """Construye el nombre visible del plan: Empleado - Fecha."""
        for record in self:
            if record.employee_id and record.date:
                record.name = f"{record.employee_id.name} - {record.date}"
            else:
                record.name = False

    def action_duplicate_to_next_week(self):
        """Acción UI: duplica el plan actual a la próxima semana."""
        self.ensure_one()
        return self._duplicate_schedule(weeks=1)

    def action_duplicate_to_multiple_weeks(self):
        """Acción UI: abre asistente para duplicación a múltiples semanas."""
        self.ensure_one()
        return {
            "name": "Duplicar a Varias Semanas",
            "type": "ir.actions.act_window",
            "res_model": "x_employee_schedule_duplicate_wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_schedule_id": self.id},
        }

    def toggle_done(self):
        """Marca/desmarca todas las líneas del plan como completadas."""
        for schedule in self:
            lines = schedule.line_ids
            if not lines:
                continue
            mark_done = any(not line.is_done for line in lines)
            lines.write({"is_done": mark_done, "state": "done" if mark_done else "in_progress"})

    def _build_line_commands(self, days_delta):
        """Genera comandos one2many para replicar líneas desplazando fechas."""
        self.ensure_one()
        commands = [(5, 0, 0)]
        for source_line in self.line_ids:
            line_vals = source_line.copy_data({
                "start_datetime": source_line.start_datetime + timedelta(days=days_delta),
                "end_datetime": source_line.end_datetime + timedelta(days=days_delta),
                "state": "pending",
                "is_done": False,
            })[0]
            line_vals.pop("schedule_id", None)
            commands.append((0, 0, line_vals))
        return commands

    def _duplicate_schedule(self, weeks=1, notify=True):
        """Duplica el plan hacia adelante por semanas.

        - Si existe destino y es sincronización recurrente, actualiza líneas.
        - Si existe destino y no es sincronización, evita duplicado.
        - Si no existe, crea un nuevo plan con sus líneas desplazadas.
        """
        self.ensure_one()
        new_date = self.date + timedelta(days=7 * weeks)
        existing = self.search([
            ("employee_id", "=", self.employee_id.id),
            ("date", "=", new_date),
        ], limit=1)

        if existing:
            if self.env.context.get("recurrent_sync") and self.is_recurrent:
                days_diff = (new_date - self.date).days
                existing.with_context(skip_recurrent_sync=True).write({
                    "line_ids": self._build_line_commands(days_diff),
                })
                return True

            if not notify:
                return False
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Advertencia",
                    "message": f"Ya existe un horario para {self.employee_id.name} en {new_date}. No se duplicó.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        new_schedule = self.copy({
            "date": new_date,
            "is_recurrent": self.is_recurrent,
            "line_ids": [(5, 0, 0)],
        })

        days_diff = (new_date - self.date).days
        new_schedule.with_context(skip_recurrent_sync=True).write({
            "line_ids": self._build_line_commands(days_diff),
        })

        if not notify:
            return True

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "¡Éxito!",
                "message": f"Horario duplicado para la semana del {new_date}",
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _get_current_week_equivalent_date(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        week_start = today - timedelta(days=today.weekday())
        return week_start + timedelta(days=self.date.weekday())

    def _get_or_create_schedule_for_date(self, target_date):
        self.ensure_one()
        target_schedule = self.search([
            ("employee_id", "=", self.employee_id.id),
            ("date", "=", target_date),
        ], limit=1)

        if target_schedule:
            return target_schedule

        target_schedule = self.copy({
            "date": target_date,
            "is_recurrent": self.is_recurrent,
            "line_ids": [(5, 0, 0)],
        })

        days_diff = (target_date - self.date).days
        target_schedule.with_context(skip_recurrent_sync=True).write({
            "line_ids": self._build_line_commands(days_diff),
        })
        return target_schedule

    def _should_redirect_recurrent_edit(self):
        self.ensure_one()
        if not self.is_recurrent or not self.date:
            return False
        today = fields.Date.context_today(self)
        week_start = today - timedelta(days=today.weekday())
        return self.date < week_start

    def _sync_recurrent_next_week(self):
        """Sincroniza una semana futura para planes marcados como recurrentes."""
        if self.env.context.get("skip_recurrent_sync"):
            return
        for schedule in self.filtered("is_recurrent"):
            schedule.with_context(
                skip_recurrent_redirect=True,
                recurrent_sync=True,
                skip_recurrent_sync=True,
            )._duplicate_schedule(weeks=1, notify=False)

    def _ensure_recurrent_future_weeks(self, weeks_ahead=4):
        """Garantiza que existan semanas futuras consecutivas para recurrencia."""
        if self.env.context.get("skip_recurrent_sync"):
            return
        for schedule in self.filtered("is_recurrent"):
            current_schedule = schedule
            for _index in range(weeks_ahead):
                next_date = current_schedule.date + timedelta(days=7)
                current_schedule.with_context(
                    skip_recurrent_redirect=True,
                    recurrent_sync=True,
                    skip_recurrent_sync=True,
                )._duplicate_schedule(weeks=1, notify=False)
                next_schedule = self.search([
                    ("employee_id", "=", current_schedule.employee_id.id),
                    ("date", "=", next_date),
                ], limit=1)
                if not next_schedule:
                    break
                current_schedule = next_schedule

    def _is_only_line_status_write(self, vals):
        if set(vals.keys()) != {"line_ids"}:
            return False

        commands = vals.get("line_ids") or []
        if not isinstance(commands, list) or not commands:
            return False

        for command in commands:
            if not isinstance(command, (list, tuple)) or len(command) < 1:
                return False

            op = command[0]
            if op != 1 or len(command) < 3:
                return False

            update_vals = command[2] or {}
            if not update_vals:
                return False

            if not set(update_vals.keys()).issubset({"is_done", "state"}):
                return False

        return True

    @api.model
    def cron_duplicate_recurrent_schedules(self):
        today = fields.Date.context_today(self)
        target_date = today + timedelta(days=7)

        recurrent_schedules = self.search([
            ("is_recurrent", "=", True),
            ("date", "<=", target_date),
        ])

        duplicated_count = 0
        for seed_schedule in recurrent_schedules:
            try:
                current_schedule = seed_schedule
                while current_schedule.date and current_schedule.date <= target_date:
                    next_date = current_schedule.date + timedelta(days=7)
                    next_schedule = self.search([
                        ("employee_id", "=", current_schedule.employee_id.id),
                        ("date", "=", next_date),
                    ], limit=1)
                    if next_schedule:
                        current_schedule = next_schedule
                        continue

                    duplicated = current_schedule._duplicate_schedule(weeks=1, notify=False)
                    if not duplicated:
                        break

                    duplicated_count += 1
                    current_schedule = self.search([
                        ("employee_id", "=", current_schedule.employee_id.id),
                        ("date", "=", next_date),
                    ], limit=1)
                    if not current_schedule:
                        break
            except Exception:
                _logger.exception("Error duplicando horario recurrente ID %s", seed_schedule.id)
                continue

        return duplicated_count

    @api.model_create_multi
    def create(self, vals_list):
        """Crea planes y ejecuta sincronización recurrente inicial."""
        records = super().create(vals_list)
        records._sync_recurrent_next_week()
        records.filtered("is_recurrent")._ensure_recurrent_future_weeks(weeks_ahead=4)
        return records

    def write(self, vals):
        """Escribe cambios en planes y gestiona redirección de recurrentes."""
        if self.env.context.get("skip_recurrent_redirect"):
            result = super().write(vals)
            self._sync_recurrent_next_week()
            if vals.get("is_recurrent"):
                self.filtered("is_recurrent")._ensure_recurrent_future_weeks(weeks_ahead=4)
            return result

        if self._is_only_line_status_write(vals):
            return super().write(vals)

        redirect_records = self.filtered(lambda schedule: schedule._should_redirect_recurrent_edit())
        direct_records = self - redirect_records
        redirected_targets = self.env["x_employee_hourly_schedule"]

        result = True
        if direct_records:
            result = super(EmployeeHourlySchedule, direct_records).write(vals)

        for schedule in redirect_records:
            target_date = schedule._get_current_week_equivalent_date()
            target_schedule = schedule._get_or_create_schedule_for_date(target_date)
            target_schedule.with_context(skip_recurrent_redirect=True).write(vals)
            redirected_targets |= target_schedule

        affected_records = direct_records | redirected_targets
        affected_records._sync_recurrent_next_week()
        if vals.get("is_recurrent"):
            affected_records.filtered("is_recurrent")._ensure_recurrent_future_weeks(weeks_ahead=4)
        return result

    def unlink(self):
        return super().unlink()


class EmployeeHourlyScheduleLine(models.Model):
    """Detalle de actividad horaria asociada a un plan diario."""

    _name = "x_employee_hourly_schedule_line"
    _description = "Actividad de Planeación Operativa"
    _order = "start_datetime"

    _DEFAULT_DAILY_LIMIT_HOURS = 8.0

    schedule_id = fields.Many2one(
        "x_employee_hourly_schedule",
        string="Plan",
        required=True,
        ondelete="cascade",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        string="Empleado",
        related="schedule_id.employee_id",
        store=True,
        readonly=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Departamento",
        related="employee_id.department_id",
        store=True,
        readonly=True,
    )
    job_id = fields.Many2one(
        "hr.job",
        string="Puesto de Trabajo",
        related="employee_id.job_id",
        store=True,
        readonly=True,
    )
    start_datetime = fields.Datetime(string="Inicio", required=True)
    end_datetime = fields.Datetime(string="Fin", required=True)
    activity_name = fields.Char(string="Actividad", required=True)
    name = fields.Char(string="Título", compute="_compute_name")
    state = fields.Selection(
        [("pending", "Pendiente"), ("in_progress", "En Progreso"), ("done", "Completado")],
        string="Estado",
        default="pending",
        required=True,
    )
    calendar_color = fields.Integer(string="Color Calendario", compute="_compute_calendar_color", store=False)
    duration_hours = fields.Float(string="Duración (Horas)", compute="_compute_duration_hours", store=True)
    time_range = fields.Char(string="Rango Horario", compute="_compute_time_range")
    daily_total_hours = fields.Float(string="Total Diario (Horas)", compute="_compute_daily_total_hours", store=True)
    is_overloaded = fields.Boolean(string="Alerta de Sobrecarga", compute="_compute_is_overloaded", store=True)
    is_done = fields.Boolean(string="Hecho")
    date = fields.Date(string="Día", compute="_compute_date", store=True)
    project_id = fields.Many2one("project.project", string="Proyecto")
    task_id = fields.Many2one("project.task", string="Tarea")
    note = fields.Text(string="Notas", help="Notas sobre la actividad realizada")
    activity_photo = fields.Image(
        string="📸 Foto Principal",
        max_width=1024,
        max_height=1024,
        help="Foto principal de la actividad",
    )
    attachment_count = fields.Integer(
        string="📷 Fotos Adjuntas",
        compute="_compute_attachment_count",
        help="Cantidad de fotos adjuntas a esta tarea",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        related="schedule_id.company_id",
        store=True,
        readonly=True,
    )

    @api.constrains("start_datetime", "end_datetime")
    def _check_datetime_order(self):
        """Valida que la hora final sea posterior a la inicial."""
        for line in self:
            if line.start_datetime and line.end_datetime and line.start_datetime >= line.end_datetime:
                raise ValidationError("La hora de fin debe ser posterior a la hora de inicio.")

    @api.depends("start_datetime")
    def _compute_date(self):
        for line in self:
            line.date = fields.Date.to_date(line.start_datetime) if line.start_datetime else False

    @api.depends("employee_id", "activity_name", "start_datetime", "end_datetime", "is_done")
    @api.depends_context("tz")
    def _compute_name(self):
        for line in self:
            parts = []
            if line.start_datetime and line.end_datetime:
                tz = self.env.context.get("tz") or self.env.user.tz
                start_str = format_time(self.env, line.start_datetime, time_format=None, tz=tz, lang_code=self.env.lang)
                end_str = format_time(self.env, line.end_datetime, time_format=None, tz=tz, lang_code=self.env.lang)
                parts.append(f"{start_str}-{end_str}")
            if line.employee_id:
                parts.append(line.employee_id.name)
            if line.activity_name:
                parts.append(line.activity_name)
            name = " - ".join(parts) if parts else False
            line.name = f"✓ {name}" if line.is_done and name else name

    @api.depends("start_datetime", "end_datetime")
    def _compute_duration_hours(self):
        for line in self:
            if line.start_datetime and line.end_datetime:
                delta = line.end_datetime - line.start_datetime
                line.duration_hours = delta.total_seconds() / 3600.0
            else:
                line.duration_hours = 0.0

    @api.depends("start_datetime", "end_datetime")
    @api.depends_context("tz")
    def _compute_time_range(self):
        for line in self:
            if line.start_datetime and line.end_datetime:
                tz = self.env.context.get("tz") or self.env.user.tz
                start_str = format_time(self.env, line.start_datetime, time_format=None, tz=tz, lang_code=self.env.lang)
                end_str = format_time(self.env, line.end_datetime, time_format=None, tz=tz, lang_code=self.env.lang)
                line.time_range = f"{start_str}-{end_str}"
            else:
                line.time_range = False

    @api.depends("employee_id", "date", "duration_hours")
    def _compute_daily_total_hours(self):
        for line in self:
            line.daily_total_hours = 0.0
        lines = self.filtered(lambda l: l.employee_id and l.date)
        if not lines:
            return
        employee_ids = lines.employee_id.ids
        dates = list({d for d in lines.mapped("date") if d})
        if not employee_ids or not dates:
            return
        grouped = self.read_group(
            [("employee_id", "in", employee_ids), ("date", "in", dates)],
            ["duration_hours:sum"],
            ["employee_id", "date"],
        )
        totals = {}
        for item in grouped:
            employee = item.get("employee_id")
            if not employee:
                continue
            date_value = item.get("date")
            if date_value is None:
                for key, value in item.items():
                    if key.startswith("date"):
                        date_value = value
                        break
            if date_value is None:
                continue
            totals[(employee[0], date_value)] = item.get("duration_hours", 0.0)
        for line in lines:
            line.daily_total_hours = totals.get((line.employee_id.id, line.date), 0.0)

    @api.depends("daily_total_hours")
    def _compute_is_overloaded(self):
        limit_hours = self._DEFAULT_DAILY_LIMIT_HOURS
        for line in self:
            line.is_overloaded = line.daily_total_hours > limit_hours

    @api.depends("is_done", "state")
    def _compute_calendar_color(self):
        for line in self:
            line.calendar_color = 1 if line.is_done or line.state == "done" else 0

    def toggle_done(self):
        """Alterna estado completado en una línea y sincroniza state."""
        for record in self:
            record.is_done = not record.is_done
            if record.is_done and record.state != "done":
                record.state = "done"
            elif not record.is_done and record.state == "done":
                record.state = "in_progress"

    def _compute_attachment_count(self):
        for line in self:
            attachments = self.env["ir.attachment"].search([
                ("res_model", "=", "x_employee_hourly_schedule_line"),
                ("res_id", "=", line.id),
            ])
            line.attachment_count = len(attachments)

    def action_attachment_open(self):
        self.ensure_one()
        return {
            "name": "📷 Fotos de la Actividad",
            "type": "ir.actions.act_window",
            "res_model": "ir.attachment",
            "view_mode": "tree,form",
            "view_id": False,
            "domain": [
                ("res_model", "=", "x_employee_hourly_schedule_line"),
                ("res_id", "=", self.id),
            ],
            "context": {
                "default_res_model": "x_employee_hourly_schedule_line",
                "default_res_id": self.id,
                "create": True,
            },
        }

    def action_duplicate_assigned_task(self):
        self.ensure_one()
        duplicated_line = self.copy({"is_done": False, "state": "pending"})
        return {
            "type": "ir.actions.act_window",
            "name": "Actividad Duplicada",
            "res_model": "x_employee_hourly_schedule_line",
            "view_mode": "form",
            "res_id": duplicated_line.id,
            "target": "current",
        }

    def _sync_recurrent_next_week(self):
        if self.env.context.get("skip_recurrent_sync"):
            return
        schedules = self.mapped("schedule_id").filtered("is_recurrent")
        for schedule in schedules:
            schedule.with_context(
                skip_recurrent_redirect=True,
                recurrent_sync=True,
                skip_recurrent_sync=True,
            )._duplicate_schedule(weeks=1, notify=False)

    @api.model_create_multi
    def create(self, vals_list):
        """Crea líneas normalizando plan, estado inicial y recurrencia."""
        today = fields.Date.context_today(self)
        week_start = today - timedelta(days=today.weekday())
        default_schedule_id = self.env.context.get("default_schedule_id")
        if not default_schedule_id and self.env.context.get("active_model") == "x_employee_hourly_schedule":
            default_schedule_id = self.env.context.get("active_id")

        normalized_vals_list = []
        for vals in vals_list:
            vals = dict(vals)
            if not vals.get("schedule_id") and default_schedule_id:
                vals["schedule_id"] = default_schedule_id
            if not vals.get("schedule_id"):
                raise ValidationError("Debe seleccionar un Plan antes de guardar la actividad.")
            schedule_id = vals.get("schedule_id")
            if schedule_id:
                schedule = self.env["x_employee_hourly_schedule"].browse(schedule_id)
                if schedule.exists() and schedule.is_recurrent and schedule.date and schedule.date < week_start:
                    target_date = schedule._get_current_week_equivalent_date()
                    target_schedule = schedule._get_or_create_schedule_for_date(target_date)
                    vals["schedule_id"] = target_schedule.id

            if vals.get("is_done") and not vals.get("state"):
                vals["state"] = "done"
            normalized_vals_list.append(vals)

        records = super().create(normalized_vals_list)
        if not self.env.context.get("skip_recurrent_sync"):
            records._sync_recurrent_next_week()
        return records

    def write(self, vals):
        """Actualiza líneas sincronizando estado lógico y recurrencia."""
        if self.env.context.get("skip_recurrent_sync"):
            return super().write(vals)

        only_status_update = set(vals.keys()).issubset({"is_done", "state"})

        if "is_done" in vals and "state" not in vals:
            if vals.get("is_done"):
                vals = dict(vals, state="done")
                res = super().write(vals)
                if not only_status_update:
                    self._sync_recurrent_next_week()
                return res

            res = super().write(vals)
            self.filtered(lambda r: not r.is_done and r.state == "done").write({"state": "in_progress"})
            if not only_status_update:
                self._sync_recurrent_next_week()
            return res

        res = super().write(vals)
        if not only_status_update:
            self._sync_recurrent_next_week()
        return res

    def unlink(self):
        if self.env.context.get("skip_recurrent_sync"):
            return super().unlink()
        schedules = self.mapped("schedule_id")
        res = super().unlink()
        schedules.filtered("is_recurrent").with_context(
            skip_recurrent_redirect=True,
            recurrent_sync=True,
            skip_recurrent_sync=True,
        )._duplicate_schedule(weeks=1, notify=False)
        return res
