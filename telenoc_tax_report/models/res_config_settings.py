from odoo import models, fields, api
from ast import literal_eval


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    start_date = fields.Date('Tax Report Start Date', help='')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            start_date=self.env['ir.config_parameter'].sudo().get_param(
                'telenoc_tax_report.start_date'),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()
        start_date = self.start_date and self.start_date or False
        param.set_param('telenoc_tax_report.start_date', start_date)
