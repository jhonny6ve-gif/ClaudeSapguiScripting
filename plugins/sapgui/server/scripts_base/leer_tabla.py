"""Lee una tabla con SE16N en modo visualizar.

Argumentos:
  tabla      nombre de la tabla
  filtros    {"CAMPO": "valor"}: valor simple (igualdad, campo 'Valor inferior'); acepta comodines * de SE16N
  max_filas  máximo de filas a traer (por defecto 200)
  ruta_csv   opcional: guarda el resultado en CSV (separador ;, UTF-8)
Devuelve columnas (nombres técnicos) y filas. Si no hay datos, devuelve el mensaje de la barra de estado.
"""
import csv

import utilidades as u

ESCRIBE = False
TC = "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC"


def _poner_filtro(session, campo, valor):
    t = session.findById(TC)
    total, vis = t.RowCount, t.VisibleRowCount
    pos = 0
    while pos < total:
        session.findById(TC).verticalScrollbar.position = pos
        t = session.findById(TC)
        for r in range(vis):
            fn = t.findById(f"txtGS_SELFIELDS-FIELDNAME[6,{r}]", False)
            if fn is not None and fn.Text.strip().upper() == campo:
                t.findById(f"ctxtGS_SELFIELDS-LOW[2,{r}]").text = valor
                return
        pos += vis
    raise RuntimeError(f"Campo {campo} no encontrado en la pantalla de selección")


def run(session, tabla, filtros=None, max_filas=200, ruta_csv=None):
    tabla = tabla.upper()
    u.tx(session, "SE16N")
    session.findById("wnd[0]/usr/ctxtGD-TAB").text = tabla
    u.enter(session)
    session.findById("wnd[0]/usr/txtGD-MAX_LINES").text = str(max_filas)
    edit = u.buscar(session, "wnd[0]/usr/chkGD-EDIT")
    if edit is not None:
        edit.selected = False
    for campo, valor in (filtros or {}).items():
        _poner_filtro(session, campo.upper(), str(valor))
    session.findById("wnd[0]/tbar[1]/btn[8]").press()
    u.esperar(session)
    grid = u.buscar(session, "wnd[0]/usr/cntlRESULT_LIST/shellcont/shell")
    if grid is None:
        msg = u.barra_estado(session)["texto"]
        u.tx(session, "")
        return {"tabla": tabla, "sin_datos": True, "mensaje": msg}
    datos = u.leer_grid(grid, max_filas)
    if ruta_csv:
        with open(ruta_csv, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(datos["columnas"])
            w.writerows(datos["filas"])
    u.tx(session, "")
    return {"tabla": tabla, **datos, "guardado_en": ruta_csv}
