"""Tests para src/articulos.py."""
import tempfile
import os
from src.articulos import ArticulosLoader


def _create_sql(rows: list[str]) -> str:
    """Crea un fichero SQL temporal con las filas dadas."""
    content = "INSERT INTO articulos VALUES\n" + ",\n".join(rows) + ";"
    fp = tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False, encoding='utf-8')
    fp.write(content)
    fp.close()
    return fp.name


def test_load_and_find_by_name():
    # Fila SQL: (id, ?, ?, id_proveedor, ?, tamano, ?, paquete, nombre, familia)
    sql = _create_sql([
        "(100, 0, 0, 435, 0, '60', 0, 25, 'ROSA EC EXPLORER 60CM 25U', 'ROSAS')",
    ])
    try:
        art = ArticulosLoader()
        n = art.load_from_sql(sql)
        assert n == 1
        a = art.find_by_name('ROSA EC EXPLORER 60CM 25U')
        assert a is not None
        assert a['id'] == 100
    finally:
        os.unlink(sql)


def test_load_empty_sql():
    sql = _create_sql([])
    try:
        art = ArticulosLoader()
        # El fichero no tiene filas que empiecen con "("
        n = art.load_from_sql(sql)
        assert n == 0
        assert art.find_by_name('NADA') is None
    finally:
        os.unlink(sql)


def test_find_rose_ec():
    sql = _create_sql([
        "(200, 0, 0, 435, 0, '60', 0, 25, 'ROSA EC MONDIAL 60CM 25U', 'ROSAS')",
    ])
    try:
        art = ArticulosLoader()
        art.load_from_sql(sql)
        a = art.find_rose_ec('MONDIAL', 60, 25)
        assert a is not None
        assert a['id'] == 200
        assert art.find_rose_ec('MONDIAL', 40, 25) is None
    finally:
        os.unlink(sql)
