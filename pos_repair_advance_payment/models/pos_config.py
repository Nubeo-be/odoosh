# -*- coding: utf-8 -*-

from odoo import models, fields


class PosConfigAdvancePayment(models.Model):
    _inherit = 'pos.config'

    # Champ "Acompte" dans le PoS Config
    pos_advance_payment = fields.Boolean(
        string='Acompte',
        default=True,
    )