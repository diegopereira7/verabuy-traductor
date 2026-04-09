"""Tests para src/config.py."""
from src.config import (
    translate_carnation_color, strip_provider_suffix,
    PROVIDERS, BASE_DIR, SQL_FILE,
)


def test_translate_color_simple():
    assert translate_carnation_color('WHITE') == 'BLANCO'
    assert translate_carnation_color('red') == 'ROJO'


def test_translate_color_compound():
    assert translate_carnation_color('DARK RED') == 'OSCURO ROJO'


def test_translate_color_unknown():
    assert translate_carnation_color('FUCHSIA') == 'FUCHSIA'


def test_strip_provider_suffix():
    assert strip_provider_suffix('ROSA EC EXPLORER 60CM 25U CANTIZA') == 'ROSA EC EXPLORER 60CM 25U'


def test_strip_provider_suffix_no_suffix():
    assert strip_provider_suffix('ROSA EC EXPLORER 60CM 25U') == 'ROSA EC EXPLORER 60CM 25U'


def test_providers_has_cantiza():
    assert 'cantiza' in PROVIDERS
    assert PROVIDERS['cantiza']['id'] == 2222


def test_base_dir_exists():
    assert BASE_DIR.exists()
