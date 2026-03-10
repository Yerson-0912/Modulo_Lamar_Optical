# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.exceptions import AccessError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def check(self, mode, values=None):
        if mode in ("read", "write", "unlink") and not self.env.is_superuser():
            target_attachments = self.filtered(
                lambda attachment: attachment.res_model == "x_employee_hourly_schedule_line" and attachment.res_id
            )
            bypass_attachments = self.env["ir.attachment"]

            manager_attachments = self.filtered(
                lambda attachment: attachment.res_model == "x_employee_hourly_schedule_line"
            )
            if manager_attachments and self.env.user.has_group("hr.group_hr_manager"):
                bypass_attachments |= manager_attachments

            owner_attachments = self.filtered(
                lambda attachment: attachment.res_model == "x_employee_hourly_schedule_line"
                and attachment.create_uid.id == self.env.uid
            )
            if owner_attachments:
                bypass_attachments |= owner_attachments

            if target_attachments:
                line_model = self.env["x_employee_hourly_schedule_line"]
                line_ids = list(set(target_attachments.mapped("res_id")))
                accessible_line_ids = set()

                for line in line_model.browse(line_ids).exists():
                    try:
                        line.check_access_rights("read")
                        line.check_access_rule("read")
                        accessible_line_ids.add(line.id)
                    except AccessError:
                        continue

                bypass_line_attachments = target_attachments.filtered(
                    lambda attachment: attachment.res_id in accessible_line_ids
                )
                if bypass_line_attachments:
                    bypass_attachments |= bypass_line_attachments

            if bypass_attachments:
                return super(IrAttachment, self - bypass_attachments).check(mode, values=values)

        return super().check(mode, values=values)

    @api.model_create_multi
    def create(self, vals_list):
        context = self.env.context
        default_res_model = context.get("default_res_model")
        default_res_id = context.get("default_res_id")

        if default_res_model == "x_employee_hourly_schedule_line" and default_res_id:
            line = self.env["x_employee_hourly_schedule_line"].browse(default_res_id)
            company_id = line.company_id.id if line.exists() and line.company_id else False

            normalized_vals_list = []
            for vals in vals_list:
                vals = dict(vals)
                if not vals.get("res_model"):
                    vals["res_model"] = default_res_model
                if not vals.get("res_id"):
                    vals["res_id"] = default_res_id
                if company_id and not vals.get("company_id"):
                    vals["company_id"] = company_id
                normalized_vals_list.append(vals)
            vals_list = normalized_vals_list

        return super().create(vals_list)
