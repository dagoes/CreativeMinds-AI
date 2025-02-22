{
    'name': 'CreativeMinds AI',
    'version': '1.0',
    'icon': '/creativeminds_ai/static/description/icon.png',
    'summary': 'Modulo para la gestion de proyectos',
    'description': """
        Gestionar proyectos con AI
    """,
    'author': 'Heily Madelay Ajila Tandazo, Daniel Gonzalez Esteban',
    'category': 'Marketing',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'mail',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}