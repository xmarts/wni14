# -*- coding: utf-8 -*-
{
    'name': "xmarts_l10n_einvoice_mx",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Xmarts",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Account',
    'version': '13.2.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/account_move_view.xml',
        'views/account_tax_view.xml',
        'views/product_template_view.xml',
        'views/uom_view.xml',
        'views/res_country_view.xml',
        'views/res_config_view.xml',
        'views/certificate_view.xml',
        'data/payment_method.xml',
        'views/account_journal_view.xml',
        'views/account_payment_view.xml',
        'views/res_bank_view.xml',
        'reports/einvoice_mx_report.xml'
        
    ],
    "post_init_hook": "post_init_hook",
    'installable': True,
    'auto_install': False,
    'uninstall_hook': 'uninstall_hook',
}
