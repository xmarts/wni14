# -*- coding: utf-8 -*-
import xlrd
import base64
import io
import logging
from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockPickingWNI(models.Model):
    _inherit = 'stock.picking'

    series_file = fields.Binary(string='N.Series Xls file', required=False, copy=False)
    series_filename = fields.Char(string="NS filename", required=False, copy=False)

    def cargar_series(self):

        if not self.series_file:
            raise UserError(_("Error: No hay un archivo adjuntado al campo de Series Xls file"))
        if '.xls' not in self.series_filename:
            raise UserError(_("Error: El archivo no es .xls o xlsx"))
        inputx = io.BytesIO()
        inputx.write(base64.decodebytes(self.series_file))


        book = xlrd.open_workbook(file_contents=inputx.getvalue() or b'')
        sheet = book.sheet_by_index(0)
        nrows = sheet.nrows
        ncols = sheet.ncols
        _logger.info(nrows)
        _logger.info(ncols)
        for i in range(nrows):
            _logger.info(sheet.cell_value(i, 0))
            _logger.info(sheet.cell_value(i, 1))
            serie = sheet.cell_value(i, 0)
            codigo = sheet.cell_value(i, 1)
            valid_product = self.env['product.template'].search([('default_code', '=', codigo)])

            if self.move_ids_without_package and valid_product:
                for move in self.move_ids_without_package:
                    if move.product_id.default_code == codigo:
                        asignada = False
                        for line in move.move_line_ids:
                            if (not line.lot_name or line.lot_name == '') and not asignada:
                                print("averts", serie, asignada)
                                line.lot_name = serie
                                line.qty_done = 1
                                asignada = True
                                print("asiganda", serie, asignada)

    def update_series(self):
        if not self.series_file:
            raise UserError(_("Error: No hay un archivo adjuntado al campo de Series Xls file"))
        if '.xls' not in self.series_filename:
            raise UserError(_("Error: El archivo no es .xls o xlsx"))
        self.move_ids_without_package.move_line_ids.lot_name = False
        self.move_ids_without_package.move_line_ids.qty_done = 0
        self.cargar_series()
