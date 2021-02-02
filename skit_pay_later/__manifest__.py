# -*- coding: utf-8 -*-

{
    'name': 'Pay Later in POS',
    'version': '1.1',
    'summary': 'This module helps to perform pay later for generated invoices',
    'author': 'Srikesh Infotech',
    'license': "OPL-1",
    'website': 'http://www.srikeshinfotech.com',
    'price': 20,
    'currency': 'EUR',
    'images': ['images/main_screenshot.png'],
    'depends': ['base', 'point_of_sale',
                'account', 'sale_management'],
    'data': [
        'views/pay_later_template.xml',
        'views/account_view.xml',
        'views/account_move_view.xml',
        'views/pos_order_view.xml',
        'views/config.xml',
        'report/pay_later_report.xml',
    ],
    'qweb': ['static/src/xml/pay_later.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
