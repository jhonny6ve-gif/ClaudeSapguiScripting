"""Crea un programa ABAP nuevo en SE38 (atributos + paquete) y opcionalmente carga su código fuente.

Argumentos:
  nombre    nombre del programa (Z... / Y...)
  titulo    título del programa
  tipo      '1' ejecutable (por defecto), 'I' include, 'M' module pool, 'S' pool de subrutinas
  paquete   '$TMP' (objeto local, por defecto) u otro paquete
  orden     orden de transporte (obligatoria si el paquete no es local)
  codigo    opcional: código fuente completo; se reemplaza el esqueleto, se verifica la sintaxis y NO se graba
Si aparece un popup que el script no reconoce, se detiene y devuelve su título y botones.
Probado en ECC 6.0 (SE38 en español). El popup de paquete varía por versión: si no lo reconoce, adapta este script.
"""
import utilidades as u

ESCRIBE = True


def _boton_por_texto(session, n, palabras):
    for b in u.botones_popup(session, n):
        t = f"{b['texto']} {b['tooltip']}".lower()
        if any(p in t for p in palabras):
            return b["id"]
    return None


def run(session, nombre, titulo, tipo="1", paquete="$TMP", orden=None, codigo=None):
    nombre = nombre.upper()
    if not nombre.startswith(("Z", "Y")):
        raise ValueError("Solo se crean programas del espacio de cliente (Z o Y).")
    u.tx(session, "SE38")
    u.responder_popup_no_grabar(session)
    session.findById("wnd[0]/usr/ctxtRS38M-PROGRAMM").text = nombre
    session.findById("wnd[0]/usr/radRS38M-FUNC_EDIT").select()
    session.findById("wnd[0]/usr/btnNEW").press()
    u.esperar(session)
    w = u.popup(session)
    if w is None:
        raise RuntimeError("SAP no abrió el popup de atributos: " + u.barra_estado(session)["texto"])
    session.findById("wnd[1]/usr/txtRS38M-REPTI").text = titulo
    session.findById("wnd[1]/usr/cmbTRDIR-SUBC").key = tipo
    pasos = []
    for _ in range(8):
        w = u.popup(session)
        if w is None:
            break
        n = 2 if u.popup(session, 2) is not None else 1
        w = u.popup(session, n)
        ids = {b["id"] for b in u.botones_popup(session, n)}
        pasos.append(w.Text)
        if u.existe(session, f"wnd[{n}]/usr/txtRS38M-REPTI"):              # atributos
            session.findById(f"wnd[{n}]/tbar[0]/btn[0]").press()
        elif u.existe(session, f"wnd[{n}]/usr/ctxtKO007-L_DEVCLASS"):      # catálogo de objetos (paquete)
            if paquete.upper() == "$TMP":
                b = _boton_por_texto(session, n, ("objeto local", "local object"))
                if b:
                    session.findById(b).press()
                else:
                    session.findById(f"wnd[{n}]/usr/ctxtKO007-L_DEVCLASS").text = "$TMP"
                    session.findById(f"wnd[{n}]/tbar[0]/btn[0]").press()
            else:
                session.findById(f"wnd[{n}]/usr/ctxtKO007-L_DEVCLASS").text = paquete
                session.findById(f"wnd[{n}]/tbar[0]/btn[0]").press()
        elif u.existe(session, f"wnd[{n}]/usr/ctxtKO008-TRKORR"):          # orden de transporte
            if not orden:
                raise RuntimeError("SAP pide orden de transporte y no se indicó 'orden'. Popup: " + w.Text)
            session.findById(f"wnd[{n}]/usr/ctxtKO008-TRKORR").text = orden
            session.findById(f"wnd[{n}]/tbar[0]/btn[0]").press()
        else:
            return {"ok": False, "detenido_en_popup": w.Text, "botones": u.botones_popup(session, n), "pasos": pasos}
        u.esperar(session)
        if u.barra_estado(session)["tipo"] in ("E", "A"):
            raise RuntimeError(u.barra_estado(session)["texto"])

    res = {"ok": True, "programa": nombre, "pasos": pasos, "barra_estado": u.barra_estado(session),
           "titulo_ventana": session.findById("wnd[0]").Text}
    if codigo:
        ed = u.editor_abap(session)
        texto = str(codigo).replace("\r\n", "\n").rstrip("\n")
        n = ed.GetLineCount()
        ed.SelectRange(1, 1, n, len(ed.GetLineText(n)) + 1)
        ed.ReplaceSelection(texto)
        session.findById("wnd[0]").sendVKey(26)  # verificar
        u.esperar(session)
        res["lineas"] = ed.GetLineCount()
        res["verificacion"] = u.barra_estado(session)
        res["nota"] = "Código cargado SIN GRABAR. Usa grabar_activar_abap para grabar y activar."
    return res
