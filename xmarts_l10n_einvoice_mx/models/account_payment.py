# coding: utf-8

from odoo import fields, models, api, _
import xmlrpc.client
import logging
from lxml.objectify import fromstring
import base64
from odoo.exceptions import UserError
from datetime import datetime
from odoo.tools import float_round
from dateutil.relativedelta import relativedelta

# from json2xml import json2xml
# from json2xml.utils import readfromurl, readfromstring, readfromjson
# import xmltodict
from odoo.tools import DEFAULT_SERVER_TIME_FORMAT

class SingnPayment(models.Model):
    _inherit = "account.payment"

    edi_payment_cfdi = fields.Binary(
        string = 'Cfdi content', copy = False, readonly = True,
        help = 'The cfdi xml content encoded in base64.')
    edi_payment_cfdi_name = fields.Char(
        string = 'CFDI name',
        copy = False,
        readonly = True,
        help = 'The attachment name of the CFDI.')
    
    edi_payment_cfdi_uuid = fields.Char(
        string = 'Fiscal Folio',
        copy = False,
        readonly = True,
        compute = "_compute_cfdi_values",
        help = 'Folio in electronic invoice, is returned by SAT when send to stamp.')
    edi_payment_expedition_date = fields.Date(
        string = 'Expedition Date', copy = False,
        help = 'Save the expedition date of the CFDI that according to the SAT '
        'documentation must be the date when the CFDI is issued.')
    edi_payment_origin = fields.Char(
        string = 'CFDI Origin', copy = False,
        help = 'In some cases the payment must be regenerated to fix data in it. '
        'In that cases is necessary this field filled, the format is: '
        '\n04|UUID1, UUID2, ...., UUIDn.\n'
        'Example:\n"04|89966ACC-0F5C-447D-AEF3-3EED22E711EE,\n'
        '89966ACC-0F5C-447D-AEF3-3EED22E711EE"')
    edi_payment_pac_status = fields.Selection(
        selection = [
            ('none', 'CFDI not necessary'),
            ('retry', 'Retry'),
            ('to_sign', 'To sign'),
            ('signed', 'Signed'),
            ('to_cancel', 'To cancel'),
            ('cancelled', 'Cancelled')
        ],
        string = 'PAC status', default = 'none',
        help = 'Refers to the status of the CFDI inside the PAC.',
        readonly = True, copy = False)
    edi_payment_partner_bank_id = fields.Many2one(
        'res.partner.bank', 'Partner Bank', help = 'If the payment was made '
        'with a financial institution define the bank account used in this '
        'payment.')
    edi_payment_payment_method_id = fields.Many2one(
        'l10n_mx_edi.payment.method',
        string = 'Payment Way',
        readonly = True,
        states = {'draft': [('readonly', False)]},
        help = 'Indicates the way the payment was/will be received, where the '
        'options could be: Cash, Nominal Check, Credit Card, etc.')
    edi_payment_sat_status = fields.Selection(
        selection = [
            ('none', 'State not defined'),
            ('undefined', 'Not Synced Yet'),
            ('not_found', 'Not Found'),
            ('cancelled', 'Cancelled'),
            ('valid', 'Valid'),
        ],
        string = 'SAT status',
        help = 'Refers to the status of the CFDI inside the SAT system.',
        readonly = True, copy = False, required = True,
        tracking = True, default = 'undefined')
    edi_payment_time_payment = fields.Char(
        string = 'Time payment', readonly = True, copy = False,
        states = {'draft': [('readonly', False)]},
        help = "Keep empty to use the current Mexico central time")

    edi_payment_method_id = fields.Many2one(
        'l10n_mx_sing_payment.payment.method', 'Payment Way')

    force_pue = fields.Boolean(
        string = 'Force PUE',
    )

    edi_payment_cfdi_supplier_rfc = fields.Char(
        'Supplier RFC',
        copy = False,
        readonly = True,
        help = 'The supplier tax identification number.',
        compute = '_compute_cfdi_values')
    edi_payment_cfdi_customer_rfc = fields.Char(
        'Customer RFC',
        copy = False,
        readonly = True,
        help = 'The customer tax identification number.',
        compute = '_compute_cfdi_values')

    edi_cadena_original = fields.Char(
        string = 'Cadena original',
        readonly = True,
    )

    edi_payment_without_invoice = fields.Boolean(
        string = 'payment without invoice', default = False

    )

    def _get_serie_and_folio(number):
        values = {'serie': None, 'folio': None}
        number = (number or '').strip()
        number_matchs = [rn for rn in re.finditer('\d+', number)]
        if number_matchs:
            last_number_match = number_matchs[-1]
            values['serie'] = number[:last_number_match.start()] or None
            values['folio'] = last_number_match.group().lstrip('0') or None
        return values

    def _get_payment_write_off(self):
        self.ensure_one()
        writeoff_move_line = self.move_line_ids.filtered(lambda l: l.account_id == self.writeoff_account_id and l.name == self.writeoff_label)
        res = {}
        if writeoff_move_line and self.invoice_ids:
            last_invoice = self.invoice_ids[-1]
            if last_invoice.currency_id == last_invoice.company_currency_id:
                write_off_invoice_currency = writeoff_move_line.balance
            elif last_invoice.currency_id == writeoff_move_line.currency_id:
                write_off_invoice_currency = writeoff_move_line.amount_currency
            else:
                write_off_invoice_currency = writeoff_move_line.currency_id._convert(
                    writeoff_move_line.amount_currency or writeoff_move_line.balance, last_invoice.currency_id,
                    last_invoice.company_id, last_invoice.date
                )
            if write_off_invoice_currency > 0:
                res[last_invoice.id] = write_off_invoice_currency
        return res

    def edi_sign_payment(self):
        for rec in self:
            time_invoice = datetime.strptime(rec.edi_payment_time_payment,
                                         DEFAULT_SERVER_TIME_FORMAT).time()
            date=datetime.combine(
                fields.Datetime.from_string(rec.edi_payment_expedition_date),
                time_invoice).strftime('%Y-%m-%dT%H:%M:%S')
            payment_date = datetime.combine(
                fields.Datetime.from_string(rec.payment_date),
                datetime.strptime('12:00:00', '%H:%M:%S').time()).strftime('%Y-%m-%dT%H:%M:%S')
            certificate_ids = rec.company_id.edi_certificate_ids
            certificate_id = certificate_ids.sudo().get_valid_certificate()
            origin = rec.edi_payment_cfdi_name.split('|')
            uuids = origin[1].split(',') if len(origin) > 1 else [] 
            related = [u.strip() for u in uuids]
            anex1_list_json=[]
            origin = rec.edi_payment_cfdi_name.split('|')
            uuids = origin[1].split(',') if len(origin) > 1 else [] 
            related = [u.strip() for u in uuids]
            if rec.edi_payment_cfdi_name:
                if len(rec.edi_payment_cfdi_name.split('|'))>1:
                    anex1_list_json.append({'TipoRelacion':origin[0]})
                    for rel in related:
                        anex1_list_json.append({'UUID':rel})
            total_paid = total_curr = total_currency = 0
            for invoice in rec.invoice_ids:
                amount = [p for p in invoice._get_reconciled_info_JSON_values() if (
                    p.get('account_payment_id', False) == rec.id or not p.get(
                    'account_payment_id') and (not p.get('invoice_id') or p.get(
                        'invoice_id') == invoice.id))]
                amount_payment = sum([data.get('amount', 0.0) for data in amount])
                total_paid += amount_payment if invoice.currency_id != rec.currency_id else 0
                total_currency += amount_payment if invoice.currency_id == rec.currency_id else 0
            amount = rec.amount - total_currency
            inv_rate = ('%.6f' % (total_paid / amount)) if rec.currency_id != rec.invoice_ids.mapped('currency_id') else False
            inv_rate = (inv_rate if ((total_paid / float(inv_rate)) <= amount) else '%.6f' % (float(inv_rate) + 0.000001)) if inv_rate else inv_rate
            rate = ('%.6f' % (rec.currency_id.with_context(**ctx)._convert(
            1, mxn, rec.company_id, rec.payment_date, round=False))) if rec.currency_id.name != 'MXN' else False
            payment_code = rec.edi_payment_payment_method_id.code
            acc_emitter_ok = payment_code in [
                '02', '03', '04', '05', '06', '28', '29', '99']
            acc_receiver_ok = payment_code in [
                '02', '03', '04', '05', '28', '29', '99']
            bank_name_ok = payment_code in ['02', '03', '04', '28', '29', '99']
            partner_bank = rec.edi_payment_partner_bank_id.bank_id
            vat = 'XEXX010101000' if partner_bank.country and partner_bank.country != self.env.ref(
            'base.mx') else partner_bank.edi_vat
            company_bank = rec.journal_id.bank_account_id
            writeoff_vals=rec._get_payment_write_off()
            anex2_list_json=[]
            for invoice in rec.invoice_ids:
                amount = [p for p in invoice._get_reconciled_info_JSON_values() if (p.get('account_payment_id', False) == rec.id or not p.get('account_payment_id') and (not p.get('move_id') or p.get('move_id') == invoice.id))]
                amount_payment = sum([data.get('amount', 0.0) for data in amount])
                amount_insoluto = invoice.amount_residual
                anex2_list_json.append({
                    "IdDocumento" : invoice.edi_cfdi_uuid,
                    "Serie" : invoice.edi_serie,
                    "Folio" : invoice.edi_folio,
                    "MonedaDR" : invoice.currency_id.name,
                    "TipoCambioDR" : inv_rate if rec.currency_id != invoice.currency_id else False,
                    "MetodoDePagoDR" : invoice.edi_cfdi['MetodoPago'],
                    "NumParcialidad":len(invoice._get_reconciled_payments().filtered(lambda p: p.state not in ('draft', 'cancelled') and not p.move_line_ids.mapped('move_id.reversed_entry_id')).ids),
                    "ImpSaldoAnt" : '%0.*f' % (rec.currency_id.edi_decimal_places, invoice.amount_residual + amount_payment),
                    "ImpPagado" : '%0.*f' % (rec.currency_id.edi_decimal_places, amount_payment - (writeoff_vals.get(invoice.id, 0) if invoice.currency_id == rec.currency_id else 0)),
                    "ImpSaldoInsoluto" : '%0.*f' % (rec.currency_id.edi_decimal_places, amount_insoluto + (writeoff_vals.get(invoice.id, 0) if invoice.currency_id == rec.currency_id else 0))
                    })
            xml_json = {"cfdi:Comprobante":{
                "xsi:schemaLocation":"http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd http://www.sat.gob.mx/Pagos http://www.sat.gob.mx/sitio_internet/cfd/Pagos/Pagos10.xsd",
                "xmlns:cfdi":"http://www.sat.gob.mx/cfd/3",
                "xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance",
                "xmlns:pago10":"http://www.sat.gob.mx/Pagos",
                "Version":"3.3",
                "Fecha":date,
                "Folio":rec._get_serie_and_folio(rec.name)['folio'],
                "Serie":rec._get_serie_and_folio(rec.name)['serie'],
                "Sello":"",
                "NoCertificado":certificate_id.serial_number,
                "Certificado":certificate_id.sudo().get_data()[0],
                "SubTotal":0,
                "Moneda":"XXX",
                "Total":0,
                "TipoDeComprobante":"P",
                "LugarExpedicion":rec.journal_id.edi_address_issued_id or rec.company_id.partner_id.commercial_partner_id.zip,
                "Confirmacion":"confirmation",
                "cfdi:CfdiRelacionados":{
                    "TipoRelacion":origin[0],
                    'cfdi:CfdiRelacionado': {"UUID":anex1_list_json}
                    },
                "cfdi:Emisor":{
                    "Rfc":rec.edi_payment_cfdi_supplier_rfc,
                    "Nombre":rec.company_id.partner_id.commercial_partner_id.name,
                    "RegimenFiscal":rec.company_id.edi_fiscal_regime
                    },
                "cfdi:Receptor":{
                    "Rfc":rec.edi_payment_cfdi_customer_rfc,
                    "Nombre":rec.partner_id.name,
                    "ResidenciaFiscal":rec.partner_id.commercial_partner_id.country_id.l10n_mx_edi_code if rec.partner_id.commercial_partner_id.country_id.l10n_mx_edi_code != 'MEX' else False,
                    "NumRegIdTrib":rec.partner_id.vat,
                    "UsoCFDI":"P01"
                    },
                "cfdi:Conceptos":{
                    "cfdi:Concepto":{
                        "ClaveProdServ":"84111506",
                        "Cantidad":"1",
                        "ClaveUnidad":"ACT",
                        "Descripcion":"Pago",
                        "ValorUnitario":"0",
                        "Importe":"0"
                        }
                    },
                "cfdi:Complemento":{
                    "pago10:Pagos":{
                        "Version":"1.0",
                        "pago10:Pago":{
                            "FechaPago" : payment_date,
                            "FormaDePagoP" : rec.edi_payment_method_id.code,
                            "MonedaP" : rec.currency_id.name,
                            "TipoCambioP" : rate,
                            "Monto" : '%.*f' % (rec.currency_id.edi_decimal_places, rec.amount),
                            "NumOperacion" : rec.communication[:100].replace('|', ' ') if rec.communication else None,
                            "RfcEmisorCtaOrd" : vat if acc_emitter_ok else None,
                            "NomBancoOrdExt" : partner_bank.name if bank_name_ok else None,
                            "CtaOrdenante" : (rec.edi_payment_partner_bank_id.acc_number or '').replace(' ', '') if acc_emitter_ok else None,
                            "RfcEmisorCtaBen" : company_bank.bank_id.edi_vat if acc_receiver_ok else None,
                            "CtaBeneficiario" : (company_bank.acc_number or '').replace(' ', '') if acc_receiver_ok else None,
                            "TipoCadPago" : False,
                            "CertPago" : False,
                            "CadPago" : False,
                            "SelloPago" :False,
                            "pago10:DoctoRelacionado":{anex2_list_json},
                            # a partir de aqui empiezan los impuestos con campos que no estan definidos en el modulo de account.payment
                            "pago10:Impuestos":{
                                "TotalImpuestosRetenidos":"total_withhold",
                                "TotalImpuestosTrasladados" : "total_transferred",
                                "pago10:Retenciones" : {
                                    "Impuesto" : "tax.tax",
                                    "Importe" : "tax.amount"
                                    },
                                "pago10:Traslados" : {
                                    "pago10:Traslado" : {
                                        "Impuesto" : "tax.tax",
                                        "TipoFactor":"tax.type",
                                        "TasaOCuota" : "tax.rate",
                                        "Importe" : "tax.amount"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }