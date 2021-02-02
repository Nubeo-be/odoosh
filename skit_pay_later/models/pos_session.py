# -*- coding: utf-8 -*-
import pytz
from datetime import timedelta
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.tools import float_is_zero


class Skit_PosSession(models.Model):
    _inherit = 'pos.session'

    def _confirm_paylater_orders(self, pay_later_order,move,payment):
            """ Posting method for Pay later order while close session
            :param pay_later_order:order
             """
            for session in self:
                pay_order = pay_later_order.filtered(
                            lambda order: order.state in ['invoiced', 'done'])
            for order in pay_order:

                account_move_line = self.env['account.move.line'].with_context(check_move_validity=False)

                combile_vals = {
                    'move_id': move.id,
                    'move_name': move.name,
                    'ref': session.name,
                    'account_id': payment.payment_method_id.receivable_account_id.id,
                    'partner_id': self.env["res.partner"]._find_accounting_partner(payment.partner_id).id,
                    'name': '%s - %s' % (self.name, payment.payment_method_id.name),
                    'debit': payment.amount,
                    'credit': 0
                    }
                account_move_line.create(combile_vals)
                # mlines.reconcile()
                invoice_vals = {
                    'move_id': move.id,
                    'move_name': move.name,
                    'ref': self.name,
                    'account_id': pay_order.partner_id.property_account_receivable_id.id,
                    'name': 'From invoiced orders',
                    'credit': payment.amount,
                    'debit': 0
                    }
                # From Invoice order lines
                m_lines = account_move_line.create(invoice_vals)
                # order_move = self.env['account.move'].search([('id', '=', order.id)])
                invoice_line_receivable = self.env['account.move.line'].search([('move_id', '=', order.account_move.id),
                                                                                ('account_internal_type', '=', 'receivable')])
                # mlines.reconcile()
                ( m_lines
                  | invoice_line_receivable
                  ).reconcile()
                  
               

    def action_pos_session_close(self):
            # Close CashBox
            pos_payment_method = self.env['pos.payment.method'].search([('is_pay_later', '=', True)])
            pos_payment = self.env['pos.payment'].search(
                [('pos_session_id', '=', self.id), ('payment_method_id', '!=', pos_payment_method.id)]
            )
            # self.write({'order_ids': []})
            res = super(Skit_PosSession, self).action_pos_session_close()
            session_id = self.id
            account_move = self.env['account.move']
            move = account_move.create({
                                            'type': 'entry',
                                            'ref': self.name,
                                            # 'amount_total': payment.amount,
                                            'journal_id': self.config_id.journal_id.id,
                                             })
            for payment in pos_payment:
                if payment.session_id.id != session_id:
                    pay_later_order = self.env['pos.order'].search([
                            ('id', '=', int(payment.pos_order_id.id)),
                            ('session_id', '!=', session_id)])
                    self._confirm_paylater_orders(pay_later_order,move,payment)
            if move.line_ids:
                move.post()
                # Set the uninvoiced orders' state to 'done'
                #self.env['pos.order'].search([('session_id', '=', self.id), ('state', '=', 'paid')]).write({'state': 'done'})
            else:
                # The cash register needs to be confirmed for cash diffs
                # made thru cash in/out when sesion is in cash_control.
#                 if self.config_id.cash_control:
#                     self.cash_register_id.button_confirm_bank()
                move.unlink()
            return res

    @api.model
    def create(self, values):
        res = super(Skit_PosSession, self).create(values)
        statements = []
        ctx = dict(self.env.context, company_id=res.config_id.company_id.id)
        statement_ids = self.env['account.bank.statement']
        if self.user_has_groups('point_of_sale.group_pos_user'):
            statement_ids = statement_ids.sudo()
        payment_method_ids = self.env['account.journal'].search([('id','in',res.config_id.payment_method_ids.ids), ('is_pay_later', '=', True)])
        for journal in payment_method_ids :
            ctx['journal_id'] = journal.id if res.config_id.cash_control and journal.type == 'cash' else False
            st_values = {
                    'journal_id': journal.id,
                    'user_id': self.env.user.id,
                    'name': res.name
            }
            statement_ids |= statement_ids.with_context(ctx).create(st_values)

        payment_method_ids = self.env['account.journal'].search([('id','in',res.config_id.payment_method_ids.ids), ('is_pay_later', '=', False)])
        for journal in payment_method_ids:
                    # set the journal_id which should be used by
                    #  account.bank.statement to set the opening balance of the
                    #  newly created bank statement
            ctx['journal_id'] = journal.id if res.config_id.cash_control and journal.type == 'cash' else False
            st_values = {
                        'journal_id': journal.id,
                        'user_id': self.env.user.id,
                        'name': res.name
                }

            statement_ids |= statement_ids.with_context(ctx).create(st_values)

        values.update({
            'statement_ids': [(6, 0, statement_ids.ids)],
        })
        # res.write(values)

        return res

    def _get_split_receivable_vals(self, payment, amount, amount_converted):
        is_pay_later = False
        if payment.payment_method_id.is_pay_later:
            is_pay_later = True
        partial_vals = {
            'account_id': payment.payment_method_id.receivable_account_id.id,
            'move_id': self.move_id.id,
            'partner_id': self.env["res.partner"]._find_accounting_partner(payment.partner_id).id,
            'name': '%s - %s' % (self.name, payment.payment_method_id.name),
            'is_pay_later': is_pay_later
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_combine_receivable_vals(self, payment_method, amount, amount_converted):
        is_pay_later = False
        if payment_method.is_pay_later:
            is_pay_later = True
        partial_vals = {
            'account_id': payment_method.receivable_account_id.id,
            'move_id': self.move_id.id,
            'name': '%s - %s' % (self.name, payment_method.name),
            'is_pay_later': is_pay_later
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _create_account_move(self):
        """ Create account.move and account.move.line records for this session.

        Side-effects include:
            - setting self.move_id to the created account.move record
            - creating and validating account.bank.statement for cash payments
            - reconciling cash receivable lines, invoice receivable lines and stock output lines
        """
        journal = self.config_id.journal_id
        # Passing default_journal_id for the calculation of default currency of account move
        # See _get_default_currency in the account/account_move.py.
        account_move = self.env['account.move'].with_context(default_journal_id=journal.id).create({
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'ref': self.name,
        })
        self.write({'move_id': account_move.id})
        #<-- START Added BY SANDHI to create Pay Later Journal SELVI need to create a configuration field 
        #for paylater journal like cash journal linked with Payment method
        paylater_account_move = self.env['account.move']
        if self.config_id.paylater_journal_id:
            paylater_account_move = self.env['account.move'].with_context(default_journal_id=self.config_id.paylater_journal_id.id).create({
                'journal_id': self.config_id.paylater_journal_id.id,
                'date': fields.Date.context_today(self),
                'ref': self.name,
            })
        # END -->

        ## SECTION: Accumulate the amounts for each accounting lines group
        # Each dict maps `key` -> `amounts`, where `key` is the group key.
        # E.g. `combine_receivables` is derived from pos.payment records
        # in the self.order_ids with group key of the `payment_method_id`
        # field of the pos.payment record.
        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
        tax_amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0}
        split_receivables = defaultdict(amounts)
        split_receivables_cash = defaultdict(amounts)
        combine_receivables = defaultdict(amounts)
        combine_receivables_cash = defaultdict(amounts)
        invoice_receivables = defaultdict(amounts)
        sales = defaultdict(amounts)
        taxes = defaultdict(tax_amounts)
        stock_expense = defaultdict(amounts)
        stock_output = defaultdict(amounts)
        #<-- START The Following added by SANDHI to create dict maps for paylater payments and its receivable
        paylater_payment = defaultdict(amounts)
        paylater_receivables = defaultdict(amounts)
        #END-->
        # Track the receivable lines of the invoiced orders' account moves for reconciliation
        # These receivable lines are reconciled to the corresponding invoice receivable lines
        # of this session's move_id.
        order_account_move_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        rounded_globally = self.company_id.tax_calculation_rounding_method == 'round_globally'
        for order in self.order_ids:
            # Combine pos receivable lines
            # Separate cash payments for cash reconciliation later.
            paylater_amount = 0
            actual_amount = order.amount_total
#             credit_moves = credit_moves.sorted(key=lambda a: (a.date_maturity or a.date, a.currency_id))
            if order.id == 13:
                payment_ids = order.payment_ids.sorted(key=lambda a: (a.is_pay_later), reverse=True)
            for payment in order.payment_ids.sorted(key=lambda a: (a.is_pay_later), reverse=True):
                amount, date = payment.amount, payment.payment_date
                
                if payment.payment_method_id.split_transactions:
                    if payment.payment_method_id.is_cash_count:
                        split_receivables_cash[payment] = self._update_amounts(split_receivables_cash[payment], {'amount': amount}, date)
                    else:
                        split_receivables[payment] = self._update_amounts(split_receivables[payment], {'amount': amount}, date)
                else:
                    key = payment.payment_method_id
                    #<-- START If Paylater create a seperate list for payment line to reconcile paylater journal later
                    if payment.payment_method_id.is_pay_later:
                            paylater_amount += amount  #Sum all paylater amounts to a variable                           
                            paylater_payment[key] = self._update_amounts(paylater_payment[key], {'amount': paylater_amount}, date)
                            actual_amount = actual_amount - paylater_amount
                    #END -->
                    elif payment.payment_method_id.is_cash_count:                       
                        combine_receivables_cash[key] = self._update_amounts(combine_receivables_cash[key], {'amount': amount}, date)
                        
                    else:           
                        combine_receivables[key] = self._update_amounts(combine_receivables[key], {'amount': amount}, date)
                        #actual_amount = actual_amount - amount

            if order.is_invoiced:
                # Combine invoice receivable lines
                key = order.partner_id.property_account_receivable_id.id
                #Actual amount should not include Paylater amount as it should not be reconciled with Invoice move lines
                actual_amount = order.amount_total - paylater_amount 
                if actual_amount > 0: #-- ADDED THIS LINE Create Invoice Receivable amount for other payment methods
                    invoice_receivables[key] = self._update_amounts(invoice_receivables[key], {'amount': actual_amount}, order.date_order)
                #<-- START Paylater receivable are collected in seperate list to reconcile with paylaer payment move line
                if paylater_amount > 0:
                    paylater_receivables[key] = self._update_amounts(paylater_receivables[key], {'amount': paylater_amount}, date)
                #END -->
                # side loop to gather receivable lines by account for reconciliation 
                #<-- SANDHI ADDED paylater Filter except those invoice movelines marked as paylater
                for move_line in order.account_move.line_ids.filtered(lambda aml: aml.account_id.internal_type == 'receivable'):
                    if move_line.is_pay_later == True and move_line.paylater_amt != move_line.amount_residual:
                        move_line['amount_residual'] = move_line.amount_residual - move_line.paylater_amt
                    if move_line.is_pay_later == True and move_line.amount_residual != 0 and move_line.paylater_amt == move_line.amount_residual:
                        continue
                    order_account_move_receivable_lines[move_line.account_id.id] |= move_line
                
            else:
                order_taxes = defaultdict(tax_amounts)
                for order_line in order.lines:
                    line = self._prepare_line(order_line)
                    # Combine sales/refund lines
                    sale_key = (
                        # account
                        line['income_account_id'],
                        # sign
                        -1 if line['amount'] < 0 else 1,
                        # for taxes
                        tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in line['taxes']),
                    )
                    sales[sale_key] = self._update_amounts(sales[sale_key], {'amount': line['amount']}, line['date_order'])
                    # Combine tax lines
                    for tax in line['taxes']:
                        tax_key = (tax['account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(tax['tag_ids']))
                        order_taxes[tax_key] = self._update_amounts(
                            order_taxes[tax_key],
                            {'amount': tax['amount'], 'base_amount': tax['base']},
                            tax['date_order'],
                            round=not rounded_globally
                        )
                for tax_key, amounts in order_taxes.items():
                    if rounded_globally:
                        amounts = self._round_amounts(amounts)
                    for amount_key, amount in amounts.items():
                        taxes[tax_key][amount_key] += amount

                if self.company_id.anglo_saxon_accounting:
                    # Combine stock lines
                    stock_moves = self.env['stock.move'].search([
                        ('picking_id', '=', order.picking_id.id),
                        ('company_id.anglo_saxon_accounting', '=', True),
                        ('product_id.categ_id.property_valuation', '=', 'real_time')
                    ])
                    for move in stock_moves:
                        exp_key = move.product_id.property_account_expense_id or move.product_id.categ_id.property_account_expense_categ_id
                        out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                        amount = -sum(move.stock_valuation_layer_ids.mapped('value'))
                        stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount}, move.picking_id.date)
                        stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount}, move.picking_id.date)

        ## SECTION: Create non-reconcilable move lines
        # Create account.move.line records for
        #   - sales
        #   - taxes
        #   - stock expense
        #   - non-cash split receivables (not for automatic reconciliation)
        #   - non-cash combine receivables (not for automatic reconciliation)
        MoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

        tax_vals = [self._get_tax_vals(key, amounts['amount'], amounts['amount_converted'], amounts['base_amount']) for key, amounts in taxes.items()]
        # Check if all taxes lines have account_id assigned. If not, there are repartition lines of the tax that have no account_id.
        tax_names_no_account = [line['name'] for line in tax_vals if line['account_id'] == False]
        if len(tax_names_no_account) > 0:
            error_message = _(
                'Unable to close and validate the session.\n'
                'Please set corresponding tax account in each repartition line of the following taxes: \n%s'
            ) % ', '.join(tax_names_no_account)
            raise UserError(error_message)

        MoveLine.create(
                tax_vals
                + [self._get_sale_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in sales.items()]
                + [self._get_stock_expense_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in stock_expense.items()]
                + [self._get_split_receivable_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in split_receivables.items()]
                + [self._get_combine_receivable_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in combine_receivables.items()]
            )

        ## SECTION: Create cash statement lines and cash move lines
        # Create the split and combine cash statement lines and account move lines.
        # Keep the reference by statement for reconciliation.
        # `split_cash_statement_lines` maps `statement` -> split cash statement lines
        # `combine_cash_statement_lines` maps `statement` -> combine cash statement lines
        # `split_cash_receivable_lines` maps `statement` -> split cash receivable lines
        # `combine_cash_receivable_lines` maps `statement` -> combine cash receivable lines
        statements_by_journal_id = {statement.journal_id.id: statement for statement in self.statement_ids}
        # handle split cash payments
        split_cash_statement_line_vals = defaultdict(list)
        split_cash_receivable_vals = defaultdict(list)
        for payment, amounts in split_receivables_cash.items():
            statement = statements_by_journal_id[payment.payment_method_id.cash_journal_id.id]
            split_cash_statement_line_vals[statement].append(self._get_statement_line_vals(statement, payment.payment_method_id.receivable_account_id, amounts['amount']))
            split_cash_receivable_vals[statement].append(self._get_split_receivable_vals(payment, amounts['amount'], amounts['amount_converted']))
        # handle combine cash payments
        combine_cash_statement_line_vals = defaultdict(list)
        combine_cash_receivable_vals = defaultdict(list)
        for payment_method, amounts in combine_receivables_cash.items():
            if not float_is_zero(amounts['amount'] , precision_rounding=self.currency_id.rounding):
                statement = statements_by_journal_id[payment_method.cash_journal_id.id]
                combine_cash_statement_line_vals[statement].append(self._get_statement_line_vals(statement, payment_method.receivable_account_id, amounts['amount']))
                combine_cash_receivable_vals[statement].append(self._get_combine_receivable_vals(payment_method, amounts['amount'], amounts['amount_converted']))
        # create the statement lines and account move lines
        BankStatementLine = self.env['account.bank.statement.line']
        split_cash_statement_lines = {}
        combine_cash_statement_lines = {}
        split_cash_receivable_lines = {}
        combine_cash_receivable_lines = {}
        for statement in self.statement_ids:
            split_cash_statement_lines[statement] = BankStatementLine.create(split_cash_statement_line_vals[statement])
            combine_cash_statement_lines[statement] = BankStatementLine.create(combine_cash_statement_line_vals[statement])
            split_cash_receivable_lines[statement] = MoveLine.create(split_cash_receivable_vals[statement])
            combine_cash_receivable_lines[statement] = MoveLine.create(combine_cash_receivable_vals[statement])

        ## SECTION: Create invoice receivable lines for this session's move_id.
        # Keep reference of the invoice receivable lines because
        # they are reconciled with the lines in order_account_move_receivable_lines
        invoice_receivable_vals = defaultdict(list)
        invoice_receivable_lines = {}
        for receivable_account_id, amounts in invoice_receivables.items():
            invoice_receivable_vals[receivable_account_id].append(self._get_invoice_receivable_vals(receivable_account_id, amounts['amount'], amounts['amount_converted']))
        for receivable_account_id, vals in invoice_receivable_vals.items():
            invoice_receivable_lines[receivable_account_id] = MoveLine.create(vals)

        ## SECTION: Create stock output lines
        # Keep reference to the stock output lines because
        # they are reconciled with output lines in the stock.move's account.move.line
        stock_output_vals = defaultdict(list)
        stock_output_lines = {}
        for output_account, amounts in stock_output.items():
            stock_output_vals[output_account].append(self._get_stock_output_vals(output_account, amounts['amount'], amounts['amount_converted']))
        for output_account, vals in stock_output_vals.items():
            stock_output_lines[output_account] = MoveLine.create(vals)

        ## SECTION: Reconcile account move lines
        # reconcile cash receivable lines
        for statement in self.statement_ids:
            if not self.config_id.cash_control:
                statement.write({'balance_end_real': statement.balance_end})
            statement.button_confirm_bank()
            all_lines = (
                  split_cash_statement_lines[statement].mapped('journal_entry_ids').filtered(lambda aml: aml.account_id.internal_type == 'receivable')
                | combine_cash_statement_lines[statement].mapped('journal_entry_ids').filtered(lambda aml: aml.account_id.internal_type == 'receivable')
                | split_cash_receivable_lines[statement]
                | combine_cash_receivable_lines[statement]
            )
            accounts = all_lines.mapped('account_id')
            lines_by_account = [all_lines.filtered(lambda l: l.account_id == account) for account in accounts]
            for lines in lines_by_account:
                lines.reconcile()

        # reconcile invoice receivable lines
        for account_id in order_account_move_receivable_lines:
            if len(invoice_receivable_lines) > 0:
                ( order_account_move_receivable_lines[account_id]
                        | invoice_receivable_lines[account_id]
                        ).reconcile()
            #===================================================================
            # for payment in order.payment_ids:
            #     if payment.payment_method_id.is_pay_later:
            #         ( move_line_1
            #         | invoice_receivable_lines[account_id]
            #         ).reconcile()
            #     else:
            #         ( order_account_move_receivable_lines[account_id]
            #         | invoice_receivable_lines[account_id]
            #         ).reconcile()
            #===================================================================

        # reconcile stock output lines
        stock_moves = self.env['stock.move'].search([('picking_id', 'in', self.order_ids.filtered(lambda order: not order.is_invoiced).mapped('picking_id').ids)])
        stock_account_move_lines = self.env['account.move'].search([('stock_move_id', 'in', stock_moves.ids)]).mapped('line_ids')
        for account_id in stock_output_lines:
            ( stock_output_lines[account_id]
            | stock_account_move_lines.filtered(lambda aml: aml.account_id == account_id)
            ).reconcile()
        #<-- START SANDHI Added to create seperate moveline under "Pay Later" JOURNAL
        paylater_payment_vals = defaultdict(list)
        paylater_payment_lines = {}   
        paylater_receivable_vals = defaultdict(list)
        paylater_receivable_lines = {}
        for key, amounts in paylater_payment.items(): #Paylater Payments LIST
            paylater_payment_vals[key].append(self._get_combine_receivable_vals(key, amounts['amount'], amounts['amount_converted']))
        for receivable_account_id, vals in paylater_payment_vals.items():
            vals[0]['move_id'] = paylater_account_move.id
            paylater_payment_lines[ vals[0]['account_id']] = MoveLine.create(vals)  
            
        for receivable_account_id, amounts in paylater_receivables.items(): #Paylater Receivable LIST
            paylater_receivable_vals[receivable_account_id].append(self._get_invoice_receivable_vals(receivable_account_id, amounts['amount'], amounts['amount_converted']))
        for receivable_account_id, vals in paylater_receivable_vals.items():
            vals[0]['move_id'] = paylater_account_move.id
            paylater_receivable_lines[receivable_account_id] = MoveLine.create(vals)   
        #Reconcile and POST Paylater Journal   
        if paylater_account_move and paylater_account_move.line_ids:
            for account_id in paylater_payment_lines:
                ( paylater_payment_lines[account_id]
                | paylater_receivable_lines[account_id]
                ).reconcile()
            paylater_account_move.post()
        else: 
            #If there are no paylater moves just delete the Paylater Journal
            paylater_account_move.unlink()

        # SANDHI Added to create seperate moveline under "Pay Later" JOURNAL END
class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    #@api.multi
    def _get_report_values(self, docids, data=None):
        """ Inherited method to update payment details of pay later
            in sales details report"""
        data = super(ReportSaleDetails, self)._get_report_values(
                                                            docids, data=data)
        user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
        today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
        today = today.astimezone(pytz.timezone('UTC'))
        if data['date_start']:
            date_start = fields.Datetime.from_string(data['date_start'])
        else:
            # start by default today 00:00:00
            date_start = today

        if data['date_stop']:
            # set time to 23:59:59
            date_stop = fields.Datetime.from_string(data['date_stop'])
        else:
            # stop by default today 23:59:59
            date_stop = today + timedelta(days=1, seconds=-1)

        # avoid a date_stop smaller than date_start
        date_stop = max(date_stop, date_start)

        date_start = fields.Datetime.to_string(date_start)
        date_stop = fields.Datetime.to_string(date_stop)
        configs = self.env['pos.config'].browse(data['config_ids'])
        # Get session statment_lines for payment details
        sessions = self.env['pos.session'].search([
                        ('start_at', '>=', date_start),
                        ('stop_at', '<=', date_stop),
                        ('config_id', 'in', configs.ids)])
        statement_ids = self.env["account.bank.statement"].search([
                                    ('pos_session_id', 'in', sessions.ids)])
        st_line_ids = self.env["account.bank.statement.line"].search([
                                ('statement_id', 'in', statement_ids.ids)]).ids
        if st_line_ids:
            self.env.cr.execute("""
                SELECT aj.name, sum(amount) total
                FROM account_bank_statement_line AS absl,
                     account_bank_statement AS abs,
                     account_journal AS aj
                WHERE absl.statement_id = abs.id
                    AND abs.journal_id = aj.id
                    AND absl.id IN %s
                GROUP BY aj.name
            """, (tuple(st_line_ids),))
            payments = self.env.cr.dictfetchall()
        else:
            payments = []
        # modified previous payments
        data['payments'] = payments
        return data


