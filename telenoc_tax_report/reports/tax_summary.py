from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)
grey = "\x1b[38;21m"
yellow = "\x1b[33;21m"
red = "\x1b[31;21m"
bold_red = "\x1b[31;1m"
reset = "\x1b[0m"
green = "\x1b[32m"
blue = "\x1b[34m"


class TaxSummaryReport(models.AbstractModel):
    _name = 'report.telenoc_tax_report.tax_summary_report'
    _description = 'Tax Summary Report'

    @api.model
    def get_account_move_line(self, date_start=False, date_stop=False, is_gov=False, is_private=False,
                              partner_ids=False):
        tax_moves = {}
        gov_start_date = self.env['ir.config_parameter'].sudo().get_param(
            'telenoc_tax_report.start_date', default=False)
        sales_tax_ids = self.env['account.tax'].search([('type_tax_use', '=', 'sale')])
        purchase_tax_ids = self.env['account.tax'].search([('type_tax_use', '=', 'purchase')])
        branch_ids = self.env['res.branch'].search([])
        tax_moves.setdefault('sales_tax', [])
        tax_moves.setdefault('purchase_tax', [])
        tax_moves.setdefault('branches', [])
        tax_moves.setdefault('branch_total_sales_tax', [])
        tax_moves.setdefault('branch_total_purchase_tax', [])
        tax_moves.setdefault('branch_total_due', [])
        if branch_ids:
            for branch in branch_ids:
                tax_moves['branches'].append(({
                    'name': branch.name,
                }))
        if sales_tax_ids:
            for tax_id in sales_tax_ids:
                branch_list = []
                total_net_sales = 0
                total_tax = 0

                if branch_ids:
                    for branch in branch_ids:
                        total_base_amount = 0
                        sales_moves = self.get_sales_account_move_line(gov_start_date, date_start, date_stop,
                                                                       partner_ids,
                                                                       branch.id, tax_id, is_gov, is_private)
                        if sales_moves and tax_id.amount > 0:
                            # الضريبة ليست صفرية
                            for move in sales_moves:
                                if move.debit > 0 and move.tax_base_amount > 0:
                                    #  في حالة الاشعار الدائن تكون الضريبة مدينة في المبيعات وتكون اشارة الرصيد موجبة
                                    #  لذلك نطرح الأساس بدل جمعه
                                    total_base_amount-= move.tax_base_amount
                                else:
                                    #  نجمع الصافي الذي على اساسه تم حساب الضريبة
                                    total_base_amount += move.tax_base_amount

                            total_tax_amount = round(sum(t.balance * -1 for t in sales_moves))
                            # ضربنا في سال 1 لان الضريبة تكون دائنة في حالة البيع ومدينة في حالة الاشعار الدائن
                            total_net_sales += total_base_amount
                        elif sales_moves and tax_id.amount == 0:  # الضريبة صفرية
                            total_base_amount = abs(round(sum(t.balance for t in sales_moves)))
                            total_net_sales += total_base_amount
                            total_tax_amount = 0
                        else:  # لا توجد قيود لهذه الضريبة
                            total_base_amount = 0
                            total_tax_amount = 0

                        branch_list.append({
                            'branch_name': branch.name,
                            'total_base_amount': round(total_base_amount),
                            'total_tax_amount': total_tax_amount,
                            'tax_id_amount': tax_id.amount
                        })

                        total_tax += total_tax_amount

                    tax_moves['sales_tax'].append(({
                        'tax_name': tax_id.description,
                        'branch': branch_list,
                        'total_net_sales': round(total_net_sales),
                        'total_tax': round(total_tax),
                    }))

            for branch_id in branch_ids:
                total_branch_base_amount = 0
                total_branch_tax_amount = 0
                for move in tax_moves['sales_tax']:
                    for line in move['branch']:
                        if branch_id.name == line['branch_name']:
                            total_branch_base_amount += line['total_base_amount']
                            total_branch_tax_amount += line['total_tax_amount']
                tax_moves['branch_total_sales_tax'].append({
                    'branch_id': branch_id.id,
                    'branch_name': branch_id.name,
                    'total_branch_base_amount': round(total_branch_base_amount),
                    'total_branch_tax_amount': round(total_branch_tax_amount)
                })
        if purchase_tax_ids:
            for tax_id in purchase_tax_ids:
                branch_list = []
                total_net_purchase = 0
                total_tax = 0
                if branch_ids:
                    for branch in branch_ids:
                        total_base_amount = 0
                        purchase_moves = self.get_purchase_account_move_line(date_start, date_stop, branch.id, tax_id)
                        if purchase_moves and tax_id.amount > 0:
                            for move in purchase_moves:
                                if move.credit > 0:
                                    total_base_amount += move.tax_base_amount * (-1)
                                else:
                                    total_base_amount += move.tax_base_amount
                            total_tax_amount = round(sum(t.balance for t in purchase_moves))
                        elif purchase_moves:
                            total_base_amount = round(sum(t.balance for t in purchase_moves))
                            if total_base_amount < 0:
                                total_base_amount = total_base_amount * -1
                            total_tax_amount = 0
                        else:
                            total_base_amount = 0
                            total_tax_amount = 0

                            # الضريبة تكون بالسالب اذا كان الاجمالي بالسالب
                        if total_base_amount < 0:
                            total_tax_amount = abs(total_tax_amount) * -1
                        else:
                            total_tax_amount = abs(total_tax_amount)

                        branch_list.append({
                            'branch_name': branch.name,
                            'total_base_amount': round(total_base_amount),
                            'total_tax_amount': total_tax_amount
                        })
                        total_net_purchase += total_base_amount
                        total_tax += abs(total_tax_amount)

                    tax_moves['purchase_tax'].append(({
                        'tax_name': tax_id.description,
                        'branch': branch_list,
                        'total_net_purchase': round(total_net_purchase),
                        'total_tax': round(total_tax),
                    }))
            for branch_id in branch_ids:
                total_branch_base_amount = 0
                total_branch_tax_amount = 0
                for move in tax_moves['purchase_tax']:
                    for line in move['branch']:
                        if branch_id.name == line['branch_name']:
                            total_branch_base_amount += line['total_base_amount']
                            total_branch_tax_amount += line['total_tax_amount']
                tax_moves['branch_total_purchase_tax'].append({
                    'branch_id': branch_id.id,
                    'branch_name': branch_id.name,
                    'total_branch_base_amount': round(total_branch_base_amount),
                    'total_branch_tax_amount': round(total_branch_tax_amount)
                })
            for branch_id in branch_ids:
                sale_amount = 0
                sale_tax = 0
                purchase_amount = 0
                purchase_tax = 0
                for sale_line in tax_moves['branch_total_sales_tax']:
                    if sale_line['branch_id'] == branch_id.id:
                        sale_amount = sale_line['total_branch_base_amount']
                        sale_tax = sale_line['total_branch_tax_amount']
                for purchase_line in tax_moves['branch_total_purchase_tax']:
                    if purchase_line['branch_id'] == branch_id.id:
                        purchase_amount = purchase_line['total_branch_base_amount']
                        purchase_tax = purchase_line['total_branch_tax_amount']
                due_amount = round(sale_amount - purchase_amount)
                due_tax = round(sale_tax - purchase_tax)
                tax_moves['branch_total_due'].append({
                    'branch_id': branch_id.id,
                    'branch_name': branch_id.name,
                    'due_amount': due_amount,
                    'due_tax': due_tax,
                })
        return tax_moves

    @api.model
    def get_sales_account_move_line(self, gov_date_start=False, date_start=False, date_stop=False, partner_ids=False,
                                    branch_id=False,
                                    tax_id=False, is_gov=False, is_private=False):

        sales_moves = False
        if is_gov:
            if not gov_date_start:
                raise ValidationError(
                    _('Please select (Tax Report Start Date) from accounting settings'))
            payment_ids = self.env['account.payment'].search(
                [('partner_type', '=', 'customer'), ('partner_id', 'in', partner_ids), ('state', '=', 'posted'),
                 ('date', '>=', date_start), ('date', '<=', date_stop)])
            move_ids = []
            if payment_ids:
                for payment_id in payment_ids:
                    move_ids += payment_id.reconciled_invoice_ids.ids
                if move_ids:
                    if branch_id:
                        sales_moves = self.env['account.move.line'].search([
                            ('date', '>=', gov_date_start),
                            ('date', '<=', date_stop),
                            ('tax_line_id', '=', tax_id.id),
                            ('parent_state', '=', 'posted'),
                            ('branch_id', '=', branch_id),
                            ('move_id', 'in', move_ids),
                        ], order='date')
                        if tax_id.amount == 0:
                            sales_moves = self.env['account.move.line'].search([
                                ('date', '>=', gov_date_start),
                                ('date', '<=', date_stop),
                                ('tax_ids', '=', tax_id.id),
                                ('parent_state', '=', 'posted'),
                                ('branch_id', '=', branch_id),
                                ('move_id', 'in', move_ids),
                            ], order='date')
                    else:
                        sales_moves = self.env['account.move.line'].search([
                            ('date', '>=', gov_date_start),
                            ('date', '<=', date_stop),
                            ('tax_line_id', '=', tax_id.id),
                            ('parent_state', '=', 'posted'),
                            ('move_id', 'in', move_ids),
                        ], order='date')
                        if tax_id.amount == 0:
                            sales_moves = self.env['account.move.line'].search([
                                ('date', '>=', gov_date_start),
                                ('date', '<=', date_stop),
                                ('tax_ids', '=', tax_id.id),
                                ('parent_state', '=', 'posted'),
                                ('move_id', 'in', move_ids),
                            ], order='date')

        elif is_private:
            if branch_id:
                sales_moves = self.env['account.move.line'].search([
                    ('partner_id.is_government', '=', False),
                    ('date', '>=', date_start),
                    ('date', '<=', date_stop),
                    ('tax_line_id', '=', tax_id.id),
                    ('parent_state', '=', 'posted'),
                    ('branch_id', '=', branch_id),
                ], order='date')
                if tax_id.amount == 0:
                    sales_moves = self.env['account.move.line'].search([
                        ('partner_id.is_government', '=', False),
                        ('date', '>=', date_start),
                        ('date', '<=', date_stop),
                        ('tax_ids', '=', tax_id.id),
                        ('parent_state', '=', 'posted'),
                        ('branch_id', '=', branch_id),
                    ], order='date')
            else:
                sales_moves = self.env['account.move.line'].search([
                    ('partner_id.is_government', '=', False),
                    ('date', '>=', date_start),
                    ('date', '<=', date_stop),
                    ('tax_line_id', '=', tax_id.id),
                    ('parent_state', '=', 'posted'),
                ], order='date')
                if tax_id.amount == 0:
                    sales_moves = self.env['account.move.line'].search([
                        ('partner_id.is_government', '=', False),
                        ('date', '>=', date_start),
                        ('date', '<=', date_stop),
                        ('tax_ids', '=', tax_id.id),
                        ('parent_state', '=', 'posted'),
                    ], order='date')
        else:
            if branch_id:
                sales_moves = self.env['account.move.line'].search([
                    ('date', '>=', date_start),
                    ('date', '<=', date_stop),
                    ('tax_line_id', '=', tax_id.id),
                    ('parent_state', '=', 'posted'),
                    ('branch_id', '=', branch_id),
                ], order='date')
                if tax_id.amount == 0:
                    sales_moves = self.env['account.move.line'].search([
                        ('date', '>=', date_start),
                        ('date', '<=', date_stop),
                        ('tax_ids', '=', tax_id.id),
                        ('parent_state', '=', 'posted'),
                        ('branch_id', '=', branch_id),
                    ], order='date')
            else:
                sales_moves = self.env['account.move.line'].search([
                    ('date', '>=', date_start),
                    ('date', '<=', date_stop),
                    ('tax_line_id', '=', tax_id.id),
                    ('parent_state', '=', 'posted'),
                ], order='date')
                if tax_id.amount == 0:
                    sales_moves = self.env['account.move.line'].search([
                        ('date', '>=', date_start),
                        ('date', '<=', date_stop),
                        ('tax_ids', '=', tax_id.id),
                        ('parent_state', '=', 'posted'),
                    ], order='date')
        return sales_moves

    @api.model
    def get_purchase_account_move_line(self, date_start=False, date_stop=False, branch_id=False,
                                       tax_id=False):
        if branch_id:
            purchase_moves = self.env['account.move.line'].search([
                ('date', '>=', date_start),
                ('date', '<=', date_stop),
                ('tax_line_id', '=', tax_id.id),
                ('parent_state', '=', 'posted'),
                ('branch_id', '=', branch_id),
            ], order='date')
            if tax_id.amount == 0:
                purchase_moves = self.env['account.move.line'].search([
                    ('date', '>=', date_start),
                    ('date', '<=', date_stop),
                    ('tax_ids', '=', tax_id.id),
                    ('parent_state', '=', 'posted'),
                    ('branch_id', '=', branch_id),
                ], order='date')
        else:
            purchase_moves = self.env['account.move.line'].search([
                ('date', '>=', date_start),
                ('date', '<=', date_stop),
                ('tax_line_id', '=', tax_id.id),
                ('journal_id.is_purchase', '=', False),
                ('parent_state', '=', 'posted'),
            ], order='date')
            if tax_id.amount == 0:
                purchase_moves = self.env['account.move.line'].search([
                    ('date', '>=', date_start),
                    ('date', '<=', date_stop),
                    ('tax_ids', '=', tax_id.id),
                    ('journal_id.is_purchase', '=', False),
                    ('parent_state', '=', 'posted'),
                ], order='date')

        return purchase_moves

    @api.model
    def _get_report_values(self, docids, data=None):
        data = dict(data or {})
        data.update(
            self.get_account_move_line(data['date_start'], data['date_stop'], data['is_government'], data['is_private'],
                                       data['partner_ids']))
        return data


class TaxDetailsReport(models.AbstractModel):
    _name = 'report.telenoc_tax_report.tax_details_report'
    _inherit = 'report.report_xlsx.abstract'
    _description = 'Tax Details Report'

    @api.model
    def get_sales_account_move_line(self, date_start=False, date_stop=False, is_gov=False, is_private=False,
                                    partner_ids=False):
        sales_tax_moves = {}
        sales_tax_ids = self.env['account.tax'].search([('type_tax_use', '=', 'sale')])
        sales_tax_moves.setdefault('sales_tax', [])
        gov_start_date = self.env['ir.config_parameter'].sudo().get_param(
            'telenoc_tax_report.start_date', default=False)
        if sales_tax_ids:
            for tax_id in sales_tax_ids:
                sales_moves = self.env['report.telenoc_tax_report.tax_summary_report'].get_sales_account_move_line(
                    gov_start_date, date_start, date_stop,
                    partner_ids,
                    False, tax_id, is_gov, is_private)

                if sales_moves:
                    for move in sales_moves:
                        price_total = 0
                        tax_base_amount = 0

                        if move.debit > 0:
                            # #  في حالة الاشعار الدائن تكون الضريبة مدينة في المبيعات وتكون اشارة الرصيد موجبة
                            # #  لذلك نجعل الضريبة والمبلغ المعتمدة عليه سالبا
                            price_total = abs(move.price_total) * -1
                            tax_base_amount = abs(move.tax_base_amount) * -1
                            _logger.info(blue + "tax_base_amount" + str(tax_base_amount) + reset)
                        else:
                            price_total = abs(move.price_total)
                            tax_base_amount = abs(move.tax_base_amount)
                            _logger.info(green + "tax_base_amount" + str(tax_base_amount) + reset)
                        #  في حالة الضريبة الصفرية يكون الاساس المبني عليه الضريبة هو  price_total  وتكون الضريبة صفر
                        if tax_id.amount == 0:
                            tax_base_amount=price_total
                            price_total=0

                        sales_tax_moves['sales_tax'].append(({
                            'partner_name': move.partner_id.name,
                            'vat': move.partner_id.vat,
                            'invoice_num': move.move_id.name,
                            'date': move.date,
                            'tax_name': tax_id.description,
                            'branch_name': move.branch_id.name,
                            'tax_amount': price_total,
                            'tax_base_amount': tax_base_amount,
                        }))

        return sales_tax_moves

    @api.model
    def get_purchase_account_move_line(self, date_start=False, date_stop=False):
        purchase_tax_moves = {}
        purchase_tax_ids = self.env['account.tax'].search([('type_tax_use', '=', 'purchase')])
        purchase_tax_moves.setdefault('purchase_tax', [])
        if purchase_tax_ids:
            for tax_id in purchase_tax_ids:
                purchase_moves = self.env['report.telenoc_tax_report.tax_summary_report'].get_purchase_account_move_line(
                    date_start, date_stop, False, tax_id)
                cash_purchase_moves = self.get_cash_purchase_account_move_line(date_start, date_stop, tax_id.id)
                if purchase_moves:
                    for move in purchase_moves:
                        if move.credit > 0 and move.tax_base_amount > 0:
                            #  في حالة الاشعار الدائن تكون الضريبة دائنة في المشتريات وتكون اشارة الرصيد سالبة
                            #  لذلك نجعل الضريبة والمبلغ المعتمدة عليه سالبين
                            price_total = move.price_total * -1
                            tax_base_amount = move.tax_base_amount * -1
                        else:
                            price_total = move.price_total
                            tax_base_amount = move.tax_base_amount

                        purchase_tax_moves['purchase_tax'].append(({
                            'partner_name': move.partner_id.name,
                            'vat': move.partner_id.vat,
                            'invoice_num': move.ref,
                            'journal_name': move.move_id.name,
                            'date': move.date,
                            'tax_name': tax_id.description,
                            'branch_name': move.branch_id.name,
                            'tax_amount': price_total,
                            'tax_base_amount':tax_base_amount,
                        }))
                if cash_purchase_moves:
                    for cash_move in cash_purchase_moves:

                        purchase_tax_moves['purchase_tax'].append(({
                            'partner_name': cash_move.vendor_name,
                            'vat': cash_move.vat_number,
                            'invoice_num': cash_move.invoice_number,
                            'journal_name': cash_move.move_id.name,
                            'date': cash_move.invoice_date,
                            'tax_name': tax_id.description,
                            'branch_name': cash_move.branch_id.name,
                            'tax_amount': cash_move.price_subtotal * (tax_id.amount / 100),
                            'tax_base_amount': cash_move.price_subtotal,
                        }))

        return purchase_tax_moves

    @api.model
    def get_cash_purchase_account_move_line(self, date_start=False, date_stop=False, tax_id=False):
        purchase_moves = self.env['account.move.line'].search([
            ('date', '>=', date_start),
            ('date', '<=', date_stop),
            ('tax_ids', '=', tax_id),
            ('journal_id.is_purchase', '=', True),
            ('parent_state', '=', 'posted'),
        ], order='date')
        return purchase_moves
