"""Ejecuta un programa ejecutable (SE38 → F8) con valores en la pantalla de selección y devuelve el resultado.

Argumentos:
  programa    nombre del programa
  parametros  {"P_CAMPO": "valor", "S_RANGO-LOW": "valor", "P_CHECK": "X"}  (opcional; se escriben tal cual)
  ejecutar    True (por defecto): F8 tras llenar la pantalla; False: solo llena y devuelve la pantalla de selección
Devuelve:
  seleccion   etiquetas y valores visibles de la pantalla de selección ({nombre: {"etiqueta", "valor"}})
  lista       líneas de la lista ABAP resultante (si la hubo), con el espaciado real
  barra_estado, en_seleccion (True si quedó en la pantalla de selección, p. ej. por un error de validación)
No ejecuta en fondo ni guarda variantes. Si el programa abre un ALV u otra pantalla, devuelve el título y la barra de estado;
léela después con leer_pantalla.
"""
import re

import utilidades as u

ESCRIBE = True  # un report puede modificar datos si el propio programa lo hace: se trata como escritura


def _seleccion(session):
    out = {}
    for o in u.hijos(session.findById("wnd[0]/usr")):
        m = re.match(r".*/(txt|ctxt|chk|rad|cmb)(.+)$", o.Id)
        if not m:
            continue
        nombre = m.group(2)
        if nombre.startswith("%_"):
            p = re.match(r"%_(.+?)_%_APP_%-TEXT", nombre)
            if p:
                out.setdefault(p.group(1), {})["etiqueta"] = o.Text
            continue
        valor = o.Selected if m.group(1) in ("chk", "rad") else o.Text
        out.setdefault(nombre, {})["valor"] = valor
        if m.group(1) in ("chk", "rad"):
            out[nombre]["etiqueta"] = o.Text
    return out


def run(session, programa, parametros=None, ejecutar=True):
    u.tx(session, "SE38")
    session.findById("wnd[0]/usr/ctxtRS38M-PROGRAMM").text = programa.upper()
    session.findById("wnd[0]").sendVKey(8)
    u.esperar(session)
    titulo_sel = session.findById("wnd[0]").Text
    for nombre, valor in (parametros or {}).items():
        id_base = None
        for pref in ("ctxt", "txt", "chk", "rad", "cmb"):
            if u.existe(session, f"wnd[0]/usr/{pref}{nombre.upper()}"):
                id_base = f"wnd[0]/usr/{pref}{nombre.upper()}"
                break
        if id_base is None:
            raise RuntimeError(f"No se encontró el campo {nombre} en la pantalla de selección")
        o = session.findById(id_base)
        if o.Type == "GuiCheckBox":
            o.Selected = str(valor).upper() in ("X", "1", "TRUE")
        elif o.Type == "GuiRadioButton":
            o.Select()
        elif o.Type == "GuiComboBox":
            o.Key = str(valor)
        else:
            o.Text = str(valor)
    res = {"titulo_seleccion": titulo_sel, "seleccion": _seleccion(session)}
    if not ejecutar:
        return res
    session.findById("wnd[0]").sendVKey(8)
    u.esperar(session)
    res["barra_estado"] = u.barra_estado(session)
    res["titulo"] = session.findById("wnd[0]").Text
    # La lista suele tener el mismo título que la selección: se decide por el contenido de la pantalla
    ids = [o.Id for o in u.hijos(session.findById("wnd[0]/usr"))]
    res["en_seleccion"] = any("_%_APP_%" in i for i in ids)
    if not res["en_seleccion"]:
        res["lista"] = u.leer_lista(session)
    return res
