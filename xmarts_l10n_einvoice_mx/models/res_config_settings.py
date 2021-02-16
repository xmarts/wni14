# -*- coding: utf-8 -*-

from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError, UserError, except_orm
from odoo import _, api, fields, models, tools
from pytz import timezone
import base64
import logging
import ssl
import subprocess
import tempfile
from datetime import datetime
from hashlib import sha1

_logger = logging.getLogger(__name__)

try:
    from OpenSSL import crypto
except ImportError:
    _logger.warning(
        'OpenSSL library not found. If you plan to use l10n_mx_edi, please install the library from https://pypi.python.org/pypi/pyOpenSSL')


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"


    edi_user_bd = fields.Char(
        string = "Usuario BD",
        related="company_id.edi_user_bd",
        readonly=False,
        )
    edi_passw_bd = fields.Char(
        string = "Contraseña BD",
        related="company_id.edi_passw_bd",
        readonly=False
        )
    edi_url_bd = fields.Char(
        string = "URL BD",
        related="company_id.edi_url_bd",
        readonly=False
        )
    edi_name_bd = fields.Char(
        string = "Nombre BD",
        related="company_id.edi_name_bd",
        readonly=False
        )

    # @api.model
    # def create(self, vals):
    #     if vals['edi_user_bd'] is not False or vals['edi_user_bd'] is not  None:
    #         val=str(vals['edi_user_bd']).encode('utf-8')
    #         pasw= sha1(val).hexdigest()
    #         vals['edi_user_bd']=pasw

    #     if vals['edi_passw_bd'] is not False or vals['edi_passw_bd'] is not  None:
    #         val=str(vals['edi_passw_bd']).encode('utf-8')
    #         pasw= sha1(val).hexdigest()
    #         vals['edi_passw_bd']=pasw

    #     if vals['edi_url_bd'] is not False or vals['edi_url_bd'] is not  None:
    #         val=str(vals['edi_url_bd']).encode('utf-8')
    #         pasw= sha1(val).hexdigest()
    #         vals['edi_url_bd']=pasw

    #     if vals['edi_name_bd'] is not False or vals['edi_name_bd'] is not  None:
    #         val=str(vals['edi_name_bd']).encode('utf-8')
    #         pasw= sha1(val).hexdigest()
    #         vals['edi_name_bd']=pasw

    #     return super(ResConfigSettings, self).create(vals)


    # def write(self, vals):
    #     if vals.get('edi_user_bd'):
    #         val=str(vals['edi_user_bd']).encode('utf-8')
    #         pasw= sha1(val).hexdigest()
    #         vals['edi_user_bd']=pasw

    #     if vals.get('edi_passw_bd'):
    #         val=str(vals['edi_passw_bd']).encode('utf-8')
    #         pasw= sha1(val).hexdigest()
    #         vals['edi_passw_bd']=pasw

    #     if vals.get('edi_url_bd'):
    #         val=str(vals['edi_url_bd']).encode('utf-8')
    #         pasw= sha1(val).hexdigest()
    #         vals['edi_url_bd']=pasw

    #     if vals.get('edi_name_bd'):
    #         val=str(vals['edi_name_bd']).encode('utf-8')
    #         pasw= sha1(val).hexdigest()
    #         vals['edi_name_bd']=pasw
            
    #     return super(ResConfigSettings, self).write(vals)


    edi_user_pac = fields.Char(
        string="Usuario para PAC.",
        related="company_id.edi_user_pac",
        readonly=False
    )
    edi_pass_pac = fields.Char(
        string="Contraseña para PAC.",
        related="company_id.edi_pass_pac",
        readonly=False
    )
    edi_test_pac = fields.Boolean(
        string="Modo de Prueba",
        default=False,
        related="company_id.edi_test_pac",
        readonly=False
    )
    # edi_certificate_ids = fields.Many2many(
    #     related='company_id.edi_certificate_ids', readonly=False,
    #     string='Certificados MX')
    
    edi_fiscal_regime = fields.Selection([('601', 'General de Ley Personas Morales'),
         ('603', 'Personas Morales con Fines no Lucrativos'),
         ('605', 'Sueldos y Salarios e Ingresos Asimilados a Salarios'),
         ('606', 'Arrendamiento'),
         ('607', 'Régimen de Enajenación o Adquisición de Bienes'),
         ('608', 'Demás ingresos'),
         ('609', 'Consolidación'),
         ('610',
          'Residentes en el Extranjero sin Establecimiento Permanente en México'),
         ('611', 'Ingresos por Dividendos (socios y accionistas)'),
         ('612', 'Personas Físicas con Actividades Empresariales y Profesionales'),
         ('614', 'Ingresos por intereses'),
         ('615', 'Régimen de los ingresos por obtención de premios'),
         ('616', 'Sin obligaciones fiscales'),
         ('620',
          'Sociedades Cooperativas de Producción que optan por diferir sus ingresos'),
         ('621', 'Incorporación Fiscal'),
         ('622', 'Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras'),
         ('623', 'Opcional para Grupos de Sociedades'),
         ('624', 'Coordinados'),
         ('628', 'Hidrocarburos'),
         ('629',
          'De los Regímenes Fiscales Preferentes y de las Empresas Multinacionales'),
         ('630', 'Enajenación de acciones en bolsa de valores')],
        string="Regimen Fiscal",
        help="It is used to fill Mexican XML CFDI"
        "Comprobante.Emisor.RegimenFiscal.",
        related='company_id.edi_fiscal_regime', readonly=False,
        )
    
    # c_serial_number = fields.Char(
    #     string='Serial number',
    #     help='The serial number to add to electronic documents',
    #     readonly=True,
    #     related="company_id.c_serial_number",
    #     index=True)
    # c_date_start = fields.Datetime(
    #     string='Available date',
    #     help='The date on which the certificate starts to be valid',
    #     related="company_id.c_date_start",
    #     readonly=True)
    # c_date_end = fields.Datetime(
    #     string='Expiration date',
    #     help='The date on which the certificate expires',
    #     related="company_id.c_date_end",
    #     readonly=True)
    
    # @tools.ormcache('edi_certificate')
    # def get_pem_cer(self, edi_certificate):
    #     '''Get the current content in PEM format
    #     '''
    #     self.ensure_one()
    #     return ssl.DER_cert_to_PEM_cert(base64.decodestring(edi_certificate)).encode('UTF-8')
    
    # def get_data(self):
    #     '''Return the content (b64 encoded) and the certificate decrypted
    #     '''
    #     self.ensure_one()
    #     cer_pem = self.get_pem_cer(self.edi_certificate)
    #     certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cer_pem)
    #     for to_del in ['\n', ssl.PEM_HEADER, ssl.PEM_FOOTER]:
    #         cer_pem = cer_pem.replace(to_del.encode('UTF-8'), b'')
    #     return cer_pem, certificate
    
    # def get_mx_current_datetime(self):
    #     '''Get the current datetime with the Mexican timezone.
    #     '''
    #     return fields.Datetime.context_timestamp(
    #         self.with_context(tz='America/Mexico_City'), fields.Datetime.now())
    
    # @api.constrains('edi_certificate', 'edi_certificate_key', 'edi_certificate_pass')
    # def _check_certificate_credentials(self):
    #     '''Check the validity of content/key/password and fill the fields
    #     with the certificate values.
    #     '''
    #     mexican_tz = timezone('America/Mexico_City')
    #     mexican_dt = self.get_mx_current_datetime()
    #     date_format = '%Y%m%d%H%M%SZ'
    #     for record in self:
    #         # Try to decrypt the certificate
    #         try:
    #             cer_pem, certificate = record.get_data()
    #             before = mexican_tz.localize(
    #                 datetime.strptime(certificate.get_notBefore().decode("utf-8"), date_format))
    #             after = mexican_tz.localize(
    #                 datetime.strptime(certificate.get_notAfter().decode("utf-8"), date_format))
    #             serial_number = certificate.get_serial_number()
    #         except except_orm as exc_orm:
    #             raise exc_orm
    #         except Exception:
    #             raise ValidationError(_('The certificate content is invalid.'))
    #         # Assign extracted values from the certificate
    #         record.c_serial_number = ('%x' % serial_number)[1::2]
    #         record.c_date_start = before.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #         record.c_date_end = after.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #         if mexican_dt > after:
    #             raise ValidationError(
    #                 _('The certificate is expired since %s') % record.c_date_end)
    #         # Check the pair key/password
    #         try:
    #             key_pem = self.get_pem_key(self.edi_certificate_key, self.edi_certificate_pass)
    #             crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
    #         except Exception:
    #             raise ValidationError(
    #                 _('The certificate key and/or password is/are invalid.'))

    # @tools.ormcache('edi_certificate_key', 'edi_certificate_pass')
    # def get_pem_key(self, edi_certificate_key, edi_certificate_pass):
    #     '''Get the current key in PEM format
    #     '''
    #     self.ensure_one()
    #     return convert_key_cer_to_pem(base64.decodestring(edi_certificate_key), edi_certificate_pass.encode('UTF-8'))
