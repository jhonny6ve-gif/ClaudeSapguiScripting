"""Graba, verifica o activa el objeto abierto en el editor ABAP (SE38/SE37/SE24/SE80).

Argumentos:
  accion  'grabar' (Ctrl+S), 'verificar' (Ctrl+F2) o 'activar' (Ctrl+F3)
  solo    (activar) nombre o lista de nombres: si aparece la lista de objetos inactivos, marca SOLO esos
          y continúa; los demás objetos inactivos del usuario no se tocan
Si SAP abre un popup (orden de transporte, lista de objetos a activar, advertencias), NO se responde:
se devuelven el título y los botones para decidir con presionar / escribir_campo.
"""
import utilidades as u

ESCRIBE = True
TECLAS = {"grabar": 11, "verificar": 26, "activar": 27}


def run(session, accion="grabar", solo=None):
    if accion not in TECLAS:
        raise ValueError(f"accion debe ser una de {list(TECLAS)}")
    session.findById("wnd[0]").sendVKey(TECLAS[accion])
    u.esperar(session)
    w = u.popup(session)
    activados = None
    if accion == "activar" and solo and w is not None and "inactiv" in w.Text.lower():
        activados = u.activar_solo(session, solo)
        w = u.popup(session)
    return {
        "objetos_inactivos": activados,
        "accion": accion,
        "barra_estado": u.barra_estado(session),
        "popup": None if w is None else {"titulo": w.Text, "botones": u.botones_popup(session)},
    }
