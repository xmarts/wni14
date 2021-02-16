# -*- coding: utf-8 -*-

import base64
import logging
import ssl
import subprocess
import tempfile
from datetime import datetime

_logger = logging.getLogger(__name__)

try:
    from OpenSSL import crypto
except ImportError:
    _logger.warning('Libreria OpenSSL no encontrada. Porfavor Instale la libreria, consulte en https://pypi.python.org/pypi/pyOpenSSL')

from pytz import timezone

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError, UserError, except_orm
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


KEY_TO_PEM_CMD = 'openssl pkcs8 -in %s -inform der -outform pem -out %s -passin file:%s'


def convert_key_cer_to_pem(key, password):
    with tempfile.NamedTemporaryFile('wb', suffix='.key', prefix='edi.mx.tmp.') as key_file, \
            tempfile.NamedTemporaryFile('wb', suffix='.txt', prefix='edi.mx.tmp.') as pwd_file, \
            tempfile.NamedTemporaryFile('rb', suffix='.key', prefix='edi.mx.tmp.') as keypem_file:
        key_file.write(key)
        key_file.flush()
        pwd_file.write(password)
        pwd_file.flush()
        subprocess.call((KEY_TO_PEM_CMD % (key_file.name, keypem_file.name, pwd_file.name)).split())
        key_pem = keypem_file.read()
    return key_pem


def str_to_datetime(dt_str, tz=timezone('America/Mexico_City')):
    return tz.localize(fields.Datetime.from_string(dt_str))


class Certificate(models.Model):
    _name = 'einvoice.edi.certificate'

    content = fields.Binary(
        string='Certificate',
        required=True,
        attachment=False,)
    key = fields.Binary(
        string='Certificate Key',
        required=True,
        attachment=False,)
    password = fields.Char(
        string='Certificate Password',
        required=True,)
    serial_number = fields.Char(
        string='Serial number',
        readonly=True,
        index=True)
    date_start = fields.Datetime(
        string='Available date',
        readonly=True)
    date_end = fields.Datetime(
        string='Expiration date',
        readonly=True)

    @tools.ormcache('content')
    def get_pem_cer(self, content):
        self.ensure_one()
        return ssl.DER_cert_to_PEM_cert(base64.decodestring(content)).encode('UTF-8')

    @tools.ormcache('key', 'password')
    def get_pem_key(self, key, password):
        self.ensure_one()
        return convert_key_cer_to_pem(base64.decodestring(key), password.encode('UTF-8'))

    def get_data(self):
        self.ensure_one()
        cer_pem = self.get_pem_cer(self.content)
        certificate = crypto.load_certificate(crypto.FILETYPE_PEM, cer_pem)
        for to_del in ['\n', ssl.PEM_HEADER, ssl.PEM_FOOTER]:
            cer_pem = cer_pem.replace(to_del.encode('UTF-8'), b'')
        return cer_pem, certificate

    def get_mx_current_datetime(self):
        return fields.Datetime.context_timestamp(
            self.with_context(tz='America/Mexico_City'), fields.Datetime.now())

    def get_valid_certificate(self):
        mexican_dt = self.get_mx_current_datetime()
        for record in self:
            date_start = str_to_datetime(record.date_start)
            date_end = str_to_datetime(record.date_end)
            if date_start <= mexican_dt <= date_end:
                return record
        return None

    def get_encrypted_cadena(self, cadena):
        self.ensure_one()
        key_pem = self.get_pem_key(self.key, self.password)
        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
        encrypt = 'sha256WithRSAEncryption'
        cadena_crypted = crypto.sign(private_key, cadena, encrypt)
        return base64.b64encode(cadena_crypted)

    @api.constrains('content', 'key', 'password')
    def _check_credentials(self):
        mexican_tz = timezone('America/Mexico_City')
        mexican_dt = self.get_mx_current_datetime()
        date_format = '%Y%m%d%H%M%SZ'
        for record in self:
            # Try to decrypt the certificate
            try:
                cer_pem, certificate = record.get_data()
                before = mexican_tz.localize(
                    datetime.strptime(certificate.get_notBefore().decode("utf-8"), date_format))
                after = mexican_tz.localize(
                    datetime.strptime(certificate.get_notAfter().decode("utf-8"), date_format))
                serial_number = certificate.get_serial_number()
            except except_orm as exc_orm:
                raise exc_orm
            except Exception:
                raise ValidationError(_('El contenido del certificado es invalido.'))
            # Assign extracted values from the certificate
            record.serial_number = ('%x' % serial_number)[1::2]
            record.date_start = before.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record.date_end = after.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if mexican_dt > after:
                raise ValidationError(_('El certificado esta expirado desde %s') % record.date_end)
            # Check the pair key/password
            try:
                key_pem = self.get_pem_key(self.key, self.password)
                crypto.load_privatekey(crypto.FILETYPE_PEM, key_pem)
            except Exception:
                raise ValidationError(_('La llave y/o contraseña es/son invalidos.'))

    @api.model
    def create(self, data):
        res = super(Certificate, self).create(data)
        self.clear_caches()
        return res

    def write(self, data):
        res = super(Certificate, self).write(data)
        self.clear_caches()
        return res

    # def unlink(self):
    #     if self.env['account.move'].sudo().search(
    #             [('l10n_mx_edi_cfdi_name', '!=', False)], limit=1):
    #         raise UserError(_(
    #             'You cannot remove a certificate if at least an invoice has been signed. '
    #             'Expired Certificates will not be used as Odoo uses the latest valid certificate. '
    #             'To not use it, you can unlink it from the current company certificates.'))
    #     res = super(Certificate, self).unlink()
    #     self.clear_caches()
    #     return res
