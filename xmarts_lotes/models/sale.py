from odoo import api, fields, models, _
from odoo.exceptions import Warning
from odoo.tools import float_compare


# MDLR- Added in _compute_check_availability state partially available,
# for cases when you have ex. 4 qty of 5 of the same stock_move.

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    show_check_availability = fields.Boolean(string='Delivery Orders', compute='_compute_check_availability',
                                             copy=False)

    @api.depends('picking_ids')
    def _compute_check_availability(self):
        for order in self:
            # default
            if not order.picking_ids:
                order.show_check_availability = False
                return
            for picking in order.picking_ids:
                if picking.immediate_transfer or picking.state not in ('confirmed', 'waiting', 'assigned'):
                    order.show_check_availability = False
                    continue
                order.show_check_availability = any(
                    move.state in ('waiting', 'confirmed', 'partially_available') and
                    float_compare(move.product_uom_qty, 0, precision_rounding=move.product_uom.rounding)
                    for move in picking.move_lines
                )
                if order.show_check_availability:
                    break

    def move_action_assign(self):
        for move in self.mapped('picking_ids').filtered(lambda x: x.show_check_availability):
            move.sudo().action_assign()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    moves_reserved_qty = fields.Integer(string="Cantidad Reservada", compute='_compute_assigned_qty', copy=False)
    related_lots = fields.Char(string="Related Lots", compute='_compute_assigned_lots', copy=False)

    @api.depends('move_ids')
    def _compute_assigned_qty(self):
        for line in self:
            reserved_qty = 0
            if line.display_type not in ['line_section', 'line_note']:
                reserved_qty = sum(
                    move.reserved_availability for move in
                    line.mapped('move_ids').filtered(lambda x: x.state != 'cancel'))
            line.moves_reserved_qty = reserved_qty or 0

    @api.depends('move_ids', 'move_ids.move_line_ids')
    def _compute_assigned_lots(self):
        for line in self:
            reserved_lots = ''
            if line.move_ids:
                reserved_lots = [move.lot_id.name or '' for picking in
                                 line.mapped('move_ids').filtered(
                                     lambda x: x.state == 'done' and x.picking_code != 'incoming')
                                 for move in picking.mapped('move_line_ids').filtered(
                        lambda x: x.qty_done > 0 and x.picking_id.sale_id.name == x.picking_id.origin)]
            if reserved_lots:
                line.related_lots = ','.join(reserved_lots)
            else:
                line.related_lots = ''

    def _prepare_invoice_line(self, **optional_values):
        values = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)
        if self.product_id.tracking != 'none':
            values['related_reserved_lots'] = self.related_lots
        return values
