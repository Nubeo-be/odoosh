# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class posOrderRepair(models.Model):
    _inherit = "pos.order"

    repair_order = fields.Many2one('repair.order',string="repair_order")
    
    @api.model
    # *** BON DE REPERATION ***
    def create_from_ui(self, orders, draft=False):
        res = super(posOrderRepair,self).create_from_ui(orders, draft)
        repair_order = None
        serial_number = None

        for data in orders:
            if (data['data']['repair_order']):
                repair_order = data['data']['repair_order']
            else:
                repair_order = False
            if (data['data']['serial_number']):
                serial_number = data['data']['serial_number']
            else:
                serial_number = False
            if (data['data']['device_dropped']):
                device_dropped = data['data']['device_dropped']
            else:
                device_dropped = False
            if (data['data']['product_repair']):
                product_repair = data['data']['product_repair']
            else:
                product_repair = False

        for order_id in res:
            order = self.env['pos.order'].search([('id', '=', order_id['id'])])
            products = order.lines.product_id
            partner_id = order.partner_id.id

            pos_reference = order.pos_reference

            account_status = 'to_pay'
            for product in products:
                if (product['radio_advance_mgmt'] == 'left_to_pay'):
                    account_status = 'account'
                elif (product['radio_advance_mgmt'] == 'account'):
                    account_status = 'paid'
                else:
                    account_status
            # [CONDITION] SI LE REPAIR ORDER EXISTE
            if (repair_order == False):
                for product in products:
                    # [CONDITION] POUR MAJ LE ACCOUNT_STATUS
                    if (product['radio_advance_mgmt'] == 'left_to_pay'):
                        account_status = 'account'

                    if (product['to_make_repair'] == True):
                        uom_id = self.env['product.product'].search([('id', '=', product['id'])]).uom_id.id
                        
                        # [CREATE] REPAIR ORDER
                        self.env['repair.order'].create({
                            'product_id' : product['id'],
                            'product_uom' : uom_id,
                            'partner_id': partner_id,
                            'ref_order': pos_reference,
                            'serial_number': serial_number,
                            'device_dropped': device_dropped,
                            'product_repair': product_repair,
                            'state': 'confirmed',
                            'account_status': account_status,
                        })
                ref_repair = self.env['repair.order'].search([('ref_order', '=', pos_reference)]).id
        
                # [UPDATE] MAJ DU FIELD REPAIR ORDER DANS LA COMMANDE
                order = self.env['pos.order'].search([('pos_reference', '=', pos_reference)])
                order.update({
                    'repair_order' : ref_repair,
                })
            else:
                # [UPDATE] MAJ DU FIELD REPAIR ORDER DANS LA COMMANDE "RETOUR"
                order_nxt = self.env['pos.order'].search([('pos_reference', '=', pos_reference)])
                order_nxt.update({
                    'repair_order' : repair_order,
                })
                current_repair = self.env['repair.order'].search([('id','=',repair_order)])
                current_repair.update({
                    'account_status' : 'paid',
                })
                
        
        
