# coding: utf-8


from odoo import models, fields, api, _


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    pedimento_si = fields.Char(string="Pedimento SI", copy=False)

