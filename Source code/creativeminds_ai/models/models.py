from odoo import models, fields, api

class CreativemindsAi(models.Model):
    _name = 'creativeminds_ai'
    _description = 'Creativeminds AI'
    
    name = fields.Char(string='Name')