{
    'name': 'CreativeMinds',
    'version': '1.0',
    'icon': '/creativeminds_ai/static/description/icon.png',
    'summary': 'Modulo para la gestion de proyectos',
    'description': """
        Gestion de proyectos
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