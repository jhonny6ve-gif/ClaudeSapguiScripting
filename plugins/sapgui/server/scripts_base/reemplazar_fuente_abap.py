"""Reemplaza bloques de líneas de un fuente ABAP en modo Modificar, verifica la sintaxis y NO graba.

Argumentos:
  nombre   programa / include / include de método (SE38) o módulo de función (SE37)
  tipo     'programa' (por defecto) o 'funcion'
  bloques  lista de {"desde": n, "hasta": m, "texto": "..."} con números de línea del fuente ORIGINAL.
           Se aplican de abajo hacia arriba para que los números no se corran.
           hasta = desde - 1  -> inserta el texto antes de la línea 'desde' (sin borrar).
Notas aprendidas:
  - El editor ABAP cuenta CR y LF por separado: el texto se envía solo con LF.
  - Si SAP pregunta por cambios sin grabar de una ejecución anterior, se responde 'No' (descarta).
Devuelve el fuente resultante, el resultado de la verificación (Ctrl+F2) y deja la sesión en Modificar.
"""
import utilidades as u

ESCRIBE = True


def run(session, nombre, bloques, tipo="programa"):
    nombre = nombre.upper()
    if tipo == "funcion":
        u.tx(session, "SE37")
        u.responder_popup_no_grabar(session)
        session.findById("wnd[0]/usr/ctxtRS38L-NAME").text = nombre
        session.findById("wnd[0]/usr/btnBUT4").press()  # Modificar
    else:
        u.tx(session, "SE38")
        u.responder_popup_no_grabar(session)
        session.findById("wnd[0]/usr/ctxtRS38M-PROGRAMM").text = nombre
        session.findById("wnd[0]/usr/radRS38M-FUNC_EDIT").select()
        session.findById("wnd[0]/usr/btnCHAP").press()  # Modificar
    u.esperar(session)
    w = u.popup(session)
    if w is not None:
        raise RuntimeError(f"Popup al entrar en Modificar: '{w.Text}' botones={u.botones_popup(session)}")
    if tipo == "funcion":
        pest = u.buscar(session, "wnd[0]/usr/tabsFUNC_TAB_STRIP/tabpSOURCE")
        if pest is not None:
            pest.select()
    ed = u.editor_abap(session)
    if ed.SubType != "AbapEditor":
        raise RuntimeError("El editor no es el editor ABAP nuevo; adapta este script para el editor de texto.")
    antes = ed.GetLineCount()
    titulo = session.findById("wnd[0]").Text
    aviso = None
    if not any(p in titulo.lower() for p in ("modif", "change", "ändern", "alterar")):
        aviso = f"El título '{titulo}' no indica modo Modificar: revisa que el cambio se haya aplicado."

    for b in sorted(bloques, key=lambda x: int(x["desde"]), reverse=True):
        d, h = int(b["desde"]), int(b["hasta"])
        texto = str(b["texto"]).replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
        n = ed.GetLineCount()
        if h >= n:  # hasta el final del fuente
            ed.SelectRange(d, 1, n, len(ed.GetLineText(n)) + 1)
            ed.ReplaceSelection(texto)
        else:
            ed.SelectRange(d, 1, h + 1, 1)
            ed.ReplaceSelection(texto + "\n")

    resultado = u.leer_editor(ed)
    session.findById("wnd[0]").sendVKey(26)  # Ctrl+F2 verificar
    u.esperar(session)
    verif = u.barra_estado(session)
    pop = u.popup(session)
    return {
        "nombre": nombre,
        "lineas_antes": antes,
        "lineas_despues": len(resultado),
        "verificacion": verif,
        "popup_verificacion": pop.Text if pop is not None else None,
        "aviso": aviso,
        "codigo": resultado,
        "nota": "SIN GRABAR. La sesión queda en modo Modificar. Usa grabar_activar_abap para grabar/activar.",
    }
