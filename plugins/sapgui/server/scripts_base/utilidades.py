"""Utilidades comunes para scripts de SAP GUI Scripting.

Importar desde cualquier script con:  import utilidades as u
Todas las funciones reciben la sesión (GuiSession) que entrega el servidor.
Se puede adaptar copiándola a la carpeta de scripts del usuario con el mismo nombre.
"""
from __future__ import annotations

import time

ESCRIBE = False


def hijos(o) -> list:
    """Hijos de un contenedor como lista (las colecciones COM se recorren por índice)."""
    c = o.Children
    return [c(i) for i in range(c.Count)]


def existe(session, id_control: str) -> bool:
    return session.findById(id_control, False) is not None


def buscar(session, id_control: str):
    """findById que devuelve None en vez de lanzar error."""
    return session.findById(id_control, False)


def tx(session, tcode: str) -> None:
    """Ejecuta /n<tcode>. Con tcode vacío vuelve al menú."""
    session.findById("wnd[0]/tbar[0]/okcd").text = "/n" + tcode
    session.findById("wnd[0]").sendVKey(0)
    esperar(session)


def enter(session, ventana: str = "wnd[0]") -> None:
    session.findById(ventana).sendVKey(0)
    esperar(session)


def esperar(session, segundos: float = 30) -> None:
    """Espera a que la sesión deje de estar ocupada."""
    fin = time.time() + segundos
    while session.Busy and time.time() < fin:
        time.sleep(0.2)


def barra_estado(session) -> dict:
    sb = session.findById("wnd[0]/sbar")
    return {"texto": sb.Text, "tipo": sb.MessageType}


def popup(session, n: int = 1):
    """Devuelve wnd[n] si hay un popup abierto, si no None."""
    return session.findById(f"wnd[{n}]", False)


def botones_popup(session, n: int = 1) -> list[dict]:
    """Botones de un popup: id y texto (útil para decidir cuál presionar)."""
    w = popup(session, n)
    if w is None:
        return []
    out = []

    def rec(o):
        if o.Type == "GuiButton":
            out.append({"id": o.Id.split(session.Id + "/")[-1], "texto": o.Text, "tooltip": o.Tooltip})
        if o.ContainerType:
            for h in hijos(o):
                rec(h)

    rec(w)
    return out


def responder_popup_no_grabar(session) -> str | None:
    """Si SAP pregunta por cambios sin grabar (popup estándar SPOP), responde 'No'.
    Devuelve el texto del popup o None si no había. Lanza error si el segundo botón no es 'No'."""
    w = popup(session)
    if w is None:
        return None
    b2 = session.findById("wnd[1]/usr/btnSPOP-OPTION2", False)
    if b2 is None or "no" not in b2.Text.lower():
        raise RuntimeError(f"Popup inesperado '{w.Text}': no se responde automáticamente.")
    titulo = w.Text
    b2.press()
    esperar(session)
    return titulo


def buscar_tipo(raiz, tipo: str, subtipo: str | None = None, max_nivel: int = 12):
    """Primer control de 'tipo' (y 'subtipo' para GuiShell) bajo 'raiz', o None."""

    def rec(o, d):
        if d > max_nivel:
            return None
        try:
            if o.Type == tipo and (subtipo is None or getattr(o, "SubType", None) == subtipo):
                return o
            if o.ContainerType:
                for h in hijos(o):
                    r = rec(h, d + 1)
                    if r is not None:
                        return r
        except Exception:  # noqa: BLE001
            return None
        return None

    return rec(raiz, 0)


def editor_abap(session):
    """Encuentra el editor de código de la pantalla actual (editor ABAP nuevo o editor de texto antiguo)."""
    usr = session.findById("wnd[0]/usr")
    ed = buscar_tipo(usr, "GuiShell", "AbapEditor")
    if ed is None:
        ed = buscar_tipo(usr, "GuiShell", "TextEdit")
    if ed is None:
        raise RuntimeError("No se encontró un editor de código en la pantalla.")
    return ed


def leer_editor(ed) -> list[str]:
    """Líneas del editor (AbapEditor o TextEdit)."""
    if ed.SubType == "AbapEditor":
        return [ed.GetLineText(i) for i in range(1, ed.GetLineCount() + 1)]
    return [ed.GetLineText(i) for i in range(ed.LineCount)]


def filas_tabla_control(session, id_tabla: str, columnas: tuple = (0,), max_filas: int = 2000):
    """Recorre TODAS las filas de un table control (tbl...) desplazando el scroll.
    Devuelve [(fila_absoluta, [textos de 'columnas'])] solo de filas con algún dato.
    Vuelve a buscar el control tras cada desplazamiento (SAP lo recrea)."""
    t = session.findById(id_tabla)
    total, vis = t.RowCount, max(t.VisibleRowCount, 1)
    out, pos = [], 0
    while pos < min(total, max_filas):
        session.findById(id_tabla).verticalScrollbar.position = pos
        t = session.findById(id_tabla)
        for r in range(vis):
            vals = []
            for c in columnas:
                try:
                    vals.append(t.GetCell(r, c).Text.strip())
                except Exception:  # noqa: BLE001  (fila vacía o fuera de rango)
                    vals.append("")
            if any(vals):
                out.append((pos + r, vals))
        pos += vis
    return out


def activar_solo(session, nombres) -> list[dict]:
    """En el popup 'Objetos inactivos' (wnd[1]) marca SOLO los objetos cuyo nombre está en 'nombres'
    (recorre todas las pestañas y todas las filas) y presiona Continuar. Devuelve lo que había y lo marcado."""
    nombres = {n.upper() for n in ([nombres] if isinstance(nombres, str) else nombres)}
    p = session.findById("wnd[1]")
    ts = buscar_tipo(p, "GuiTabStrip")
    tabs = [ts.Children(i).Id for i in range(ts.Children.Count)] if ts is not None else [None]
    vistos = []
    for tab_id in tabs:
        if tab_id:
            session.findById(tab_id).select()
            esperar(session)
        cont = session.findById(tab_id) if tab_id else session.findById("wnd[1]")
        t = buscar_tipo(cont, "GuiTableControl")
        if t is None:
            continue
        tid = t.Id.split(session.Id + "/")[-1]
        for fila, (tipo, nombre) in filas_tabla_control(session, tid, (1, 2)):
            marcar = nombre.upper() in nombres
            session.findById(tid).GetAbsoluteRow(fila).Selected = marcar
            vistos.append({"tipo": tipo, "nombre": nombre, "marcado": marcar})
    session.findById("wnd[1]/tbar[0]/btn[0]").press()
    esperar(session)
    return vistos


def leer_lista(session, ventana: str = "wnd[0]") -> list[str]:
    """Lee una lista ABAP clásica (WRITE) como líneas de texto, respetando columnas:
    los controles se llaman lbl[col,fila] / txt[col,fila], así que se reconstruye el espaciado real."""
    usr = session.findById(f"{ventana}/usr")
    celdas = {}
    import re  # noqa: PLC0415

    for o in hijos(usr):
        m = re.search(r"\[(\d+),(\d+)\]$", o.Id)
        if not m:
            continue
        col, fila = int(m.group(1)), int(m.group(2))
        celdas.setdefault(fila, []).append((col, o.Text))
    lineas = []
    for fila in sorted(celdas):
        linea = ""
        for col, txt in sorted(celdas[fila]):
            linea = linea.ljust(col) + txt
        lineas.append(linea.rstrip())
    return lineas


def leer_grid(grid, max_filas: int = 1000) -> dict:
    """Lee un ALV grid (GuiShell subtipo GridView): columnas y filas como listas."""
    cols_obj = grid.ColumnOrder
    cols = [cols_obj(i) for i in range(cols_obj.Count)]
    n = min(grid.RowCount, max_filas)
    filas = []
    for r in range(n):
        if r % 20 == 0:
            grid.firstVisibleRow = r  # fuerza la carga de las filas visibles
        filas.append([grid.GetCellValue(r, c) for c in cols])
    return {"columnas": cols, "filas": filas, "total": grid.RowCount, "leidas": n}
