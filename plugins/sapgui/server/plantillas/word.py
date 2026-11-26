"""Documentos Word (EF, ET, dictamen QA) con formato fijo a partir de un JSON por secciones.

Contenido:
{
  "titulo": "Especificación funcional: ajuste del programa Z_EJEMPLO",
  "subtitulo": "Una línea que resume el requerimiento.",
  "ficha": {"Objeto": "Z_EJEMPLO", "Módulo": "SD", "Fecha": "26.11.2026", "Elaborado por": "...", "Estado": "Borrador"},
  "secciones": [{"titulo": "Objetivo", "bloques": [ ...bloques... ]}]
}
Bloques: parrafo{texto} · lista{items, numerada:bool} · tabla{columnas, filas} · codigo{codigo}
· nota{texto} · subseccion{titulo, bloques}.
Texto en línea: **negrita** y `código`. Las secciones se numeran solas (1., 2., 2.1 ...).
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor, Twips

from .marca import data_uri, hex_rgb  # noqa: F401  (data_uri reservado para logos en encabezado)

FUENTE = "Calibri"
MONO = "Consolas"
GRIS_ZEBRA = "F2F2F2"
GRIS_TEXTO = RGBColor(0x7F, 0x7F, 0x7F)


def _rgb(h: str) -> RGBColor:
    return RGBColor(*hex_rgb(h))


def _sombrear(celda, color_hex: str) -> None:
    tcPr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex.lstrip("#"))
    tcPr.append(shd)


def _bordes(tabla, color="BFBFBF") -> None:
    tblPr = tabla._tbl.tblPr
    b = OxmlElement("w:tblBorders")
    for lado in ("top", "left", "bottom", "right", "insideH", "insideV"):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), "4")
        e.set(qn("w:color"), color)
        b.append(e)
    tblPr.append(b)


def _runs(p, texto: str, size: float | None = None, bold: bool | None = None, color: RGBColor | None = None) -> None:
    for parte in re.split(r"(\*\*[^*]+\*\*|`[^`]+`)", str(texto)):
        if not parte:
            continue
        if parte.startswith("**") and parte.endswith("**"):
            r = p.add_run(parte[2:-2])
            r.bold = True
        elif parte.startswith("`") and parte.endswith("`"):
            r = p.add_run(parte[1:-1])
            r.font.name = MONO
            r._element.rPr.rFonts.set(qn("w:eastAsia"), MONO)
        else:
            r = p.add_run(parte)
            if bold is not None:
                r.bold = bold
        if size:
            r.font.size = Pt(size)
        if color is not None:
            r.font.color.rgb = color


def _tabla(doc, columnas, filas, primario: str, primera_col_gris=False, size=9.5) -> None:
    t = doc.add_table(rows=1, cols=len(columnas))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _bordes(t)
    for i, c in enumerate(columnas):
        cel = t.rows[0].cells[i]
        _sombrear(cel, primario)
        p = cel.paragraphs[0]
        _runs(p, c, size=size, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    # repetir encabezado en cada página
    trPr = t.rows[0]._tr.get_or_add_trPr()
    h = OxmlElement("w:tblHeader")
    h.set(qn("w:val"), "true")
    trPr.append(h)
    for n, fila in enumerate(filas):
        celdas = t.add_row().cells
        for i in range(len(columnas)):
            val = fila[i] if i < len(fila) else ""
            p = celdas[i].paragraphs[0]
            lineas = str(val).split("\n")
            for k, ln in enumerate(lineas):
                if k:
                    p = celdas[i].add_paragraph()
                _runs(p, ln, size=size)
            if (primera_col_gris and i == 0) or (not primera_col_gris and n % 2 == 1):
                _sombrear(celdas[i], GRIS_ZEBRA)
            if primera_col_gris and i == 0:
                for r in celdas[i].paragraphs[0].runs:
                    r.bold = True
    _anchos(t, columnas, primera_col_gris)
    doc.add_paragraph()


ANCHO_UTIL = 11906 - 2 * 1100  # twips de texto en A4 con los márgenes del documento
ANGOSTAS = {"nº": 600, "n°": 600, "#": 600, "severidad": 1300, "estado": 1300, "cumple": 1000, "tipo": 1300,
            "resultado": 1500, "orden": 1100}


def _anchos(t, columnas, es_ficha: bool) -> None:
    """Columnas angostas para Nº/estado y el resto repartido; en la ficha, 'Dato' más angosto."""
    fijos = {}
    for i, c in enumerate(columnas):
        if es_ficha and i == 0:
            fijos[i] = 2600
        elif str(c).strip().lower() in ANGOSTAS:
            fijos[i] = ANGOSTAS[str(c).strip().lower()]
    libres = [i for i in range(len(columnas)) if i not in fijos]
    resto = max(ANCHO_UTIL - sum(fijos.values()), 1000)
    anchos = [fijos.get(i, resto // max(len(libres), 1)) for i in range(len(columnas))]
    t.autofit = False
    for fila in t.rows:
        for i, cel in enumerate(fila.cells):
            cel.width = Twips(anchos[i])


def _bloques(doc, bloques, primario: str, nivel_prefijo: str) -> None:
    sub = 0
    for b in bloques:
        t = b.get("tipo", "parrafo")
        if t == "parrafo":
            _runs(doc.add_paragraph(), b.get("texto", ""))
        elif t == "lista":
            estilo = "List Number" if b.get("numerada") else "List Bullet"
            for it in b.get("items", []):
                _runs(doc.add_paragraph(style=estilo), it)
        elif t == "tabla":
            _tabla(doc, b.get("columnas", []), b.get("filas", []), primario)
        elif t == "codigo":
            for ln in str(b.get("codigo", "")).replace("\r\n", "\n").split("\n"):
                p = doc.add_paragraph()
                p.paragraph_format.space_after = Pt(0)
                r = p.add_run(ln if ln else " ")
                r.font.name = MONO
                r.font.size = Pt(9)
            doc.add_paragraph()
        elif t == "nota":
            p = doc.add_paragraph()
            _runs(p, b.get("texto", ""), size=9.5, color=GRIS_TEXTO)
        elif t == "subseccion":
            sub += 1
            doc.add_heading(f"{nivel_prefijo}.{sub} {b.get('titulo', '')}", level=2)
            _bloques(doc, b.get("bloques", []), primario, f"{nivel_prefijo}.{sub}")
        else:
            raise ValueError(f"Tipo de bloque desconocido: {t}")


def _campo_pagina(p) -> None:
    for tipo, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        r = p.add_run()
        if tipo:
            f = OxmlElement("w:fldChar")
            f.set(qn("w:fldCharType"), tipo)
            r._r.append(f)
        else:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = txt
            r._r.append(it)


def generar(contenido: dict, marca: dict, ruta: str) -> str:
    primario = marca["colores"]["primario"]
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Twips(11906), Twips(16838)  # A4
    sec.top_margin = sec.bottom_margin = Twips(1000)
    sec.left_margin = sec.right_margin = Twips(1100)

    st = doc.styles["Normal"]
    st.font.name = FUENTE
    st.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
    st.font.size = Pt(10.5)
    for nombre, size in (("Title", 18), ("Heading 1", 13), ("Heading 2", 11)):
        s = doc.styles[nombre]
        s.font.name = FUENTE
        rf = s.element.get_or_add_rPr().get_or_add_rFonts()
        for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            rf.set(qn(a), FUENTE)
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rf.get(qn(a)) is not None:
                del rf.attrib[qn(a)]
        s.font.size = Pt(size)
        s.font.bold = True
        s.font.color.rgb = _rgb(primario) if nombre != "Title" else RGBColor(0, 0, 0)
        s.paragraph_format.space_before = Pt(14 if nombre == "Heading 1" else 8)
        s.paragraph_format.space_after = Pt(4)

    t = doc.add_paragraph(style="Title")
    t.add_run(contenido.get("titulo", "Documento"))
    pPr = t._p.get_or_add_pPr()
    for el in pPr.findall(qn("w:pBdr")):
        pPr.remove(el)
    if contenido.get("subtitulo"):
        _runs(doc.add_paragraph(), contenido["subtitulo"], size=10.5, color=GRIS_TEXTO)

    ficha = contenido.get("ficha") or {}
    if ficha:
        _tabla(doc, ["Dato", "Detalle"], [[k, v] for k, v in ficha.items()], primario, primera_col_gris=True)

    for i, s in enumerate(contenido.get("secciones", []), 1):
        doc.add_heading(f"{i}. {s.get('titulo', '')}", level=1)
        _bloques(doc, s.get("bloques", []), primario, str(i))

    pie = sec.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    txt = " · ".join(x for x in (marca.get("empresa", ""), contenido.get("titulo", "")) if x)
    r = pie.add_run(f"{txt} · Página " if txt else "Página ")
    r.font.size = Pt(8)
    r.font.color.rgb = GRIS_TEXTO
    _campo_pagina(pie)

    p = Path(ruta).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(p))
    return str(p)
