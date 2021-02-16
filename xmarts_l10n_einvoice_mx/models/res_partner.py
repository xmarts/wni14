# coding: utf-8

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def edi_get_customer_rfc(self):
        if self.country_id and self.country_id != self.env.ref('base.mx'):
            return 'XEXX010101000'
        if (self.country_id == self.env.ref('base.mx') or not self.country_id) and not self.vat:
            self.message_post(
                body=_('Using General Public VAT because no vat found'),
                subtype='account.mt_invoice_validated')
            return 'XAXX010101000'
        return self.vat.strip()