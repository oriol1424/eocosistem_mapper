import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

CATEGORIAS = [
    "Empresas privadas",
    "Academia",
    "Administración pública",
    "Sociedad civil organizada"
]

COLUMNAS_POR_CATEGORIA = {
    "Empresas privadas": ["Nombre", "Tipo", "Sector", "Descripción", "Web", "Dirección", "Teléfono", "Ubicación"],
    "Academia": ["Nombre", "Tipo", "Sector", "Descripción", "Web", "Dirección", "Teléfono", "Ubicación"],
    "Administración pública": ["Nombre", "Tipo", "Descripción", "Web", "Dirección", "Teléfono", "Horarios", "Ubicación"],
    "Sociedad civil organizada": ["Nombre", "Tipo", "Sector", "Descripción", "Web", "Dirección", "Teléfono", "Ubicación"],
}

CAMPOS_POR_CATEGORIA = {
    "Empresas privadas": ["nombre", "tipo", "sector", "descripcion", "web", "direccion", "contacto", "ubicacion"],
    "Academia": ["nombre", "tipo", "sector", "descripcion", "web", "direccion", "contacto", "ubicacion"],
    "Administración pública": ["nombre", "tipo", "descripcion", "web", "direccion", "contacto", "horarios", "ubicacion"],
    "Sociedad civil organizada": ["nombre", "tipo", "sector", "descripcion", "web", "direccion", "contacto", "ubicacion"],
}

COLORES_CABECERA = {
    "Empresas privadas":        "1D6FA8",
    "Academia":                 "6B4FA8",
    "Administración pública":   "1A7A4A",
    "Sociedad civil organizada":"A85A1A"
}


def _borde_fino():
    lado = Side(style="thin", color="CCCCCC")
    return Border(left=lado, right=lado, top=lado, bottom=lado)


def exportar_excel(resultados: dict, zona: str) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)

    for categoria in CATEGORIAS:
        actores = resultados.get(categoria, [])
        ws = wb.create_sheet(title=categoria[:31])
        color = COLORES_CABECERA.get(categoria, "444444")
        columnas = COLUMNAS_POR_CATEGORIA[categoria]
        campos = CAMPOS_POR_CATEGORIA[categoria]

        # Título
        ws.merge_cells(f"A1:{get_column_letter(len(columnas))}1")
        cell = ws["A1"]
        cell.value = f"{categoria} — {zona}"
        cell.font = Font(bold=True, size=13, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=color)
        cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 28

        # Cabecera
        fill = PatternFill("solid", fgColor=color)
        font_cab = Font(bold=True, color="FFFFFF", size=11)
        align_cab = Alignment(horizontal="center", vertical="center", wrap_text=True)
        borde = _borde_fino()

        for col_idx, col_name in enumerate(columnas, start=1):
            cell = ws.cell(row=2, column=col_idx, value=col_name)
            cell.fill = fill
            cell.font = font_cab
            cell.alignment = align_cab
            cell.border = borde
        ws.row_dimensions[2].height = 22

        # Datos
        for row_idx, actor in enumerate(actores, start=3):
            bg = "F7F7F7" if row_idx % 2 == 0 else "FFFFFF"
            for col_idx, campo in enumerate(campos, start=1):
                valor = actor.get(campo, "") or ""
                cell = ws.cell(row=row_idx, column=col_idx, value=valor)
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                cell.fill = PatternFill("solid", fgColor=bg)
                cell.border = borde

        # Anchos de columna
        anchos = [30, 22, 22, 50, 35, 35, 20, 20]
        for col_idx, ancho in enumerate(anchos[:len(columnas)], start=1):
            ws.column_dimensions[get_column_letter(col_idx)].width = ancho

        ws.freeze_panes = "A3"

        if actores:
            ws.auto_filter.ref = f"A2:{get_column_letter(len(columnas))}{len(actores) + 2}"

        if not actores:
            ws.cell(row=3, column=1, value="No se encontraron actores para esta categoría.")

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
