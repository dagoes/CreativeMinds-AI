# -*- coding: utf-8 -*-
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
    'version': '17.0.1.0.0',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}