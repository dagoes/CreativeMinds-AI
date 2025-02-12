{
    'name': 'CreativeMinds AI',
    'version': '1.0',
    'icon': '/creativeminds_ai/static/description/icon.png',
    'summary': 'Modulo para la gestion de proyectos',
    'description': """
        Gestionar proyectos con AI
    """,
    'author': 'Heily Madelay Ajila Tandazo',
    'category': 'Marketing',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/assets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/creativeminds_ai/static/src/css/style.css',
            '/creativeminds_ai/static/src/js/script.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}