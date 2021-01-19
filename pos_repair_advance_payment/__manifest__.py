# -*- coding: utf-8 -*-
{
    'name': "pos_repair_advance_payment",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Nubeo",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Point of Sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','point_of_sale','sale_management','website_sale','repair'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/view_pos_config.xml',
        'static/src/xml/assets.xml',
        'views/product_template.xml',
    ],
    'qweb': ['static/src/xml/pos_advance_payment.xml'],
}
