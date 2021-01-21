# -*- coding: utf-8 -*-
import logging
from odoo import api, models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class account_journal(models.Model):
    _inherit = "account.journal"
    _description = "Checkbox for Pay Later"

    is_pay_later = fields.Boolean('Is Pay Later', default = False)

    @api.model
    def create(self, vals):
        """ Create New Records """
        company_id = vals.get('company_id') or self.company_id.id
        account_ids = self.search([('company_id', '=', company_id)]) # load the journal of self.company
        for account in account_ids:
            if account.is_pay_later and vals.get('is_pay_later') is True:
                raise UserError(_('Pay Later is already selected for another journal. You cannot use it for multiple journals.'))
        res = super(account_journal, self).create(vals)
        return res

    # @api.multi
    def write(self, vals):
        """ Update Records """

        company_id = vals.get('company_id') or self.company_id.id 
        account_ids = self.search([('company_id', '=', company_id)]) # load the journal of self.company
        for account in account_ids:
            if account.is_pay_later and vals.get('is_pay_later') is True:
                raise UserError(_('Pay Later is already selected for another journal. You cannot use it for multiple journals.'))
        res = super(account_journal, self).write(vals)
        return res


class Skit_PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def fetch_partner_order(self, customer, session_id):
        """ Serialize the orders of the customer

        params: customer int representing the customer id
        """
        params = {'partner_id': customer}
        # Generate Order Details
        sql_query = """ select  x.order_id, x.date_order, x.type  from (
                        select id as order_id,date_order,'POS'as type
                        from pos_order
                        where partner_id = %(partner_id)s
                        )
                        as x order by x.date_order desc"""

        self._cr.execute(sql_query, params)
        rows = self._cr.dictfetchall()
        datas = self.get_order_datas(rows, session_id)
        idatas = self.get_pending_invoice(customer, session_id)

        result = {'orders': datas, 'pendinginvoice': idatas}
        return result

    @api.model
    def get_order_orderlines(self, rec_order_id):
        """ Order Reprint Receipt"""
        discount = 0
        result = []
        order_id = self.search([('id', '=', rec_order_id)], limit=1)
        lines = self.env['pos.order.line'].search([('order_id', '=',
                                                    order_id.id)])
        payments = self.env['pos.payment'].search([
                            ('pos_order_id', '=', order_id.id)], order="id desc", limit=1)
        payment_lines = []
        orders = []
        for order in order_id:
            order_detail = {
                            'pos_reference': order.pos_reference,
                            'amount_total': order.amount_total,
                            'amount_tax': order.amount_tax,
                            'id': order.id,
                            'name': order.name,
                            'customer': order.partner_id.name,
                            'mobile': order.partner_id.mobile or ''
                            }
            orders.append(order_detail)
        change = 0
        for i in payments:
            if i.amount > 0 and i.payment_method_id.is_pay_later is False:
                temp = {
                    'amount': i.amount,
                    'name': i.payment_method_id.name,
                    'payment_date': i.payment_date
                }
                payment_lines.append(temp)
            else:
                change += i.amount
        bal = 0
        for j in payments:
            if j.amount > 0 and j.payment_method_id.is_pay_later is False:
                bal += j.amount
        for line in lines:
            new_vals = {
                'product_id': line.product_id.name,
                'qty': line.qty,
                'price_unit': line.price_unit,
                'discount': line.discount,
                }
            discount += (line.price_unit * line.qty * line.discount) / 100
            result.append(new_vals)
        balance = order.amount_total - bal

        return [result, discount, payment_lines, orders, change, balance]

    @api.model
    def get_order_datas(self, rows, session_id):
        """ Serialize all orders of the devotee

        params: rows - list of orders
        """
        datas = []
        sno = 0
        pos_ids = [x['order_id'] for x in rows if x['type'] == "POS"]
        porders = self.env['pos.order'].search([('id', 'in', pos_ids)])
        allorders = {'POS': porders}
        for key, orders in allorders.items():
            for order in orders:
                sno = sno + 1
                dateorder = False
                invoices = self.env['account.move'].search([
                                        ('id', 'in', order.account_move.ids)])
                dateorder = fields.Date.from_string(order.date_order)
                session_id = order.session_id.id
                if dateorder:
                    dateorder = dateorder.strftime("%Y/%m/%d")
                else:
                    dateorder = ''
                if invoices:
                    for invoice in invoices:
                        datas.append({
                                'id': order.id,
                                'sno': sno,
                                'type': key,
                                'invoice_ref': invoice.name,
                                'invoice_id': invoice.id,
                                'amount_total': round(order.amount_total, 2),
                                'date_order': dateorder,
                                'name': order.name or '',
                                'session_id': session_id})
                else:
                    datas.append({'id': order.id,
                                  'sno': sno,
                                  'type': key,
                                  'invoice_ref': '',
                                  'invoice_id': '',
                                  'amount_total': round(order.amount_total, 2),
                                  'date_order': dateorder,
                                  'name': order.name or '',
                                  'session_id': session_id})
        return datas

    @api.model
    def get_pending_invoice(self, partner_id, session_id):
        """ Fetch the pending invoice for current user
        params: partner - current user
        """
        idatas = []

        p_invoice = self.env['account.move'].search(
                            [('partner_id', '=', partner_id),
                             ('type', 'not in', ('in_invoice', 'in_refund')),
                             ('state', '=', 'posted')])
        isno = 0
        paid_amount = 0
        for invoice in p_invoice:
            isno = isno + 1
            posorder = self.env['pos.order'].search([
                                ('account_move', '=', invoice.id)])
            type = 'POS'
            paid_amount1 = 0
            paid_amount2 = 0
            if posorder:
                if posorder.payment_ids:
                    paid_amount1 = sum([x.amount for x in posorder.payment_ids if not x.payment_method_id.is_pay_later])
                paid_amount = paid_amount1
                #To avoid return orders in pending invoice
                if(paid_amount < 0):
                    paid_amount = -(paid_amount)
                dateinvoice = fields.Date.from_string(invoice.invoice_date)
                diff = (invoice.amount_total - paid_amount)
                amt = round(diff, 2)
                if diff == 0:
                    amt = 0
                idatas.append({'id': invoice.id,
                               'sno': isno,
                               'type': type,
                               'porder_id': posorder.id or '',
                               'name': invoice.invoice_origin or '',
                               'invoice_ref': invoice.name,
                               'amount_total': round(invoice.amount_total, 2),
                               'unpaid_amount': amt if amt > 0 else '',
                               'date_invoice': dateinvoice.strftime("%Y/%m/%d")
                               })
        return idatas

    def calculate_paidamt(self, invoice):
        residual = 0.0
        residual_company_signed = 0.0
        paid_amt = 0.0
        # sign = invoice.type in ['in_refund', 'out_refund'] and -1 or 1
        for line in invoice.sudo().line_ids:
                residual_company_signed += line.amount_residual
                if line.currency_id == invoice.currency_id:
                    residual += line.amount_residual_currency if line.currency_id else line.amount_residual
                else:
                    from_currency = (line.currency_id and line.currency_id.with_context(date=line.date)) or line.company_id.currency_id.with_context(date=line.date)
                    residual += from_currency.compute(line.amount_residual, invoice.currency_id)
#         self.residual_company_signed = abs(residual_company_signed) * sign
#         self.residual_signed = abs(residual) * sign
        paid_amt = invoice.amount_total - abs(residual)
        return paid_amt

    @api.model
    def fetch_invoice_lines(self, invoice_id):
        """ Serialize the invoice Lines
        params: devotee int representing the invoice id
        """
        invoice = self.env['account.move'].browse(int(invoice_id))
        iLines = invoice.invoice_line_ids
        line = []
        sno = 0
        for iLine in iLines:
            sno = sno + 1
            line.append({
                'sno': sno,
                'id': iLine.id,
                'product': iLine.product_id.name,
                'qty': iLine.quantity,
                'price_unit': iLine.price_unit,
                'amount': iLine.price_subtotal
            })
        return line
    
    
    def action_pos_order_invoice(self):
        #Selvi TO check this super call is correct
        super(Skit_PosOrder, self).action_pos_order_invoice()
        # Added By Sandhi To Mark the "Receivable" Move Line of Invoices as "PayLater" to 
        #avoid auto reconciliation during Close Session
        for order in self:
            for move_line in order.account_move.line_ids.filtered(lambda aml: aml.account_id.internal_type == 'receivable'):
                paylater_amt = 0.0                
                for payment in order.payment_ids:
                    if payment.payment_method_id.is_pay_later:
                        move_line.write({'is_pay_later': True})
                        paylater_amt += payment.amount
                        
                    move_line.write({'paylater_amt': paylater_amt})
                
            
            
        

class Skit_AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_pay_later = fields.Boolean('IsPaylater', default=False)
    paylater_amt = fields.Float(string='PayLater Amt', digits='Product Price')
  #  order_id = fields.Many2one('pos.order', string='Order Ref', ondelete='cascade')

class Skit_AccountMove(models.Model):
    _inherit = 'account.move'

    is_pending_invoice = fields.Boolean('Current Invoice', default=False)   

    def _compute_amount(self):
        super(Skit_AccountMove, self)._compute_amount()
        invoice_ids = [move.id for move in self if move.id and move.is_invoice(include_receipts=True)]
        self.env['account.payment'].flush(['state'])
        if invoice_ids:
            self._cr.execute(
                '''
                    SELECT move.id
                    FROM account_move move
                    JOIN account_move_line line ON line.move_id = move.id
                    JOIN account_partial_reconcile part ON part.debit_move_id = line.id OR part.credit_move_id = line.id
                    JOIN account_move_line rec_line ON
                        (rec_line.id = part.credit_move_id AND line.id = part.debit_move_id)
                        OR
                        (rec_line.id = part.debit_move_id AND line.id = part.credit_move_id)
                    JOIN account_payment payment ON payment.id = rec_line.payment_id
                    JOIN account_journal journal ON journal.id = rec_line.journal_id
                    WHERE payment.state IN ('posted', 'sent')
                    AND journal.post_at = 'bank_rec'
                    AND move.id IN %s
                ''', [tuple(invoice_ids)]
            )
            in_payment_set = set(res[0] for res in self._cr.fetchall())
        else:
            in_payment_set = {}
        for move in self:
            currencies = set()
            for line in move.line_ids:
                if line.currency_id:
                    currencies.add(line.currency_id)
            currency = len(currencies) == 1 and currencies.pop() or move.company_id.currency_id
            is_paid = currency and currency.is_zero(move.amount_residual) or not move.amount_residual

            # Compute 'invoice_payment_state'.
            if move.state == 'posted' and is_paid:
                if move.id in in_payment_set:
                    move.invoice_payment_state = 'in_payment'
                else:
                    move.invoice_payment_state = 'paid'
            else:
                move.invoice_payment_state = 'not_paid'

    @api.model
    def get_pending_invoice_details(self, invoice_id, payment_lines,
                                    pos_session):
        """ Get Invoice Details and payment process """
        for pl in payment_lines:
            invoice = self.browse(int(invoice_id))
            order = self.env['pos.order'].search([
                ('account_move', '=', invoice.id)])
            amount = (pl['amount'] - pl['change'])
            payment_method_id = pl['paymethod']['id']
            session = self.env['pos.session'].browse(int(pos_session))
            """  add payment methods for POS order under Payment tab
                create pos.payment  """
            current_date = fields.Date.from_string(fields.Date.today())
            args = {
                            'amount': amount,
                            'payment_date': current_date,
                            'name': pl['name'] + ': ',
                            'pos_order_id': order.id,
                            'payment_method_id': payment_method_id,
                            'pos_session_id': session.id,
                    }
            order.add_payment(args)
            invoice.update({'is_pending_invoice': True})
        return True


class PoSPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    is_pay_later = fields.Boolean(
        string='Is Pay Later',
        default=False)

    @api.model
    def create(self, vals):
        """ Create New Records """
        payment_method_ids = self.search([]) # load the journal of self.company
        for payment in payment_method_ids:
            if payment.is_pay_later and vals.get('is_pay_later') is True:
                raise UserError(_('Pay Later is already selected for another Payment Method. You cannot use it for multiple payment methods.'))
        journal = self.env['account.journal'].search([('is_pay_later', '=', True)])
        if not journal:
            paylater_journal = self.env['account.journal'].create({'name': 'Pay Later',
                            'is_pay_later': True,
                            'default_credit_account_id': vals.get('receivable_account_id'),
                            'default_debit_account_id': vals.get('receivable_account_id'),
                            'code': 'PL',
                            'type': 'bank'})
        res = super(PoSPaymentMethod, self).create(vals)
        return res

    # @api.multi
    def write(self, vals):
        """ Update Records """

        payment_method_ids = self.search([])
        for payment in payment_method_ids:
            if payment.is_pay_later and vals.get('is_pay_later') is True:
                raise UserError(_('Pay Later is already selected for another Payment Method. You cannot use it for multiple payment methods.'))
        journal = self.env['account.journal'].search([('is_pay_later', '=', True)])
        if not journal:
            paylater_journal = self.env['account.journal'].create({'name': 'Pay Later',
                            'is_pay_later': True,
                            'default_credit_account_id': self.receivable_account_id.id,
                            'default_debit_account_id': self.receivable_account_id.id,
                            'code': 'PL',
                            'type': 'bank'})
        res = super(PoSPaymentMethod, self).write(vals)
        return res


class PoSPayment(models.Model):
    _inherit = 'pos.payment'

    pos_session_id = fields.Many2one(
        'pos.session', string='POS Session')
    is_pay_later = fields.Boolean(string='Is Pay Later',related='payment_method_id.is_pay_later', readonly=True)
    
