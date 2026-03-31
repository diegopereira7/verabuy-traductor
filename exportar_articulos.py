import openpyxl, re

with open(r'C:\verabuy-traductor\articulos (3).sql', 'r', encoding='utf-8') as f:
    contenido = f.read()

wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Articulos'
ws.append(['ID', 'ID_ERP', 'ID_PROVEEDOR', 'NOMBRE', 'MARCA', 'TAMANO', 'COLOR', 'VARIEDAD', 'NOMBRE_PROVEEDOR', 'FAMILIA', 'PAQUETE'])

count = 0
for match in re.finditer(r'\((\d+),([^)]+)\)', contenido):
    try:
        vals = match.group(0)
        campos = []
        en_comilla = False
        campo = ''
        for c in vals[1:-1]:
            if c == chr(39) and not en_comilla:
                en_comilla = True
                campo = ''
            elif c == chr(39) and en_comilla:
                en_comilla = False
                campos.append(campo)
                campo = ''
            elif c == ',' and not en_comilla:
                if campo.strip():
                    campos.append(campo.strip())
                campo = ''
            elif en_comilla:
                campo += c
            else:
                campo += c
        if campo.strip():
            campos.append(campo.strip())

        if len(campos) >= 14:
            ws.append([
                campos[0],
                campos[1],
                campos[3],
                campos[8],
                campos[6],
                campos[5],
                campos[4],
                campos[14] if len(campos) > 14 else '',
                campos[13] if len(campos) > 13 else '',
                campos[9] if len(campos) > 9 else '',
                campos[7],
            ])
            count += 1
    except:
        pass

wb.save(r'C:\verabuy-traductor\articulos_verabuy.xlsx')
print(str(count) + ' articulos exportados')
