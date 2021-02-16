# coding: utf-8

from odoo import fields, models


class PaymentMethod(models.Model):
    _name = 'einvoice.payment.method'
    _description = "Payment Method for Mexico from SAT Data"

    name = fields.Char(
        required=True,
        help='Payment way, is found in the SAT catalog.')
    code = fields.Char(
        required=True,
        help='Code defined by the SAT by this payment way. This value will '
        'be set in the XML node "metodoDePago".')
    active = fields.Boolean(
        default=True,
        help='If this payment way is not used by the company could be '
        'deactivated.')
