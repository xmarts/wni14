# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from os.path import join, dirname, realpath
from odoo import tools

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    _load_product_sat_catalog(cr, registry)
    _assign_codes_uom(cr, registry)


def uninstall_hook(cr, registry):

    cr.execute("DELETE FROM edi_product_sat_code;")
    cr.execute("""DELETE FROM ir_model_data
               WHERE model='edi.product.sat.code';""")


def _load_product_sat_catalog(cr, registry):
    """Import CSV data as it is faster than xml and because we can't use
    noupdate anymore with csv"""
    csv_path = join(dirname(realpath(__file__)), 'data',
                    'edi.product.sat.code.csv')
    csv_file = open(csv_path, 'rb')
    cr.copy_expert(
        """COPY edi_product_sat_code(code, name, applies_to, active)
           FROM STDIN WITH DELIMITER '|'""", csv_file)
    # Create xml_id, to allow make reference to this data
    print("EJECUTA INSERT ||||||||||||||")
    cr.execute("""INSERT INTO ir_model_data
               (name, res_id, module, model, noupdate)
               SELECT concat('prod_code_sat_', code),
               id,
               'xmarts_l10n_einvoice_mx',
               'edi.product.sat.code',
               true
               FROM edi_product_sat_code """)


def _assign_codes_uom(cr, registry):
    """Assign the codes in UoM of each data, this is here because the data is
    created in the last method"""
    tools.convert.convert_file(cr, 'xmarts_l10n_einvoice_mx', 'data/product_data.xml',
                               None, mode='init', kind='data')
