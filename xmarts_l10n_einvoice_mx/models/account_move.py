# coding: utf-8

from odoo import fields, models, api, _, tools
import xmlrpc.client
import logging
from lxml.objectify import fromstring
import base64
from odoo.exceptions import UserError
from datetime import datetime
from odoo.tools import float_round
from dateutil.relativedelta import relativedelta
from odoo.tools.float_utils import float_repr
import requests

# from json2xml import json2xml
# from json2xml.utils import readfromurl, readfromstring, readfromjson
import json
# import xmltodict
from odoo.tools import DEFAULT_SERVER_TIME_FORMAT
from lxml import etree

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    def _get_edi_usage(self):
        return [
            ("G01", _("G01 Adquisición de mercancias.")),
            ("G02", _("G02 Devoluciones, descuentos o bonificaciones.")),
            ("G03", _("G03 Gastos en general.")),
            ("I01", _("I01 Construcciones.")),
            ("I02", _("I02 Mobilario y equipo de oficina por inversiones.")),
            ("I03", _("I03 Equipo de transporte.")),
            ("I04", _("I04 Equipo de computo y accesorios.")),
            ("I05", _("I05 Dados, troqueles, moldes, matrices y herramental.")),
            ("I06", _("I06 Comunicaciones telefónicas.")),
            ("I07", _("I07 Comunicaciones satelitales.")),
            ("I08", _("I08 Otra maquinaria y equipo.")),
            ("D01", _("D01 Honorarios médicos, dentales y gastos hospitalarios.")),
            ("D02", _("D02 Gastos médicos por incapacidad o discapacidad.")),
            ("D03", _("D03 Gastos funerales.")),
            ("D04", _("D04 Donativos.")),
            ("D05", _("D05 Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación).")),
            ("D06", _("D06 Aportaciones voluntarias al SAR.")),
            ("D07", _("D07 Primas por seguros de gastos médicos.")),
            ("D08", _("D08 Gastos de transportación escolar obligatoria.")),
            ("D09", _("D09 Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones.")),
            ("D10", _("D10 Pagos por servicios educativos (colegiaturas).")),
            ("P01", _("P01 Por definir."))
        ]

    def _get_edi_pac_status(self):
        return [
            ("retry", _("Reintentar")),
            ("to_sign", _("Para Firmar")),
            ("signed", _("Firmado")),
            ("to_cancel", _("Para Cancelar")),
            ("cancelled", _("Cancelado")),
        ]

    def _get_edi_cfdi_relation_type(self):
        return [
            ("01", _("01 - Nota de crédito")),
            ("02", _("02 - Nota de débito de los documentos relacionados")),
            ("03", _("03 - Devolución de mercancía sobre facturas o traslados previos")),
            ("04", _("04 - Sustitución de los CFDI previos")),
            ("05", _("05 - Traslados de mercancías facturados previamente")),
            ("06", _("06 - Factura generada por los traslados previos")),
            ("07", _("07 - CFDI por aplicación de anticipo")),
        ]

    edi_usage = fields.Selection(
        string="Uso de CFDI",
        selection="_get_edi_usage",
        tracking=True,
        copy=False
    )
    edi_payment_method_id = fields.Many2one(
        string="Forma de pago",
        comodel_name="einvoice.payment.method",
        tracking=True,
        copy=False
    )
    edi_pac_status = fields.Selection(
        string="Estado de PAC",
        selection="_get_edi_pac_status",
        copy=False,
        tracking=True,
        readonly=True
    )
    edi_cfdi = fields.Binary(
        string="Archivo CFDI",
        copy=False,
        readonly=True
    )
    edi_cfdi_name = fields.Char(
        string="Nombre del archivo CFDI",
        copy=False,
        tracking=True,
        readonly=True
    )
    edi_cfdi_uuid = fields.Char(
        string="Folio Fiscal",
        copy=False,
        tracking=True,
        readonly=True
    )
    edi_cfdi_relation_type = fields.Selection(
        string="Relacion del CFDI",
        selection="_get_edi_cfdi_relation_type",
        tracking=True,
        copy=False
    )
    edi_cfdi_origin = fields.Char(
        string="CFDI Origen",
        tracking=True,
        copy=False
    )
    edi_cadena_original = fields.Text(
        string="Cadena Original",
        copy=False,
        readonly=True
    )
    edi_cfdi_supplier_rfc = fields.Char(
        string="RFC Emisor",
        copy=False,
        tracking=True,
        readonly=True
    )
    edi_cfdi_customer_rfc = fields.Char(
        string="RFC Receptor",
        copy=False,
        tracking=True,
        readonly=True
    )
    edi_cfdi_amount = fields.Monetary(
        string="Monto CFDI",
        copy=False,
        tracking=True,
        readonly=True
    )
    edi_folio = fields.Char(
        string="Folio",
        copy=False,
        tracking=True,
        readonly=True
    )
    edi_serie = fields.Char(
        string="Serie",
        copy=False,
        tracking=True,
        readonly=True
    )

    edi_sat_status = fields.Selection(
        selection=[
            ('none', 'State not defined'),
            ('undefined', 'Not Synced Yet'),
            ('not_found', 'Not Found'),
            ('cancelled', 'Cancelled'),
            ('valid', 'Valid'),
        ],
        string='SAT status',
        readonly=True,
        copy=False,
        tracking=True,
        default='undefined')

    @api.model
    def edi_get_xml_etree(self, cfdi=None):
        self.ensure_one()
        if cfdi is None and self.edi_cfdi:
            cfdi = base64.decodestring(self.edi_cfdi)
        return fromstring(cfdi) if cfdi else None

    @api.model
    def edi_get_et_etree(self, cfdi):
        if not hasattr(cfdi, 'Complemento'):
            return None
        attribute = 'cce11:ComercioExterior[1]'
        namespace = {'cce11': 'http://www.sat.gob.mx/ComercioExterior11'}
        node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
        return node[0] if node else None

    @api.model
    def edi_get_tfd_etree(self, cfdi):
        if not hasattr(cfdi, 'Complemento'):
            return None
        attribute = 'tfd:TimbreFiscalDigital[1]'
        namespace = {'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'}
        node = cfdi.Complemento.xpath(attribute, namespaces=namespace)
        return node[0] if node else None

    def edi_amount_to_text(self):
        self.ensure_one()
        currency = self.currency_id.name.upper()
        currency_type = 'M.N' if currency == 'MXN' else 'M.E.'
        # Split integer and decimal part
        amount_i, amount_d = divmod(self.amount_total, 1)
        amount_d = round(amount_d, 2)
        amount_d = int(round(amount_d * 100, 2))
        words = self.currency_id.with_context(lang=self.partner_id.lang or 'es_ES').amount_to_text(amount_i).upper()
        invoice_words = '%(words)s %(amount_d)02d/100 %(curr_t)s' % dict(
            words=words, amount_d=amount_d, curr_t=currency_type)
        return invoice_words

    def edi_update_sat_status(self):
        CFDI_SAT_QR_STATE = {
            'No Encontrado': 'not_found',
            'Cancelado': 'cancelled',
            'Vigente': 'valid',
            }
        url = 'https://consultaqr.facturaelectronica.sat.gob.mx/ConsultaCFDIService.svc?wsdl'
        headers = {'SOAPAction': 'http://tempuri.org/IConsultaCFDIService/Consulta', 'Content-Type': 'text/xml; charset=utf-8'}
        template = """<?xml version="1.0" encoding="UTF-8"?>
                    <SOAP-ENV:Envelope xmlns:ns0="http://tempuri.org/" 
                    xmlns:ns1="http://schemas.xmlsoap.org/soap/envelope/" 
                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                     xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">
                       <SOAP-ENV:Header/>
                       <ns1:Body>
                          <ns0:Consulta>
                             <ns0:expresionImpresa>${data}</ns0:expresionImpresa>
                          </ns0:Consulta>
                       </ns1:Body>
                    </SOAP-ENV:Envelope>    
                    """
        namespace = {'a': 'http://schemas.datacontract.org/2004/07/Sat.Cfdi.Negocio.ConsultaCfdi.Servicio'}
        for inv in self.filtered('edi_cfdi'):
            supplier_rfc = inv.edi_cfdi_supplier_rfc
            customer_rfc = inv.edi_cfdi_customer_rfc
            total = float_repr(inv.edi_cfdi_amount,
                               precision_digits=inv.currency_id.decimal_places)
            uuid = inv.edi_cfdi_uuid
            params = '?re=%s&amp;rr=%s&amp;tt=%s&amp;id=%s' % (
                tools.html_escape(tools.html_escape(supplier_rfc or '')),
                tools.html_escape(tools.html_escape(customer_rfc or '')),
                total or 0.0, uuid or '')
            soap_env = template.format(data=params)
            try:
                soap_xml = requests.post(url, data=soap_env,
                                         headers=headers, timeout=20)
                response = fromstring(soap_xml.text)
                status = response.xpath(
                    '//a:Estado', namespaces=namespace)
            except Exception as e:
                inv.message_post(body=_(
                    """<p>Error: . </p><p><ul>%s</ul></p>""" % str(e)),
                                 message_type=_('notification'))
                continue
            inv.edi_sat_status = CFDI_SAT_QR_STATE.get(
                status[0] if status else '', 'none')

    def post(self):
        # OVERRIDE
        # Assign time and date coming from a certificate.
        if self.move_type not in ['out_invoice', 'out_refund']:
            return super(AccountMove, self).post()
        else:
            for move in self:

                # Line having a negative amount is not allowed.
                for line in move.invoice_line_ids:
                    if line.price_subtotal < 0:
                        raise UserError(_("Tiene lineas de factura en negativo "
                                          " que no son permitidas en el documento del CFDI. "
                                          " En su lugar, cree una nota de crédito."))

                date_mx = datetime.now()
                if not move.invoice_date:
                    move.invoice_date = date_mx.date()
                    move.with_context(
                        check_move_validity=False)._onchange_invoice_date()
            sequence = False,
            to_write = {}
            invoice_name = move._get_sequence()
            if invoice_name:
                interpolated_prefix, interpolated_suffix = invoice_name._get_prefix_suffix()
                for p in invoice_name.date_range_ids:
                    to_write['edi_folio'] = p.number_next_actual
                    to_write['edi_serie'] = interpolated_prefix

            if move.name == '/':
                # Get the journal's sequence.
                sequence = move._get_sequence()
                if not sequence:
                    raise UserError(
                        _('Defina una secuencia en el diario seleccionado.'))

                # Consume a new number.
                to_write['name'] = sequence.with_context(
                    ir_sequence_date=move.date).next_by_id()
            move.write(to_write)
            result = super(AccountMove, self).post()
            if self.move_type in ['out_invoice', 'out_refund']:
                self.edi_sign_invoice()
            return result
    
    def _einvoice_edi_get_payment_policy(self):
        self.ensure_one()
        version = '3.3'
        term_ids = self.invoice_payment_term_id.line_ids
        if version == '3.2':
            if len(term_ids.ids) > 1:
                return 'Pago en parcialidades'
            else:
                return 'Pago en una sola exhibición'
        elif version == '3.3' and self.invoice_date_due and self.invoice_date:
            if self.move_type == 'out_refund':
                return 'PUE'
            if self.invoice_date_due.month > self.invoice_date.month or \
               self.invoice_date_due.year > self.invoice_date.year or \
               len(term_ids) > 1:  # to be able to force PPD
                return 'PPD'
            return 'PUE'
        return ''
    
    @api.model
    def _l10n_mx_edi_xmarts_info(self):
        # test = company_id.l10n_mx_edi_pac_test_env
        # username = company_id.l10n_mx_edi_pac_username
        # password = company_id.l10n_mx_edi_pac_password
        url = 'http://ws.facturacionmexico.com.mx/pac/?wsdl'
        return {
            'url': url,
            'multi': False,  # TODO: implement multi
            'username': 'DEMO700101XXX' if self.company_id.edi_test_pac == True else self.company_id.edi_user_pac,
            'password': 'DEMO700101XXX' if self.company_id.edi_test_pac == True else self.company_id.edi_pass_pac,
            'production': 'NO' if self.company_id.edi_test_pac == True else 'SI',
        }
    
    def edi_cancel_cfdi(self):
        for rec in self:
            try:
                user_data = rec._l10n_mx_edi_xmarts_info()
                print("USER DATA: ", user_data)
                url = rec.company_id.edi_url_bd
                db = rec.company_id.edi_name_bd
                username = rec.company_id.edi_user_bd
                password = rec.company_id.edi_passw_bd
                common = xmlrpc.client.ServerProxy(
                    '{}/xmlrpc/2/common'.format(url))
                uid = common.authenticate(db, username, password, {})
                models = xmlrpc.client.ServerProxy(
                    '{}/xmlrpc/2/object'.format(url))
                response = {}
            
            
                model_name = 'sign.account.move'
            
                json_data = {'uuid': rec.edi_cfdi_uuid.lower()}
                print("DATA TO CANCEL: ", json_data, user_data['username'], user_data['password'], user_data['production'])
                _logger.debug("This is my debug message !  %s %s %s " % (user_data['username'], user_data['password'], user_data['production']))
                response = models.execute_kw(
                    db, uid, password, model_name, 'request_cancel_invoice', [False, json_data, user_data['username'], user_data['password'], user_data['production'], rec.edi_cfdi])
                if response['status'] == 'success':
                    rec.message_post(body=_(
                        """<p>El servicio de cancelacion solicitado fue llamado con exito. """),
                        message_type=_('notification'))
                    rec.edi_pac_status = 'cancelled'
                    rec.edi_cfdi_relation_type = '04'
                    rec.edi_cfdi_origin = rec.edi_cfdi_uuid
                    rec.edi_cfdi_uuid = ''
                if response['status'] == 'error':
                    rec.message_post(body=_(
                    """<p>El servicio de cancelacion solicitado falló. </p><p><ul>%s</ul></p>""" % response['mensaje']),
                                 message_type=_('notification'))
                    # rec.edi_pac_status = 'to_cancel'
            except Exception as err:
                rec.message_post(body=_(
                    """<p>La conexion falló.</p><p><ul>%s</ul></p>""" % err))
                # rec.edi_pac_status = 'to_cancel'
            
        
        
    def edi_sign_invoice(self):

        def tax_name(t): return {
            'ISR': '001', 'IVA': '002', 'IEPS': '003'}.get(t, False)
        
        for rec in self:
            
            product_list = """"""
            errorp = False
            for line in rec.invoice_line_ids:
                if not line.product_id.edi_code_sat_id:
                    errorp = True
                    product_list = product_list + """<li>El atributo Codigo Sat del producto (%s) no esta definido.</li>""" % (
                        line.product_id.name)
                if not line.product_id.uom_id.edi_code_sat_id:
                    errorp = True
                    product_list = product_list + """<li>El atributo Codigo Sat de la unidad de medida del producto (%s) no esta definido.</li>""" % (
                        line.product_id.name)

            if errorp is True:
                rec.message_post(
                    body=_(
                        """<p>El servicio de firma solicitado falló.</p><p><ul>%s</ul></p>""" % product_list),
                    message_type=_('notification'))
                rec.edi_pac_status = 'retry'
                return False
            
            error_log = []
            time_invoice = self.env['einvoice.edi.certificate'].sudo().get_mx_current_datetime()
            certificate_ids = rec.company_id.edi_certificate_ids
            certificate_id = certificate_ids.sudo().get_valid_certificate()
            if not certificate_id:
                error_log.append(_('No se encontro certificado valido'))
                
            condiciones = str(rec.invoice_payment_term_id.name).replace('|', ' ')
            
            subtotal_wo_discount = lambda l: float_round(
            l.price_subtotal / (1 - l.discount/100) if l.discount != 100 else
            l.price_unit * l.quantity, int(2))
            
            total_withhold = 0
            total_transferred = 0
            name_transferred = "" 
            name_withhold = "" 
            type_transferred = "" 
            for line in rec.invoice_line_ids.filtered('price_subtotal'):
                price = line.price_unit * (1.0 - (line.discount or 0.0) / 100.0)
                tax_line = {tax['id']: tax for tax in line.tax_ids.compute_all(
                    price, line.currency_id, line.quantity, line.product_id, line.partner_id, self.move_type in ('in_refund', 'out_refund'))['taxes']}
                for tax in line.tax_ids.filtered(lambda r: r.edi_cfdi_tax_type != 'Exento'):
                    tax_dict = tax_line.get(tax.id, {})
                    amount = round(abs(tax_dict.get(
                        'amount', tax.amount / 100 * float("%.2f" % line.price_subtotal))), 2)
                    if tax.amount >= 0:
                        total_transferred += amount
                        name_transferred = tax_name(tax.mapped('invoice_repartition_line_ids.tag_ids')[0].name if tax.mapped(
                            'invoice_repartition_line_ids.tag_ids') else '')  
                        type_transferred = tax.edi_cfdi_tax_type 
                    else:
                        total_withhold += amount
                        name_withhold = tax_name(tax.mapped('invoice_repartition_line_ids.tag_ids')[0].name if tax.mapped(
                            'invoice_repartition_line_ids.tag_ids') else '')  
            get_discount = lambda l, d: ('%.*f' % (int(d), subtotal_wo_discount(l) - l.price_subtotal)) if l.discount else False
            total_discount = sum([float(get_discount(p, 2)) for p in rec.invoice_line_ids]) 
            amount_untaxed = '%.*f' % (2, sum([subtotal_wo_discount(p)
                              for p in self.invoice_line_ids]))
            date = rec.invoice_date or fields.Date.today()
            company_id = rec.company_id
            ctx = dict(company_id=company_id.id, date=date)
            mxn = self.env.ref('base.MXN').with_context(ctx)
            invoice_currency = rec.currency_id.with_context(ctx)
            document_type = 'ingreso' if self.move_type == 'out_invoice' else 'egreso'
            anex1_list_json=[]
            origin = ''
            uuids = ''
            related = ''
            if rec.edi_cfdi_origin:
                origin = rec.edi_cfdi_origin
                luuids = origin.split(',')
                print("UUIDS: ", uuids)
                related = [u for u in uuids]
            if rec.edi_cfdi_origin:
                if rec.edi_cfdi_origin:
                    anex1_list_json.append({'TipoRelacion':rec.edi_cfdi_relation_type})
                    uuids = []
                    for u in luuids:
                        print("RELATED: ", u)
                        uuids.append( {'UUID':u})
            lista_productos = []
            for line in rec.invoice_line_ids.filtered(lambda inv: not inv.display_type):
                
                taxes_line = line.filtered(
                    'price_subtotal').tax_ids.flatten_taxes_hierarchy()
                
                if taxes_line:
                    price = line.price_unit * \
                        (1.0 - (line.discount or 0.0) / 100.0)
                        
                tax_line = {tax['id']: tax for tax in taxes_line.compute_all(
                    price, line.currency_id, line.quantity, line.product_id, line.partner_id, is_refund=rec.move_type in ('in_refund', 'out_refund'))['taxes']}
                
                transferred = taxes_line.filtered(lambda r: r.amount >=0)
                withholding = taxes_line.filtered(lambda r: r.amount < 0)
                
                product_taxes_list = []
                product_taxes_list2 = []
                
    
                
                if transferred:
                    for tax in transferred:
                        tax_dict = tax_line.get(tax.id, {})
                        tasa = '%.6f' % abs(
                            tax.amount if tax.amount_type == 'fixed' else (tax.amount / 100.0))
                        tax_amount = '%.2f' % abs(tax_dict.get(
                            'amount', (tax.amount if tax.amount_type == 'fixed' else tax.amount / 100.0) * line.price_subtotal))
                        product_taxes_list.append({"cfdi:Traslado": {
                            "Base": '%.*f' % (rec.currency_id.decimal_places, float(tax_amount) / float(tasa) if tax.amount_type == 'fixed' else tax_dict.get('base', line.price_subtotal)),
                            "Impuesto": tax_name(tax.mapped('invoice_repartition_line_ids.tag_ids')[0].name if tax.mapped('invoice_repartition_line_ids.tag_ids') else ''),
                            "TipoFactor": tax.edi_cfdi_tax_type,
                            "TasaOCuota": tasa if tax.edi_cfdi_tax_type != 'Exento' else False,
                            "Importe": tax_amount if tax.edi_cfdi_tax_type != 'Exento' else False}})
                if withholding:
                    for tax in withholding:
                        tax_dict = tax_line.get(tax.id, {})
                        tasa = '%.6f' % abs(tax.amount if tax.amount_type == 'fixed' else (tax.amount / 100.0))
                        product_taxes_list2.append({"cfdi:Retencion": {
                            "Base": '%.*f' % (rec.currency_id.decimal_places, tax_dict.get('base', line.price_subtotal)),
                            "Impuesto": tax_name(tax.mapped('invoice_repartition_line_ids.tag_ids')[0].name if tax.mapped('invoice_repartition_line_ids.tag_ids') else ''),
                            "TipoFactor": tax.edi_cfdi_tax_type,
                            "TasaOCuota": tasa,
                            "Importe": '%.2f' % abs(tax_dict.get('amount', tax.amount / 100.0 * line.price_subtotal))
                        }})
                
                lista_productos.append({"cfdi:Concepto": {
                    'ClaveProdServ': line.product_id.edi_code_sat_id.code,
                    'NoIdentificacion': line.product_id.default_code or '',
                    'Cantidad': '%.6f' % line.quantity,
                    'ClaveUnidad': line.product_uom_id.edi_code_sat_id.code,
                    'Unidad': line.product_uom_id.name,
                    'Descripcion': line.name,
                    'ValorUnitario': '%.*f' % (rec.currency_id.decimal_places, subtotal_wo_discount(line)/line.quantity) if line.quantity else 0.0,
                    'Importe': '%.*f' % (rec.currency_id.decimal_places, subtotal_wo_discount(line)),
                    'Descuento': ('%.*f' % (rec.currency_id.decimal_places, subtotal_wo_discount(line) - line.price_subtotal)),
                    "cfdi:Impuestos": {"cfdi:Traslados": product_taxes_list, "cfdi:Retenciones": product_taxes_list2}
                }})
                            
            xml_json = {'xsi:schemaLocation': 'http://www.sat.gob.mx/cfd/3 http://www.sat.gob.mx/sitio_internet/cfd/3/cfdv33.xsd http://www.sat.gob.mx/ComercioExterior11 http://www.sat.gob.mx/sitio_internet/cfd/ComercioExterior11/ComercioExterior11.xsd',
                        'xmlns:cfdi': 'http://www.sat.gob.mx/cfd/3',
                        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                        'xmlns:cce11': 'http://www.sat.gob.mx/ComercioExterior11',
                        'Version':'3.3',
                        'Fecha': time_invoice.strftime('%Y-%m-%dT%H:%M:%S'),
                        'Folio':rec.edi_folio,
                        'Serie': rec.edi_serie,
                        'Sello':'',
                        'FormaPago': rec.edi_payment_method_id.code,
                        'NoCertificado': '',
                        'Certificado': '',
                        'CondicionesDePago': condiciones.strip()[:1000] if rec.invoice_payment_term_id else False,
                        'SubTotal': amount_untaxed,
                        'Descuento': '%.*f' % (2, total_discount) if total_discount else 0,
                        'Moneda': rec.currency_id.name,
                        'TipoCambio': ('%.6f' % (invoice_currency._convert(1, mxn, rec.company_id, rec.invoice_date or fields.Date.today(), round=False))) if rec.currency_id.name != 'MXN' else {},
                        'Total': '%0.*f' % (2, float(amount_untaxed) - float(float('%.*f' % (2, total_discount)) or 0) + (
                                                float(total_transferred) or 0) - (float(total_withhold) or 0)),
                        'TipoDeComprobante': document_type[0].upper(),
                        'MetodoPago': rec._einvoice_edi_get_payment_policy(),
                        'LugarExpedicion': rec.company_id.partner_id.commercial_partner_id.zip,
                        
                        'cfdi:CfdiRelacionados':{
                            "TipoRelacion": rec.edi_cfdi_relation_type if rec.edi_cfdi_origin else '',
                            'cfdi:CfdiRelacionado': uuids
                            }if origin else [],
                        
                        'cfdi:Emisor':{
                            'Rfc':rec.company_id.vat,
                            'Nombre':rec.company_id.partner_id.commercial_partner_id.name,
                            'RegimenFiscal':rec.company_id.edi_fiscal_regime
                        },

                        'cfdi:Receptor':{
                            'Rfc': rec.partner_id.vat,
                            'Nombre':rec.partner_id.name,
                            # 'ResidenciaFiscal': rec.partner_id.country_id.edi_code if rec.partner_id.country_id.edi_code != 'MEX' and rec.partner_id.vat not in ['XEXX010101000', 'XAXX010101000'] else {},
                            #'NumRegIdTrib':rec.partner_id.vat,
                            'UsoCFDI':rec.edi_usage
                        },

                        'cfdi:Conceptos': lista_productos,
                        'cfdi:Impuestos':{
                            'TotalImpuestosTrasladados': total_transferred if total_transferred > 0 else {},
                            'TotalImpuestosRetenidos': total_withhold if total_withhold > 0 else {},
                            'cfdi:Retenciones':[
                                {
                                    'cfdi:Retencion':{
                                        'Importe':total_withhold,
                                        'Impuesto':name_withhold
                                    }
                                }
                            ] if total_withhold > 0 else [],
                            'cfdi:Traslados':[
                                {
                                    'cfdi:Traslado':{
                                        'Importe':total_transferred,
                                        'Impuesto':name_transferred,
                                        'TipoFactor':type_transferred,
                                        'TasaOCuota':'%.6f' % abs(tax.amount if tax.amount_type == 'fixed' else (tax.amount / 100.0)),
                                    }
                                }
                            ] if total_transferred > 0 else []
                        }
                    }
            rec.edi_cfdi_supplier_rfc = rec.company_id.vat
            rec.edi_cfdi_customer_rfc = rec.partner_id.vat
            rec.edi_cfdi_amount = '%0.*f' % (2, float(amount_untaxed) - float(float('%.*f' % (2, total_discount)) or 0) + (
                                                float(total_transferred) or 0) - (float(total_withhold) or 0))
            try:
                user_data = rec._l10n_mx_edi_xmarts_info()
                url = rec.company_id.edi_url_bd
                db = rec.company_id.edi_name_bd
                username = rec.company_id.edi_user_bd
                password = rec.company_id.edi_passw_bd
                common = xmlrpc.client.ServerProxy(
                    '{}/xmlrpc/2/common'.format(url))
                uid = common.authenticate(db, username, password, {})
                models = xmlrpc.client.ServerProxy(
                    '{}/xmlrpc/2/object'.format(url))
                response = {}
                
                
                model_name = 'sign.account.move'

                response = models.execute_kw(db, uid, password, model_name,'request_sign_invoice', [False, xml_json, user_data['username'], user_data['password'], user_data['production']])
                if response['status'] == 'success':
                    print("RRRRRRRRRRR: ",response['cfdi'])
                    rec.edi_cfdi = response['cfdi']
                    rec.edi_cfdi_uuid = response['uuid'].upper()
                    rec.edi_cfdi_name = \
                        ('%s-%s-MX-Invoice-%s.xml' %
                            (rec.journal_id.code, rec.name,
                            "3.3".replace('.', '-'))).replace('/', '')
                    rec.edi_pac_status = 'signed'
                    rec.message_post(body=_(
                        """<p>El servicio de firma solicitado fue llamado con exito. """ ),
                        message_type=_('notification'))
                if response['status'] == 'error':
                    if response['codigo'] in [0,1]:
                        rec.message_post(body=_(
                            """<p>El servicio de firma solicitado falló. </p><p><ul>%s</ul></p>""" % response['mensaje_original_pac_json']),
                                            message_type=_('notification'))
                        rec.edi_pac_status = 'retry'
                    else:
                        rec.message_post(body=_(
                            """<p>El servicio de firma solicitado falló. %s</p><p><ul>%s</ul></p>""" % (json.loads(response['mensaje_original_pac_json'])['message'],
                                                                                                        json.loads(response['mensaje_original_pac_json'])['messageDetail'])),
                            message_type=_('notification'))
                        rec.edi_pac_status = 'retry'
            except Exception as err:
                rec.message_post(body=_(
                    """<p>La conexion falló.</p><p><ul>%s</ul></p>""" % err))
                rec.edi_pac_status = 'retry'
            
