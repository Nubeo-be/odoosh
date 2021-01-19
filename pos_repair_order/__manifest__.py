# -*- coding: utf-8 -*-
{
    'name': 'PoS Repair Order',
    'version': '13.0',
    'description': """Launch automatic Repair Order in PoS""",
    'author': 'Nubeo',
    'category': 'Point of Sale',
    'depends': ['point_of_sale', 'repair', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_view.xml',
        'views/pos_template.xml',
        'views/pos_order_form.xml',
    ],
    'installable': True,
    'auto_install': False,
}