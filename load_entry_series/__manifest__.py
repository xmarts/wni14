# -*- coding: utf-8 -*-
{
    'name': "Serie/Lotes Entrada por excel",

    'summary': """
        Adaptaciones a wni""",

    'description': """
        Este  modulo asigna los lotes de entrada en recepcion usando un excel
    """,

    'author': "Xmarts",
    'website': "http://www.xmarts.com",
    'category': 'Uncategorized',
    'version': '14.1',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','purchase','stock'],

    # always loaded
    'data': [
        'views/templates.xml',
        'security/ir.model.access.csv',
    ],
}