# coding: utf-8


from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        # OVERRIDE
        for move in self.filtered(lambda move: move.is_invoice()):
            for line in move.line_ids:
                if line.related_reserved_lots:
                    related_lots = line.related_reserved_lots.split(",")
                    moves = self.env['stock.move.line'].sudo().search([
                        ('lot_id.name', 'in', related_lots),
                        ('picking_id.customs_number', '!=', False),
                        ('picking_id.picking_type_code', '=', 'incoming'),
                    ])
                    line.customs_number = ','.join(
                        list(set(moves.mapped('picking_id.customs_number'))))

        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    customs_number = fields.Char(
        help='Optional field for entering the customs information in the case '
        'of first-hand sales of imported goods or in the case of foreign trade'
        ' operations with goods or services.\n'
        'The format must be:\n'
        ' - 2 digits of the year of validation followed by two spaces.\n'
        ' - 2 digits of customs clearance followed by two spaces.\n'
        ' - 4 digits of the serial number followed by two spaces.\n'
        ' - 1 digit corresponding to the last digit of the current year, '
        'except in case of a consolidated customs initiated in the previous '
        'year of the original request for a rectification.\n'
        ' - 6 digits of the progressive numbering of the custom.',
        string='Customs number',
        copy=False)
