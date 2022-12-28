from odoo import fields, models


class TaxSummaryReport(models.TransientModel):
    _name = 'tax.summary.report.wizard'
    _description = 'Tax Summary Report'
    
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    is_government = fields.Boolean('Government')
    is_private = fields.Boolean('is private')
    partner_ids = fields.Many2many('res.partner', string='Customer', domain=[('is_government', '=', True)])
    
    def generate_report(self):
        """
        The only report that generate PDF
        :return:
        """
        data = {'date_start': self.start_date, 'date_stop': self.end_date, 'is_government': self.is_government,
                'is_private': self.is_private,
                'partner_ids': self.partner_ids.ids}
        return self.env.ref('telenoc_tax_report.tax_summary').report_action([], data=data)
    
    def export_sales_xls(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'is_government': self.is_government,
            'is_private': self.is_private,
            'partner_ids': self.partner_ids.ids,
            'is_sales': True
        }
        return self.env.ref("telenoc_tax_report.action_sales_tax_details_report_xls").with_context(
            datas=data).report_action(self)
    
    def export_purchase_xls(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'is_sales': False
        }
        return self.env.ref("telenoc_tax_report.action_purchase_tax_details_report_xls").with_context(
            datas=data).report_action(self)

