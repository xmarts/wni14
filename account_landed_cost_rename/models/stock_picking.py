# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

import re

CUSTOM_NUMBERS_PATTERN = re.compile(r'[0-9]{2}  [0-9]{2}  [0-9]{4}  [0-9]{7}')


class StockPicking(models.Model):
    _inherit = 'stock.picking'

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
        string='Customs number', size=21, copy=False)

    _sql_constraints = [
        (
            'customs_number',
            'UNIQUE (customs_number)',
            _('The custom number must be unique!'),
        )
    ]

    def _get_custom_numbers(self):
        self.ensure_one()
        if self.customs_number:
            return [num.strip() for num in self.customs_number.split(',')]
        else:
            return []

    @api.constrains('customs_number')
    def _check_customs_number(self):
        stock_picking = self.env['stock.picking']
        for picking in self:
            custom_numbers = picking._get_custom_numbers()
            if any(not CUSTOM_NUMBERS_PATTERN.match(custom_number) for custom_number in custom_numbers):
                stock_picking |= picking

        if not stock_picking:
            return

        raise ValidationError(_(
            "Custom numbers set on invoice lines are invalid and should have a pattern like: 15  48  3009  0001234:\n%(invalid_message)s",
            invalid_message='\n'.join(
                '%s (id=%s)' % (p.customs_number, p.id) for p in stock_picking),
        ))
