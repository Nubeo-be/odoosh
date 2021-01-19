# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductProductAdvancePayment(models.Model):
    _inherit = 'product.product'

    def search_template_id(self):
        product_tmpl_id = self.env['product.template'].search([('radio_advance_mgmt','=', 'left_to_pay')]).id

        product_prod = self.env['product.product'].search([('product_tmpl_id','=',product_tmpl_id)]).id

        return product_prod

    def search_product_advance_payment(self):
        product_tmpl_id = self.env['product.template'].search([('radio_advance_mgmt','=','advance_payment')]).id
        
        product = self.env['product.product'].search([('product_tmpl_id','=',product_tmpl_id)]).id

        return product