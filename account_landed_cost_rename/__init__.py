from . import models


def post_load():
    can_patch = True
    try:
        from odoo.addons.l10n_mx_edi_landing.models.account_move import AccountMove
    except ImportError:
        can_patch = False

    def post(self):
        # OVERRIDE
        for move in self.filtered(lambda move: move.is_invoice()):
            for line in move.line_ids:
                if line.related_reserved_lots:
                    related_lots = line.related_reserved_lots.split(",")
                    lots = self.env['stock.production.lot'].sudo().search([
                        ('name', 'in', related_lots), ('pedimento_si', '!=', False)
                    ])
                    line.l10n_mx_edi_customs_number = ','.join(list(set(lots.mapped('pedimento_si'))))
                    # parte de vauxo
                stock_moves = line.mapped('sale_line_ids.move_ids').filtered(
                    lambda r: r.state in ('done', 'assigned') and not r.scrapped)
                if not stock_moves:
                    continue

                    # buscar compras , compras checar pickings , buscar landed cost con esos pickings profit
                if line.related_reserved_lots:
                    related_lots = line.related_reserved_lots.split(",")
                    lots = self.env['stock.production.lot'].sudo().search([
                        ('name', 'in', related_lots),
                    ])
                    picking_ids = lots.purchase_order_ids.picking_ids.filtered(
                        lambda p: p.state not in ['cancel', 'draft'])
                    landed_costs = self.env['stock.landed.cost'].sudo().search([
                        ('picking_ids', 'in', picking_ids.ids),
                        ('l10n_mx_edi_customs_number', '!=', False),
                    ])
                    if not landed_costs:
                        continue
                    line.l10n_mx_edi_customs_number = ','.join(
                        list(set(landed_costs.mapped('l10n_mx_edi_customs_number'))))
        super(AccountMove, self).post()

    if can_patch:
        AccountMove.post = post
