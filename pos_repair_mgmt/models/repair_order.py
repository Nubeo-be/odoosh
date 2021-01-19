from odoo import api, models, fields

class PosRepair(models.Model):
    _inherit = 'repair.order'

    @api.model
    def _prepare_filter_for_pos(self, pos_session_id):
        return [
            ('state', 'in', ['draft', 'cancel', 'confirmed', 'under_repair', 'ready', '2binvoiced', 'invoice_except', 'done']),
        ]

    @api.model
    def _prepare_filter_query_for_pos(self, pos_session_id, query):
        return [
            '|', '|', '|','|',
            ('name', 'ilike', query),
            ('product_id.name', 'ilike', query),
            ('partner_id.display_name', 'ilike', query),
            ('state', 'ilike', query),
            ('user_id.name', 'ilike', query),
        ]

    @api.model
    def _prepare_fields_for_pos_list(self):
        return ['name','product_id','partner_id','state','user_id','amount_total','account_status']
    
    @api.model
    def search_done_orders_for_pos(self, query, pos_session_id):
        session_obj = self.env['pos.session']
        config = session_obj.browse(pos_session_id).config_id
        condition = self._prepare_filter_for_pos(pos_session_id)
        if query:
            condition += self._prepare_filter_query_for_pos(pos_session_id, query)
        field_names = self._prepare_fields_for_pos_list()
        return self.search_read(
            condition, field_names, limit=config.iface_load_done_order_max_qty)

    def _prepare_done_repair_for_pos(self):
        self.ensure_one()
        order = self.env['pos.order'].search([('pos_reference', '=', self.ref_order)])

        serial_number = self.serial_number

        device_dropped = self.device_dropped

        product_repair = self.product_repair

        repair_lines = []
        payment_lines = []

        for repair_line in order.lines:
            repair_line = self._prepare_done_repair_line_for_pos(repair_line)
            repair_lines.append(repair_line)
        for payment_line in order.payment_ids:
            payment_line = self._prepare_done_repair_payment_for_pos(
                payment_line)
            payment_lines.append(payment_line)
        res = {
            'id': order.id,
            'date_order': order.date_order,
            # 'pos_reference': order.pos_reference,
            'name': order.name,
            'partner_id': self.partner_id.id,
            'fiscal_position': order.fiscal_position_id.id,
            'line_ids': repair_lines,
            # 'statement_ids': payment_lines,
            'payment_lines': payment_lines,
            'to_invoice': bool(order.account_move),
            # 'returned_order_id': order.returned_order_id.id,
            # 'returned_order_reference': order.returned_order_reference,
            'repair_order': order.repair_order.id,
            'serial_number':serial_number,
            'device_dropped':device_dropped,
        }

        return res
    
    def _prepare_done_repair_line_for_pos(self, repair_line):
        self.ensure_one()
        return {
            'product_id': repair_line.product_id.id,
            'qty': repair_line.qty,
            'price_unit': repair_line.price_unit,
            'discount': repair_line.discount,
        }
    
    def _prepare_done_repair_payment_for_pos(self, payment_line):
        self.ensure_one()
        return {
            # 'journal_id': payment_line.journal_id.id,
            'payment_method_id': payment_line.payment_method_id.id,
            'amount': payment_line.amount,
        }

    def load_done_repair_for_pos(self):
        self.ensure_one()
        return self._prepare_done_repair_for_pos()
