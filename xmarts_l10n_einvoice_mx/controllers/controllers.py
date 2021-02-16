# -*- coding: utf-8 -*-
# from odoo import http


# class XmartsL10nEinvoiceMx(http.Controller):
#     @http.route('/xmarts_l10n_einvoice_mx/xmarts_l10n_einvoice_mx/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/xmarts_l10n_einvoice_mx/xmarts_l10n_einvoice_mx/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('xmarts_l10n_einvoice_mx.listing', {
#             'root': '/xmarts_l10n_einvoice_mx/xmarts_l10n_einvoice_mx',
#             'objects': http.request.env['xmarts_l10n_einvoice_mx.xmarts_l10n_einvoice_mx'].search([]),
#         })

#     @http.route('/xmarts_l10n_einvoice_mx/xmarts_l10n_einvoice_mx/objects/<model("xmarts_l10n_einvoice_mx.xmarts_l10n_einvoice_mx"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('xmarts_l10n_einvoice_mx.object', {
#             'object': obj
#         })
