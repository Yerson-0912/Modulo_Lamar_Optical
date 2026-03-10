# -*- coding: utf-8 -*-
"""
Asistente para duplicar planes semanales a múltiples periodos.

Desarrollador:
- Nombre: Yerson Vargas Vargas
- Teléfono: 3122919236
- Correo: yervargas@gmail.com
"""

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class EmployeeScheduleDuplicateWizard(models.TransientModel):
    """Wizard de UI para duplicar un plan base durante varias semanas."""

    _name = 'x_employee_schedule_duplicate_wizard'
    _description = 'Asistente para Duplicar Horarios'

    schedule_id = fields.Many2one(
        'x_employee_hourly_schedule',
        string='Horario a Duplicar',
        required=True,
        readonly=True
    )
    employee_name = fields.Char(
        related='schedule_id.employee_id.name',
        string='Empleado',
        readonly=True
    )
    original_date = fields.Date(
        related='schedule_id.date',
        string='Fecha Original',
        readonly=True
    )
    num_weeks = fields.Integer(
        string='Número de Semanas',
        default=4,
        required=True,
        help='Número de semanas consecutivas a duplicar (máximo 52)'
    )
    skip_existing = fields.Boolean(
        string='Saltar si Ya Existe',
        default=True,
        help='No duplicar si ya existe un horario para esa fecha'
    )
    mark_as_recurrent = fields.Boolean(
        string='Marcar Copias como Recurrentes',
        default=True,
        help='Las copias también se marcarán como plantillas recurrentes'
    )

    @api.constrains('num_weeks')
    def _check_num_weeks(self):
        """Restringe el rango permitido de semanas a duplicar."""
        for wizard in self:
            if wizard.num_weeks < 1:
                raise UserError('Debe duplicar al menos 1 semana.')
            if wizard.num_weeks > 52:
                raise UserError('No puede duplicar más de 52 semanas (1 año).')

    def action_duplicate(self):
        """Ejecuta la duplicación y retorna notificación de resultado."""
        self.ensure_one()

        schedule_model = self.env['x_employee_hourly_schedule']
        created_count = 0
        skipped_count = 0

        for week_offset in range(1, self.num_weeks + 1):
            target_date = self.schedule_id.date + timedelta(days=7 * week_offset)
            existing = schedule_model.search([
                ('employee_id', '=', self.schedule_id.employee_id.id),
                ('date', '=', target_date),
            ], limit=1)

            if existing:
                skipped_count += 1
                if not self.skip_existing:
                    raise UserError(
                        f'Ya existe un horario para {self.schedule_id.employee_id.name} en {target_date}.'
                    )
                continue

            created = self.schedule_id._duplicate_schedule(weeks=week_offset, notify=False)
            if created:
                created_count += 1
                if not self.mark_as_recurrent:
                    created_schedule = schedule_model.search([
                        ('employee_id', '=', self.schedule_id.employee_id.id),
                        ('date', '=', target_date),
                    ], limit=1)
                    if created_schedule:
                        created_schedule.write({'is_recurrent': False})

        message_parts = []
        if created_count > 0:
            message_parts.append(f'{created_count} horario(s) creado(s)')
        if skipped_count > 0:
            message_parts.append(f'{skipped_count} omitido(s) (ya existían)')

        message = ' | '.join(message_parts) if message_parts else 'No se crearon horarios'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '¡Duplicación Completada!',
                'message': message,
                'type': 'success' if created_count > 0 else 'info',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
