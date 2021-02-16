# coding: utf-8

from odoo import fields, models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    edi_decimal_places = fields.Integer(
        'Número de decimales', readonly=True)
