"""Lee el código fuente ABAP en modo Visualizar.

Argumentos:
  nombre       programa, include, include de método de clase (CLASE====...CMnnn) o módulo de función
  tipo         'programa' (SE38, valor por defecto) o 'funcion' (SE37)
  ruta_salida  opcional: archivo donde guardar el fuente (UTF-8)
Devuelve: {"nombre", "lineas": n, "codigo": [...]}
"""
import utilidades as u

ESCRIBE = False


def run(session, nombre, tipo="programa", ruta_salida=None):
    nombre = nombre.upper()
    if tipo == "funcion":
        u.tx(session, "SE37")
        session.findById("wnd[0]/usr/ctxtRS38L-NAME").text = nombre
        session.findById("wnd[0]/usr/btnBUT3").press()  # Visualizar
        u.esperar(session)
        pest = u.buscar(session, "wnd[0]/usr/tabsFUNC_TAB_STRIP/tabpSOURCE")
        if pest is not None:
            pest.select()
    else:
        u.tx(session, "SE38")
        session.findById("wnd[0]/usr/ctxtRS38M-PROGRAMM").text = nombre
        session.findById("wnd[0]/usr/radRS38M-FUNC_EDIT").select()
        session.findById("wnd[0]/usr/btnSHOP").press()  # Visualizar
        u.esperar(session)
    if u.popup(session) is not None:
        raise RuntimeError(f"Popup: {u.popup(session).Text} | {u.barra_estado(session)['texto']}")
    ed = u.editor_abap(session)
    lineas = u.leer_editor(ed)
    if ruta_salida:
        with open(ruta_salida, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lineas) + "\n")
    titulo = session.findById("wnd[0]").Text
    u.tx(session, "")
    return {"nombre": nombre, "titulo": titulo, "lineas": len(lineas), "codigo": lineas, "guardado_en": ruta_salida}
