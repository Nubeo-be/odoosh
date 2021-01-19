from odoo import models, fields, api
from odoo.exceptions import Warning


class MrpProduction(models.Model):
    _inherit = 'repair.order'

    # def create(self, vals):
    #     print("003")
    #     print(self.env['pos.order'].search([]))
    #     res = super(MrpProduction, self).create(vals)

    #     print(self.env['pos.order'].search([]))
    #     print("003--end")
    #     return res

    def create_mrp_from_pos(self, products):
        product_ids = []
        if products:
            for product in products:
                flag = 1
                if product_ids:
                    for product_id in product_ids:
                        if product_id['id'] == product['id']:
                            product_id['qty'] += product['qty']
                            flag = 0
                if flag:
                    product_ids.append(product)
            for prod in product_ids:
                if prod['qty'] > 0:
                    product = self.env['product.product'].search([('id', '=', prod['id'])])
                    pos_reference_search = self.env['pos.order'].search([('pos_reference', '=', prod['pos_reference_bis'])])
                    # print("001")
                    # print(pos_reference_search)
                    # print("-")
                    # bom_count = self.env['mrp.bom'].search([('product_tmpl_id', '=', prod['product_tmpl_id'])])
                    # if bom_count:
                    #     bom_temp = self.env['mrp.bom'].search([('product_tmpl_id', '=', prod['product_tmpl_id']),
                    #                                            ('product_id', '=', False)])
                    #     bom_prod = self.env['mrp.bom'].search([('product_id', '=', prod['id'])])
                    #     if bom_prod:
                    #         bom = bom_prod[0]
                    #     elif bom_temp:
                    #         bom = bom_temp[0]
                    #     else:
                    #         bom = []
                    #     if bom:
                    #         vals = {
                    #             'origin': 'POS-' + prod['pos_reference'],
                    #             'state': 'confirmed',
                    #             'product_id': prod['id'],
                    #             'product_tmpl_id': prod['product_tmpl_id'],
                    #             'product_uom_id': prod['uom_id'],
                    #             'product_qty': prod['qty'],
                    #             'bom_id': bom.id,
                    #         }
                    # mrp_order = self.sudo().create(vals)
                    # list_value = []
                    self.sudo().create({
                        'product_id': prod['id'],
                        'product_uom': prod['uom_id'],
                        'partner_id': prod['partner_id'],
                        'pos_reference_bis': prod['pos_reference_bis'],
                        # 'pos_reference': [(6, 0, [pos_reference_search.id])]
                    })
                    
                    # print(self.env['repair.order'].search([('pos_reference', '=', prod['pos_reference'])]))
                    # repair_id = self.env['repair.order'].search([('pos_reference', '=', prod['pos_reference'])]).id
                    # for bom_line in mrp_order.bom_id.bom_line_ids:
                    #     list_value.append((0, 0, {
                    #                 'raw_material_production_id': mrp_order.id,
                    #                 'name': mrp_order.name,
                    #                 'product_id': bom_line.product_id.id,
                    #                 'product_uom': bom_line.product_uom_id.id,
                    #                 'product_uom_qty': bom_line.product_qty,
                    #                 'picking_type_id': mrp_order.picking_type_id.id,
                    #                 'location_id': mrp_order.location_src_id.id,
                    #                 'location_dest_id': mrp_order.location_dest_id.id,
                    #                 'company_id': mrp_order.company_id.id,
                    #     }))
                    # mrp_order.update({'move_raw_ids':list_value})

        return True
        # return repair_id


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    to_make_repair = fields.Boolean(string='To Create Repair Order',
                                    help="Check if the product should be make repair order")

# class ProductProduct(models.Model):
#     _inherit = 'product.product'

    # @api.onchange('to_make_repair')
    # def onchange_to_make_mrp(self):
    #     if self.to_make_repair:
    #         if not self.bom_count:
    #             raise Warning('Please set Bill of Material for this product.')

# class RepairOrderReference(models.Model):
#     _inherit = 'pos.order'

#     repair_order = fields.Char(string="Référence réparation")
