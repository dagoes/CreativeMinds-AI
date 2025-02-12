from odoo import models, fields

class CreativeMindsAI(models.Model):
    _name = 'creativeminds.ai'
    _description = 'Creative Minds AI Model'

    name = fields.Char(string='Name', required=True)

class Employees(models.Model):
    _name = 'creativeminds.employees'
    _description = 'Employees'

    name = fields.Char(string='Name', required=True)

class Teams(models.Model):
    _name = 'creativeminds.teams'
    _description = 'Teams'

    name = fields.Char(string='Name', required=True)

class ControlPanel(models.Model):
    _name = 'creativeminds.control.panel'
    _description = 'Control Panel'

    name = fields.Char(string='Name', required=True)