from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_repair_mgmt = fields.Boolean(
        string='Repair Management',
        help='Allows to manage repairs in the frontend',
        default=True,
    )

    iface_copy_done_order = fields.Boolean(
        string='Duplicate Orders',
        default=True,
        help='Allows to duplicate already done orders in the frontend',
    )

    # iface_reprint_done_order = fields.Boolean(
    #     string='Reprint Orders',
    #     default=True,
    #     help='Allows to reprint already done orders in the frontend',
    # )

    # iface_return_done_order = fields.Boolean(
    #     string='Return Orders',
    #     default=True,
    #     help='Allows to return already done orders in the frontend',
    # )

    # iface_load_done_order_max_qty = fields.Integer(
    #     string='Maximum Orders to load',
    #     default=10,
    #     required=True,
    #     help='Maximum number of orders to load on the PoS at its init. '
    #          'Set it to 0 to load none (it\'s still possible to load them by '
    #          'ticket code).',
    # )
