# -*- coding: utf-8 -*-
import base64
import io

from odoo import models, _


class PurchaseTaxReport(models.AbstractModel):
	_name = 'report.telenoc_tax_report.purchase_tax_details_report_xls'
	_inherit = 'report.report_xlsx.abstract'
	_description = 'Purchase Tax Details XLS Report'
	
	def generate_xlsx_report(self, workbook, data, wizard):
		data = self.env.context.get('datas')
		moves_worksheet = workbook.add_worksheet(_("Purchase Tax Details"))
		header_format = workbook.add_format({
			'bold': True,
			'align': 'center',
			'font_color': 'white',
			'bg_color': '#0099CC',
			'font_size': 12,
			'font_name': 'Calibri',
			'valign': 'vcenter',
			'text_wrap': True,
		})
		
		moves_worksheet = self.set_worksheet_column_sizes(moves_worksheet,
		                                                  {'A': 7, 'B': 30, 'C': 20, 'D': 20, 'E': 20, 'F': 25,
		                                                   'G': 30, 'H': 20, 'I': 20, 'J': 20})
		
		center_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
		date_format = workbook.add_format({'num_format': 'dd/mm/yyyy', 'align': 'center', 'valign': 'vcenter'})
		date_gray_format = workbook.add_format(
			{'num_format': 'dd/mm/yyyy', 'align': 'center', 'valign': 'vcenter', 'bg_color': '#eeeeee'})
		center_gray_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'bg_color': '#eeeeee'})
		left_format = workbook.add_format({'align': 'left', 'valign': 'vcenter'})
		left_gray_format = workbook.add_format({'align': 'left', 'valign': 'vcenter', 'bg_color': '#eeeeee'})
		banner_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
		payments_and_taxes_banner_format = workbook.add_format({'align': 'center', 'valign': 'vcenter'})
		payments_and_taxes_banner_format.set_font_size(20)
		# TODO: A.SALAMA ===> Adding Company Logo
		company_logo = self.env.user.company_id.logo
		if company_logo:
			imgdata = base64.b64decode(company_logo)
			image = io.BytesIO(imgdata)
			moves_worksheet.insert_image('A1:B3', 'company_logo.png',
			                             {'image_data': image, 'x_scale': 1.9, 'y_scale': 0.9})
		moves_worksheet.merge_range('C1:H4', "%s\n%s\n%s - %s" % (
			self.env.user.company_id.name,
			_("Purchase Tax Details"),
			data['start_date'],
			data['end_date'],
		
		), banner_format)
		
		row = 6
		
		row += 2
		
		moves_worksheet.write_row(row, 0, [_('Seq'), _('Vendor'), _('VAT'), _('Journal'), _('Bill'), _('Date'),
		                                   _('TAX'), _('Branch'),
		                                   _('TAX Amount'), _('Amount')], header_format)
		row += 1
		res = self.env['report.telenoc_tax_report.tax_details_report'].get_purchase_account_move_line(
			date_start=data['start_date'],
			date_stop=data['end_date'], )
		
		if res:
			for seq, line in enumerate(res.get('purchase_tax')):
				moves_worksheet.write(row, 0, seq + 1, center_format if (seq % 2) == 0 else center_gray_format)
				moves_worksheet.write(row, 1, line.get('partner_name', ''),
				                      left_format if (seq % 2) == 0 else left_gray_format)
				moves_worksheet.write(row, 2, line.get('vat', ''),
				                      center_format if (seq % 2) == 0 else center_gray_format)
				moves_worksheet.write(row, 3, line.get('journal_name', ''),
				                      center_format if (seq % 2) == 0 else center_gray_format)
				moves_worksheet.write(row, 4, line.get('invoice_num', ''),
				                      center_format if (seq % 2) == 0 else center_gray_format)
				moves_worksheet.write(row, 5, line.get('date', ''),
				                      date_format if (seq % 2) == 0 else date_gray_format)
				moves_worksheet.write(row, 6, line.get('tax_name', ''),
				                      center_format if (seq % 2) == 0 else center_gray_format)
				moves_worksheet.write(row, 7, line.get('branch_name', ''),
				                      center_format if (seq % 2) == 0 else center_gray_format)
				moves_worksheet.write_number(row, 8, line.get('tax_amount', ''),
				                             center_format if (seq % 2) == 0 else center_gray_format)
				moves_worksheet.write_number(row, 9, line.get('tax_base_amount', ''),
				                             center_format if (seq % 2) == 0 else center_gray_format)
				row += 1
		
		workbook.close()
	
	def set_worksheet_column_sizes(self, worksheet, data):
		for column_name, size in data.items():
			worksheet.set_column('%s:%s' % (column_name, column_name), size)
		
		return worksheet
		