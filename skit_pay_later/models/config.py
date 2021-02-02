from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'
    _description = 'Point of Sale Configuration'

    def _default_paylater_journal(self):
        for paylater in self.payment_method_ids.filtered(lambda x: x.is_pay_later == True):
            if paylater:
                return self.env['account.journal'].search([('is_pay_later', '=', True)])

    paylater_journal_id = fields.Many2one(
        'account.journal', string='Paylater Journal',
        help="Accounting journal used to create paylater.",
        default=_default_paylater_journal)