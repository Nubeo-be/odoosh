# -*- coding: utf-8 -*-
{
    'name': "PoS Repair Management",
    'version': '13.0',
    'description': """This module is useful for managing repairs via the point of sale.""",
    'author': "Nubeo",
    'category': 'Point Of Sale',
    'depends': ['base','point_of_sale','repair'],
    'data': [
        'views/assets.xml',
        'views/pos_order_form.xml',
        'views/view_pos_config.xml',
    ],
    'qweb': [
        'static/src/xml/pos.xml'
    ],
    'application': False,
    'installable': True,
}
