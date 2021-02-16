# -*- coding: utf-8 -*-

from odoo import _, api, fields, models, tools


class ResCompany(models.Model):
    _inherit = "res.company"

    # edi_certificate = fields.Binary(
    #     string="Certificado (*.cer)"
    # )
    # edi_certificate_key = fields.Binary(
    #     string="Llave de Certificado (*.key)"
    # )
    # edi_certificate_pass = fields.Char(
    #     string="Contraseña del Certificado"
    # )
    edi_user_bd = fields.Char(
        string = "Usuario BD"
        )
    edi_passw_bd = fields.Char(
        string = "Contraseña BD"
        )
    edi_url_bd = fields.Char(
        string = "URL BD"
        )
    edi_name_bd = fields.Char(
        string = "Nombre BD"
        )

    edi_user_pac = fields.Char(
        string="Usuario para PAC."
    )
    edi_pass_pac = fields.Char(
        string="Contraseña para PAC."
    )
    edi_test_pac = fields.Boolean(
        string="Modo de Prueba",
        default=False
    )
    edi_certificate_ids = fields.Many2many("einvoice.edi.certificate", readonly=False,
                                           string='Certificados MX')
    
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
        string="Fiscal Regime",
        help="It is used to fill Mexican XML CFDI"
        "Comprobante.Emisor.RegimenFiscal."
        )

    # c_serial_number = fields.Char(
    #     string='Serial number',
    #     help='The serial number to add to electronic documents',
    #     readonly=True,
    #     index=True)
    # c_date_start = fields.Datetime(
    #     string='Available date',
    #     help='The date on which the certificate starts to be valid',
    #     readonly=True)
    # c_date_end = fields.Datetime(
    #     string='Expiration date',
    #     help='The date on which the certificate expires',
    #     readonly=True)
