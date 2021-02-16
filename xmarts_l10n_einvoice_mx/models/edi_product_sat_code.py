# coding: utf-8

from odoo import fields, models, api, _
from odoo.osv import expression

class EdiProductSatCode(models.Model):
    _name = "edi.product.sat.code"
    _description = "Codigos del SAT para los productos y unidades de medida de odoo."
    
    def get_apliesd_to(self):
        return [
            ("product", _("Producto")),
            ("uom", _("Unidad de Medida")),
        ]
    
    name = fields.Char(
        string="Nombre de Codigo SAT",
        required=True,
    )
    code = fields.Char(
        string="Codigo SAT",
        required=True,
    )
    applies_to = fields.Selection(
        string="Aplicado a:",
        required=True,
        selection="get_apliesd_to"
    )
    active = fields.Boolean(
        default=True
    )

    def name_get(self):
        result = []
        for prod in self:
            if prod.code and prod.name:
                result.append((prod.id, "{} {}".format(prod.code, prod.name)))
            else:
                result.append((prod.id,""))
        return result

    #@api.model
    #def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
    #    args = args or []
    #    if operator == 'ilike' and not (name or '').strip():
    #        domain = []
    #    else:
    #        domain = ['|', ('name', 'ilike', name), ('code', 'ilike', name)]
    #    #sat_code_ids = self._search(expression.AND(
    #    #    [domain, args]), limit=limit, access_rights_uid=name_get_uid)
    #    return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
    #    # return models.lazy_name_get(self.browse(sat_code_ids).with_user(name_get_uid))
