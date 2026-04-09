"""Tests para src/models.py."""
from src.models import InvoiceLine, InvoiceHeader


def test_expected_name_rosa_ec():
    line = InvoiceLine(species='ROSES', variety='Explorer', size=60, stems_per_bunch=25, origin='EC')
    assert line.expected_name() == "ROSA EC EXPLORER 60CM 25U"


def test_expected_name_carnation():
    line = InvoiceLine(species='CARNATIONS', variety='White', size=70, stems_per_bunch=20, grade='FANCY', origin='COL')
    assert line.expected_name() == "CLAVEL COL FANCY BLANCO 70CM 20U"


def test_expected_name_hydrangea_latin():
    line = InvoiceLine(species='HYDRANGEAS', variety='PREMIUM BLANCO', provider_key='latin')
    assert line.expected_name() == "HYDRANGEA PREMIUM BLANCO 60CM 1U LATIN"


def test_match_key():
    line = InvoiceLine(species='ROSES', variety='Explorer', size=60, stems_per_bunch=25)
    assert line.match_key() == "ROSES|EXPLORER|60|25|"


def test_invoice_header_defaults():
    h = InvoiceHeader()
    assert h.invoice_number == ''
    assert h.total == 0.0


def test_expected_name_empty_variety():
    line = InvoiceLine(species='GYPSOPHILA', variety='MILLION STAR')
    assert line.expected_name() == "PANICULATA MILLION STAR"
