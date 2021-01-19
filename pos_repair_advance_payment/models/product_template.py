# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductTemplateAdvancePayment(models.Model):
    _inherit = 'product.template'

    radio_advance_mgmt = fields.Selection([('advance_payment','Acompte'),('left_to_pay','Solde restant')],'Gestion des acomptes')