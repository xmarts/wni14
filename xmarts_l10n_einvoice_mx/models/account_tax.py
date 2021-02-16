# coding: utf-8

from odoo import fields, models, api, _


class AccountTax(models.Model):
    _name = "account.tax"
    _inherit = "account.tax"
    
    def _get_edi_factor_type(self):
        return [
            ("Tasa", _("Tasa")),
            ("Cuota", _("Cuota")),
            ("Excento", _("Excento")),
        ]

    edi_cfdi_tax_type = fields.Selection(
        string="Tipo Factor",
        required=True,
        selection="_get_edi_factor_type"
    )
