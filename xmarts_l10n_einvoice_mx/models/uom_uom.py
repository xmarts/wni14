# coding: utf-8

from odoo import fields, models, api, _


class UomUom(models.Model):
    _inherit = "uom.uom"

    edi_code_sat_id = fields.Many2one(
        string="Codigo SAT",
        required=True,
        comodel_name="edi.product.sat.code",
        domain=[('applies_to', '=', 'uom')]
    )
