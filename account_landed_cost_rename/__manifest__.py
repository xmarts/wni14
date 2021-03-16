{
    'name': 'Account landed cost Rename',
    'version': '14',
    'category': "",
    'description': """ Adds a method to rename a landed cost number by adding pedimento_si field in lot 
    """,
    'sequence': 1,
    'author':'Xmarts',
    'depends': ['base','account','xmarts_lotes'],
    'data': [
        'views/production_lot_views.xml',
    ],
    'qweb': [
        ],
    'demo': [],
    'test': [],
    "post_load": "post_load",
    'installable': True,
    'auto_install': False,
}
