# coding: utf-8

from odoo import fields, models, api, _

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    edi_code_sat_id = fields.Many2one(
        string="Codigo SAT",
        required=True,
        comodel_name="edi.product.sat.code",
        domain=[('applies_to', '=', 'product')]
    )
