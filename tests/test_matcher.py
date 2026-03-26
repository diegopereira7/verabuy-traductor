"""Tests para src/matcher.py."""
from src.models import InvoiceLine
from src.matcher import split_mixed_boxes, rescue_unparsed_lines


def test_split_mixed_variety():
    line = InvoiceLine(variety='RED/YELLOW', stems=500, line_total=95.0, bunches=2)
    result = split_mixed_boxes([line])
    assert len(result) == 2
    assert result[0].variety == 'RED'
    assert result[1].variety == 'YELLOW'
    assert result[0].stems == 250
    assert result[1].line_total == 47.5
    assert result[0].box_type == 'MIX'


def test_split_no_slash():
    line = InvoiceLine(variety='EXPLORER', stems=100)
    result = split_mixed_boxes([line])
    assert len(result) == 1
    assert result[0].variety == 'EXPLORER'


def test_split_already_mixed():
    line = InvoiceLine(variety='RED/YELLOW', stems=500, box_type='MIX')
    result = split_mixed_boxes([line])
    assert len(result) == 1  # Already marked, not split again


def test_rescue_finds_product_line():
    text = "Header line\n1 QB HYDRANGEA WHITE PREMIUM ATPDEA 0603190125 35 35 0.580 20.30\nFooter"
    result = rescue_unparsed_lines(text, [])
    assert len(result) == 1
    assert result[0].match_status == 'sin_parser'


def test_rescue_skips_noise():
    text = "Total USD 1959.35"
    result = rescue_unparsed_lines(text, [])
    assert len(result) == 0


def test_rescue_skips_already_parsed():
    text = "1 QB HYDRANGEA WHITE 35 35 0.580 20.30\n"
    parsed = [InvoiceLine(raw_description="1 QB HYDRANGEA WHITE 35 35 0.580 20.30")]
    result = rescue_unparsed_lines(text, parsed)
    assert len(result) == 0
