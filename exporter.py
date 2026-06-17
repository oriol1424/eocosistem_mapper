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

COLUMNAS = ["Nombre", "Tipo", "Sector", "Descripción", "Web", "Ubicación", "Contacto"]

COLORES_CABECERA = {
    "Empresas privadas":        "1D6FA8",
    "Academia":                 "6B4FA8",
    "Administración pública":   "1A7A4A",
    "Sociedad civil organizada":"A85A1A"
}


def _estilo_cabecera(categoria: str):
    color = COLORES_CABECERA.get(categoria, "444444")
    fill = PatternFill("solid", fgColor=color)
    font = Font(bold=True, color="FFFFFF", size=11)
    alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    return fill, font, alignment


def _borde_fino():
    lado = Side(style="thin", color="CCCCCC")
    return Border(left=lado, right=lado, top=lado, bottom=lado)


def exportar_excel(resultados: dict, zona: str) -> bytes:
    """
    resultados: dict con clave = categoría, valor = lista de actores
    Devuelve bytes del Excel para descarga directa en Streamlit.
    """
    wb = Workbook()
    wb.remove(wb.active)

    for categoria in CATEGORIAS:
        actores = resultados.get(categoria, [])
        ws = wb.create_sheet(title=categoria[:31])

        ws.merge_cells("A1:G1")
        titulo_cell = ws["A1"]
        titulo_cell.value = f"{categoria} — {zona}"
        titulo_cell.font = Font(bold=True, size=13, color="FFFFFF")
        titulo_cell.fill = PatternFill("solid", fgColor=COLORES_CABECERA.get(categoria, "444444"))
        titulo_cell.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[1].height = 28

        fill, font, alignment = _estilo_cabecera(categoria)
        borde = _borde_fino()

        for col_idx, col_name in enumerate(COLUMNAS, start=1):
            cell = ws.cell(row=2, column=col_idx, value=col_name)
            cell.fill = fill
            cell.font = font
            cell.alignment = alignment
            cell.border = borde
        ws.row_dimensions[2].height = 22

        for row_idx, actor in enumerate(actores, start=3):
            fila = [
                actor.get("nombre", ""),
                actor.get("tipo", ""),
                actor.get("sector", ""),
                actor.get("descripcion", ""),
                actor.get("web", ""),
                actor.get("ubicacion", ""),
                actor.get("contacto", ""),
            ]
            bg = "F7F7F7" if row_idx % 2 == 0 else "FFFFFF"
            for col_idx, valor in enumerate(fila, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=valor or "")
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                cell.fill = PatternFill("solid", fgColor=bg)
                cell.border = borde

        anchos = [30, 22, 22, 50, 35, 20, 25]
        for col_idx, ancho in enumerate(anchos, start=1):
            ws.column_dimensions[get_column_letter(col_idx)].width = ancho

        ws.freeze_panes = "A3"

        if actores:
            ws.auto_filter.ref = f"A2:{get_column_letter(len(COLUMNAS))}{len(actores) + 2}"

        if not actores:
            ws.cell(row=3, column=1, value="No se encontraron actores para esta categoría.")

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
