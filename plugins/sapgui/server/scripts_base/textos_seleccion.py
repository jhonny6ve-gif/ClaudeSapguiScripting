"""Mantiene los textos de selección de un programa (SE38 > Elementos de texto > Textos de selección), graba y activa.

Uso (ejecutar_script "textos_seleccion"):
  {"programa": "ZPROG", "textos": {"P_TEXTO": "Texto", "S_BUKRS": "Sociedad"}, "activar": true}

Argumentos:
  programa  nombre del programa
  textos    dict {PARAMETRO/SELECT-OPTION: texto}; solo se modifican esas filas (el resto queda igual).
            Los nombres deben existir en la pestaña (el programa debe estar activo con esos PARAMETERS).
  activar   True (por defecto): Ctrl+F3 tras grabar. Si aparece la lista de objetos inactivos, marca SOLO
            las entradas cuyo nombre es exactamente 'programa' y desmarca las demás (otros objetos del usuario
            quedan inactivos y sin tocar).
Devuelve: {"grabar": barra de estado, "activar": barra de estado, "objetos_inactivos": [...], "textos": {leídos tras grabar}}.
Si falta un nombre o aparece un popup no reconocido, se detiene y lo informa.
Probado en ECC 6.0, SE38 en español (dynpro SAPLSETXP 1310, popup SAPLSEWORKINGAREA).
"""
import utilidades as u

ESCRIBE = True

TAB = "wnd[0]/usr/tabsTX_TABSTR_CONTROL/tabpSSSS"


def _tabla_id(session):
    t = u.buscar_tipo(session.findById(TAB), "GuiTableControl")
    return t.Id.split(session.Id + "/")[-1]


def _leer_textos(session):
    return {n: tx for _, (n, tx) in u.filas_tabla_control(session, _tabla_id(session), (0, 1)) if n}


def run(session, programa, textos, activar=True):
    programa = programa.upper()
    textos = {k.upper(): v for k, v in textos.items()}
    u.tx(session, "SE38")
    session.findById("wnd[0]/usr/ctxtRS38M-PROGRAMM").text = programa
    session.findById("wnd[0]/usr/radRS38M-FUNC_TEXT").select()
    session.findById("wnd[0]/usr/btnCHAP").press()
    u.esperar(session)
    if u.popup(session):
        return {"error": "popup al entrar", "titulo": session.findById("wnd[1]").Text,
                "botones": u.botones_popup(session)}
    if not u.existe(session, TAB):
        return {"error": "no se abrió Elementos de texto en modo Modificar", "barra": u.barra_estado(session)}
    session.findById(TAB).select()
    u.esperar(session)
    tid = _tabla_id(session)
    filas = {n: f for f, (n,) in u.filas_tabla_control(session, tid, (0,))}
    faltan = [k for k in textos if k not in filas]
    if faltan:
        return {"error": "nombres no encontrados en la pestaña", "faltan": faltan, "existentes": list(filas)}
    for nombre, texto in textos.items():
        session.findById(tid).verticalScrollbar.position = filas[nombre]
        session.findById(tid).GetCell(0, 1).Text = texto
    session.findById("wnd[0]").sendVKey(11)  # grabar
    u.esperar(session)
    res = {"grabar": u.barra_estado(session)}
    if u.popup(session):
        res.update(error="popup tras grabar", titulo=session.findById("wnd[1]").Text, botones=u.botones_popup(session))
        return res
    res["textos"] = _leer_textos(session)
    if activar:
        session.findById("wnd[0]").sendVKey(27)  # activar
        u.esperar(session)
        p = u.popup(session)
        if p and "inactivos" in p.Text.lower():
            res["objetos_inactivos"] = u.activar_solo(session, programa)
            p = u.popup(session)
        if p:
            res.update(error="popup no reconocido al activar", titulo=p.Text, botones=u.botones_popup(session))
            return res
        res["activar"] = u.barra_estado(session)
    return res
