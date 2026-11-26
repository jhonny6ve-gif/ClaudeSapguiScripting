# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp>=1.2,<2",
#   "pywin32>=306; sys_platform == 'win32'",
# ]
# ///
"""Servidor MCP para controlar SAP GUI for Windows mediante SAP GUI Scripting.

Se conecta a las sesiones que el usuario ya abrió en SAP Logon (no inicia sesión
ni maneja contraseñas). Todas las llamadas COM se ejecutan en un único hilo
dedicado, porque los objetos de SAP GUI Scripting no se pueden compartir entre
hilos.
"""
from __future__ import annotations

import ast
import contextlib
import datetime as _dt
import importlib.util
import io
import json
import os
import queue
import shutil
import sys
import tempfile
import threading
import traceback
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP, Image

# --------------------------------------------------------------------------
# Rutas y configuración
# --------------------------------------------------------------------------
SERVER_DIR = Path(__file__).resolve().parent
BASE_SCRIPTS = SERVER_DIR / "scripts_base"
HOME = Path(os.environ.get("SAPGUI_CLAUDE_HOME", Path.home() / ".sapgui-claude"))
USER_SCRIPTS = HOME / "scripts"
HISTORIAL = USER_SCRIPTS / "historial"
CONFIG_FILE = HOME / "config.json"

for _p in (USER_SCRIPTS, HISTORIAL):
    _p.mkdir(parents=True, exist_ok=True)

# Los scripts importan "utilidades" (y entre ellos). La carpeta del usuario va primero.
for _p in (str(BASE_SCRIPTS), str(USER_SCRIPTS)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CONFIG_DEFECTO: dict[str, Any] = {
    "sistemas_permitidos": [],   # vacío = todos. Ej: ["DEV", "QAS/200"]
    "solo_lectura": False,
    "tablas_bloqueadas": [],
    "log_auditoria": str(HOME / "auditoria.jsonl"),  # "" para desactivar
}


def cargar_config() -> dict[str, Any]:
    cfg = dict(CONFIG_DEFECTO)
    if CONFIG_FILE.exists():
        try:
            cfg.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
        except Exception as e:  # noqa: BLE001
            print(f"config.json inválido, se usan valores por defecto: {e}", file=sys.stderr)
    return cfg


class Bloqueado(Exception):
    pass


def auditar(accion: str, sesion_info: dict | None, detalle: dict | None = None, ok: bool = True) -> None:
    ruta = cargar_config().get("log_auditoria")
    if not ruta:
        return
    reg = {
        "hora": _dt.datetime.now().isoformat(timespec="seconds"),
        "accion": accion,
        "ok": ok,
        "sesion": sesion_info,
        "detalle": detalle,
    }
    try:
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps(reg, ensure_ascii=False, default=str) + "\n")
    except Exception as e:  # noqa: BLE001
        print(f"No se pudo escribir el log de auditoría: {e}", file=sys.stderr)


# --------------------------------------------------------------------------
# Hilo COM dedicado
# --------------------------------------------------------------------------
class HiloCOM:
    def __init__(self) -> None:
        self._q: queue.Queue = queue.Queue()
        self._t = threading.Thread(target=self._loop, name="sapgui-com", daemon=True)
        self._t.start()

    def _loop(self) -> None:
        import pythoncom  # noqa: PLC0415

        pythoncom.CoInitialize()
        while True:
            fn, res = self._q.get()
            try:
                res.put((True, fn()))
            except BaseException as e:  # noqa: BLE001
                res.put((False, e))

    def run(self, fn: Callable[[], Any]) -> Any:
        res: queue.Queue = queue.Queue(maxsize=1)
        self._q.put((fn, res))
        ok, val = res.get()
        if ok:
            return val
        raise val


COM = HiloCOM()
SESIONES_ABIERTAS: set[str] = set()


def _engine():
    import win32com.client  # noqa: PLC0415

    try:
        sap = win32com.client.GetObject("SAPGUI")
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(
            "No se encontró SAP GUI. Abre SAP Logon e inicia sesión en el sistema. "
            f"Detalle: {e}"
        ) from e
    eng = sap.GetScriptingEngine
    if eng is None:
        raise RuntimeError("SAP GUI Scripting no está habilitado en SAP GUI (Opciones > Accesibilidad y scripting).")
    return eng


def _hijos(o) -> list:
    c = o.Children
    return [c(i) for i in range(c.Count)]


def _info(s) -> dict:
    i = s.Info
    return {
        "id": s.Id,
        "sistema": i.SystemName,
        "mandante": i.Client,
        "usuario": i.User,
        "idioma": i.Language,
        "transaccion": i.Transaction,
        "ocupada": bool(s.Busy),
    }


def _permitido(info: dict) -> None:
    lista = [x.upper() for x in cargar_config().get("sistemas_permitidos") or []]
    if not lista:
        return
    sid, cli = info["sistema"].upper(), str(info["mandante"])
    if sid in lista or f"{sid}/{cli}" in lista:
        return
    raise Bloqueado(f"El sistema {sid}/{cli} no está en 'sistemas_permitidos' de {CONFIG_FILE}")


def _escritura() -> None:
    if cargar_config().get("solo_lectura"):
        raise Bloqueado(f"Modo solo lectura activo ('solo_lectura' en {CONFIG_FILE}).")


def _sesion(id_sesion: str):
    s = _engine().findById(id_sesion)
    if s is None or s.Type != "GuiSession":
        raise RuntimeError(f"'{id_sesion}' no es una sesión válida. Usa listar_sesiones.")
    _permitido(_info(s))
    return s


def _rel(s, obj_id: str) -> str:
    pref = s.Id + "/"
    return obj_id[len(pref):] if obj_id.startswith(pref) else obj_id


def _ctrl(s, id_control: str):
    return s.findById(id_control)


def _resumen(s) -> dict:
    """Estado tras una acción: título, barra de estado y popups abiertos."""
    out: dict[str, Any] = {}
    try:
        out["titulo"] = s.findById("wnd[0]").Text
        sb = s.findById("wnd[0]/sbar")
        out["barra_estado"] = {"texto": sb.Text, "tipo": sb.MessageType}
    except Exception:  # noqa: BLE001
        pass
    pops = []
    for n in range(1, 6):
        try:
            w = s.findById(f"wnd[{n}]", False)
        except Exception:  # noqa: BLE001
            w = None
        if w is None:
            break
        pops.append({"id": f"wnd[{n}]", "titulo": w.Text})
    if pops:
        out["popups"] = pops
    return out


def _accion(nombre: str, id_sesion: str, fn: Callable[[Any], Any], escribe: bool, detalle: dict | None = None):
    def trabajo():
        s = _sesion(id_sesion)
        info = _info(s)
        try:
            if escribe:
                _escritura()
            r = fn(s)
            auditar(nombre, info, detalle)
            return r
        except Exception as e:
            auditar(nombre, info, {**(detalle or {}), "error": str(e)}, ok=False)
            raise

    return COM.run(trabajo)


# --------------------------------------------------------------------------
# Carga de scripts
# --------------------------------------------------------------------------
def _ruta_script(nombre: str) -> Path | None:
    nombre = nombre.removesuffix(".py")
    for d in (USER_SCRIPTS, BASE_SCRIPTS):
        p = d / f"{nombre}.py"
        if p.exists():
            return p
    return None


def _cargar_modulo(ruta: Path):
    spec = importlib.util.spec_from_file_location(f"sapgui_script_{ruta.stem}", ruta)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    # Recargar utilidades por si el usuario la adaptó
    sys.modules.pop("utilidades", None)
    spec.loader.exec_module(mod)
    return mod


def _correr_script(nombre: str, id_sesion: str, args: dict | None) -> dict:
    ruta = _ruta_script(nombre)
    if ruta is None:
        raise RuntimeError(f"No existe el script '{nombre}'. Usa listar_scripts.")

    def trabajo():
        s = _sesion(id_sesion)
        info = _info(s)
        buf = io.StringIO()
        mod = _cargar_modulo(ruta)
        if getattr(mod, "ESCRIBE", True):
            _escritura()
        if cargar_config().get("tablas_bloqueadas") and args and "tabla" in args:
            if str(args["tabla"]).upper() in [t.upper() for t in cargar_config()["tablas_bloqueadas"]]:
                raise Bloqueado(f"La tabla {args['tabla']} está en 'tablas_bloqueadas'.")
        try:
            with contextlib.redirect_stdout(buf):
                r = mod.run(s, **(args or {}))
            auditar(f"script:{nombre}", info, {"args": args, "origen": str(ruta.parent.name)})
            return {"ok": True, "script": str(ruta), "resultado": r, "salida": buf.getvalue(), **_resumen(s)}
        except Exception as e:  # noqa: BLE001
            auditar(f"script:{nombre}", info, {"args": args, "error": str(e)}, ok=False)
            return {
                "ok": False,
                "script": str(ruta),
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(limit=6),
                "salida": buf.getvalue(),
                **_resumen(s),
            }

    return COM.run(trabajo)


# --------------------------------------------------------------------------
# Servidor MCP
# --------------------------------------------------------------------------
mcp = FastMCP(
    "sapgui",
    instructions=(
        "Controla SAP GUI for Windows por SAP GUI Scripting sobre sesiones que el usuario ya abrió. "
        "Antes de actuar en una pantalla nueva usa leer_pantalla para obtener los IDs exactos. "
        "Trabaja en una sesión nueva (abrir_sesion) y no en las del usuario. "
        "Para tareas que no cubren las herramientas fijas, revisa listar_scripts; si no hay, "
        "prueba con ejecutar_codigo y guarda lo que funcione con guardar_script."
    ),
)

VKEYS = {
    "ENTER": 0, "F1": 1, "F2": 2, "F3": 3, "F4": 4, "F5": 5, "F6": 6, "F7": 7, "F8": 8,
    "F9": 9, "F10": 10, "CTRL+S": 11, "F12": 12, "SHIFT+F1": 13, "SHIFT+F2": 14, "SHIFT+F3": 15,
    "SHIFT+F4": 16, "SHIFT+F5": 17, "SHIFT+F6": 18, "SHIFT+F7": 19, "SHIFT+F8": 20,
    "SHIFT+F9": 21, "SHIFT+CTRL+0": 22, "SHIFT+F11": 23, "SHIFT+F12": 24, "CTRL+F1": 25,
    "CTRL+F2": 26, "CTRL+F3": 27, "CTRL+F4": 28, "CTRL+F5": 29, "CTRL+F6": 30,
    "CTRL+F7": 31, "CTRL+F8": 32, "CTRL+F9": 33, "CTRL+F10": 34, "CTRL+F11": 35,
    "CTRL+F12": 36, "CTRL+E": 70, "CTRL+F": 71, "CTRL+P": 86, "CTRL+N": 74,
    "CTRL+G": 84, "CTRL+R": 85, "CTRL+PGUP": 80, "PGUP": 81, "PGDN": 82, "CTRL+PGDN": 83,
}


@mcp.tool()
def listar_sesiones() -> list[dict]:
    """Lista las conexiones y sesiones abiertas en SAP GUI: id, sistema, mandante, usuario, transacción y si está ocupada."""

    def trabajo():
        eng = _engine()
        out = []
        for c in _hijos(eng):
            for s in _hijos(c):
                d = _info(s)
                d["conexion"] = c.Description
                d["scripting_bloqueado_por_servidor"] = bool(c.DisabledByServer)
                out.append(d)
        return out

    return COM.run(trabajo)


@mcp.tool()
def abrir_sesion(sistema: str, mandante: str | None = None) -> dict:
    """Abre una sesión NUEVA (otra ventana) en una conexión ya logueada del sistema indicado y la devuelve.
    No toca las sesiones existentes del usuario. No inicia sesión: el usuario debe haber entrado antes."""

    def trabajo():
        eng = _engine()
        base = None
        for c in _hijos(eng):
            for s in _hijos(c):
                i = s.Info
                if i.SystemName.upper() == sistema.upper() and (mandante is None or str(i.Client) == str(mandante)):
                    base = s
                    break
            if base:
                break
        if base is None:
            raise RuntimeError(f"No hay sesión abierta en {sistema}{'/' + mandante if mandante else ''}. Inicia sesión en SAP Logon.")
        _permitido(_info(base))
        conn = base.Parent
        antes = {x.Id for x in _hijos(conn)}
        if conn.Children.Count >= 6:
            raise RuntimeError("La conexión ya tiene el máximo de sesiones; cierra alguna.")
        base.CreateSession()
        import time  # noqa: PLC0415

        for _ in range(60):
            time.sleep(0.25)
            nuevas = [x for x in _hijos(conn) if x.Id not in antes]
            if nuevas and not nuevas[0].Busy:
                s = nuevas[0]
                SESIONES_ABIERTAS.add(s.Id)
                info = _info(s)
                auditar("abrir_sesion", info)
                return info
        raise RuntimeError("SAP no abrió la sesión nueva a tiempo.")

    return COM.run(trabajo)


@mcp.tool()
def cerrar_sesion(id_sesion: str, forzar: bool = False) -> str:
    """Cierra una sesión. Por defecto solo cierra las abiertas con abrir_sesion; forzar=True cierra cualquiera."""
    if id_sesion not in SESIONES_ABIERTAS and not forzar:
        return "No cerrada: esa sesión no fue abierta por este servidor (usa forzar=True si el usuario lo pidió)."

    def fn(s):
        s.Parent.CloseSession(s.Id)
        SESIONES_ABIERTAS.discard(id_sesion)
        return f"Sesión {id_sesion} cerrada."

    return _accion("cerrar_sesion", id_sesion, fn, escribe=False)


@mcp.tool()
def ejecutar_transaccion(id_sesion: str, tcode: str) -> dict:
    """Ejecuta una transacción (equivale a escribir /n<tcode> en el campo de comandos). tcode vacío vuelve al menú."""

    def fn(s):
        s.findById("wnd[0]/tbar[0]/okcd").text = "/n" + tcode
        s.findById("wnd[0]").sendVKey(0)
        return _resumen(s)

    return _accion("ejecutar_transaccion", id_sesion, fn, escribe=False, detalle={"tcode": tcode})


def _nodo(s, o) -> dict:
    d = {"id": _rel(s, o.Id), "tipo": o.Type}
    for prop in ("Name", "Text", "Tooltip"):
        try:
            v = getattr(o, prop)
            if v:
                d[prop.lower()] = str(v)[:80]
        except Exception:  # noqa: BLE001
            pass
    try:
        if o.Type == "GuiShell":
            d["subtipo"] = o.SubType
    except Exception:  # noqa: BLE001
        pass
    try:
        if o.Type in ("GuiCheckBox", "GuiRadioButton"):
            d["seleccionado"] = bool(o.Selected)
        elif o.Type in ("GuiTextField", "GuiCTextField", "GuiPasswordField", "GuiComboBox"):
            d["modificable"] = bool(o.Changeable)
    except Exception:  # noqa: BLE001
        pass
    return d


@mcp.tool()
def leer_pantalla(id_sesion: str, desde: str = "wnd[0]", profundidad: int = 6, max_nodos: int = 400, solo_con_texto: bool = False) -> dict:
    """Devuelve el árbol de controles de la pantalla (id relativo a la sesión, tipo, nombre, texto).
    Úsalo SIEMPRE antes de leer o escribir en una pantalla nueva, para conocer los IDs exactos.
    'desde' acota la rama (ej. 'wnd[0]/usr', 'wnd[1]')."""

    def fn(s):
        raiz = s.findById(desde)
        nodos: list[dict] = []

        def rec(o, d):
            if len(nodos) >= max_nodos or d > profundidad:
                return
            n = _nodo(s, o)
            if not solo_con_texto or n.get("text") or n["tipo"] in ("GuiShell", "GuiTableControl", "GuiButton"):
                nodos.append({**n, "nivel": d})
            try:
                if o.ContainerType:
                    for ch in _hijos(o):
                        rec(ch, d + 1)
            except Exception:  # noqa: BLE001
                pass

        rec(raiz, 0)
        return {"nodos": nodos, "truncado": len(nodos) >= max_nodos, **_resumen(s)}

    return _accion("leer_pantalla", id_sesion, fn, escribe=False)


@mcp.tool()
def leer_campo(id_sesion: str, id_control: str) -> dict:
    """Lee un control por su id (texto, tipo, si está seleccionado o es modificable)."""
    return _accion("leer_campo", id_sesion, lambda s: _nodo(s, _ctrl(s, id_control)), escribe=False)


@mcp.tool()
def escribir_campo(id_sesion: str, id_control: str, valor: str) -> dict:
    """Escribe en un control: texto en campos, 'X'/'' en checkbox, clave en combobox, selección en radio."""

    def fn(s):
        o = _ctrl(s, id_control)
        t = o.Type
        if t == "GuiCheckBox":
            o.Selected = valor.strip().upper() in ("X", "1", "TRUE", "SI", "SÍ")
        elif t == "GuiRadioButton":
            o.Select()
        elif t == "GuiComboBox":
            o.Key = valor
        else:
            o.Text = valor
        return {"control": _nodo(s, o), **_resumen(s)}

    return _accion("escribir_campo", id_sesion, fn, escribe=True, detalle={"control": id_control, "valor": valor})


@mcp.tool()
def presionar(id_sesion: str, id_control: str) -> dict:
    """Presiona un botón, selecciona una pestaña, opción de menú o radio, o hace doble clic en un label."""

    def fn(s):
        o = _ctrl(s, id_control)
        t = o.Type
        if t in ("GuiButton",):
            o.Press()
        elif t in ("GuiTab", "GuiMenu", "GuiRadioButton", "GuiContextMenu"):
            o.Select()
        elif t == "GuiLabel":
            o.SetFocus()
            s.findById("wnd[0]").sendVKey(2)
        else:
            try:
                o.Press()
            except Exception:  # noqa: BLE001
                o.Select()
        return _resumen(s)

    return _accion("presionar", id_sesion, fn, escribe=True, detalle={"control": id_control})


@mcp.tool()
def enviar_tecla(id_sesion: str, tecla: str = "ENTER", ventana: str = "wnd[0]") -> dict:
    """Envía una tecla virtual a una ventana: ENTER, F3, F8, CTRL+S (grabar), CTRL+F2 (verificar), CTRL+F3 (activar)... o el número VKey."""
    k = VKEYS.get(tecla.upper().replace(" ", ""), None)
    if k is None:
        if not tecla.isdigit():
            raise ValueError(f"Tecla desconocida '{tecla}'. Conocidas: {', '.join(VKEYS)}")
        k = int(tecla)

    def fn(s):
        s.findById(ventana).sendVKey(k)
        return _resumen(s)

    return _accion("enviar_tecla", id_sesion, fn, escribe=True, detalle={"tecla": tecla, "ventana": ventana})


@mcp.tool()
def seleccionar_menu(id_sesion: str, ruta: str) -> dict:
    """Selecciona una opción de la barra de menú por textos separados por '>' (ej. 'Programa>Grabar')
    o por id (ej. 'wnd[0]/mbar/menu[0]/menu[6]'). Sin coincidencia, devuelve las opciones disponibles."""

    def fn(s):
        if ruta.startswith("wnd["):
            s.findById(ruta).Select()
            return _resumen(s)
        nodo = s.findById("wnd[0]/mbar")
        for parte in [p.strip().lower() for p in ruta.split(">")]:
            hijos = _hijos(nodo)
            m = [h for h in hijos if h.Text.replace("&", "").strip().lower() == parte] or [
                h for h in hijos if h.Text.replace("&", "").strip().lower().startswith(parte)
            ]
            if not m:
                return {"error": f"No se encontró '{parte}'", "opciones": [h.Text for h in hijos]}
            nodo = m[0]
        nodo.Select()
        return _resumen(s)

    return _accion("seleccionar_menu", id_sesion, fn, escribe=True, detalle={"ruta": ruta})


@mcp.tool()
def barra_estado(id_sesion: str) -> dict:
    """Título de la ventana, mensaje de la barra de estado (tipo S/W/E/A/I) y popups abiertos (wnd[1]...)."""
    return _accion("barra_estado", id_sesion, _resumen, escribe=False)


@mcp.tool()
def captura(id_sesion: str, ventana: str = "wnd[0]", ruta: str | None = None) -> Image:
    """Toma una captura PNG de una ventana de SAP y la devuelve como imagen (y la guarda si se da 'ruta')."""

    def fn(s):
        destino = ruta or os.path.join(tempfile.gettempdir(), f"sapgui_{_dt.datetime.now():%Y%m%d_%H%M%S}.png")
        s.findById(ventana).HardCopy(destino, 2)
        return destino

    p = _accion("captura", id_sesion, fn, escribe=False)
    return Image(path=p)


# ---- Herramientas fijas implementadas como scripts (se pueden adaptar) ----
@mcp.tool()
def leer_fuente_abap(id_sesion: str, nombre: str, tipo: str = "programa", ruta_salida: str | None = None) -> dict:
    """Lee el código fuente ABAP en modo visualizar. tipo: 'programa' (programas, includes e includes de
    métodos de clase vía SE38) o 'funcion' (módulo de función vía SE37). Devuelve las líneas y opcionalmente las guarda.
    Implementado por el script 'leer_fuente_abap' (adaptable)."""
    return _correr_script("leer_fuente_abap", id_sesion, {"nombre": nombre, "tipo": tipo, "ruta_salida": ruta_salida})


@mcp.tool()
def reemplazar_fuente_abap(id_sesion: str, nombre: str, bloques: list[dict], tipo: str = "programa") -> dict:
    """Entra en modo Modificar y reemplaza bloques de líneas. bloques = [{"desde": n, "hasta": m, "texto": "..."}],
    con números de línea del fuente ORIGINAL (se aplican de abajo hacia arriba). hasta = desde-1 inserta antes de 'desde'.
    Corre la verificación de sintaxis y NO graba ni activa: para eso usa grabar_activar_abap.
    Implementado por el script 'reemplazar_fuente_abap' (adaptable)."""
    return _correr_script("reemplazar_fuente_abap", id_sesion, {"nombre": nombre, "tipo": tipo, "bloques": bloques})


@mcp.tool()
def grabar_activar_abap(id_sesion: str, accion: str = "grabar") -> dict:
    """En el editor ABAP abierto: accion='grabar' (Ctrl+S), 'verificar' (Ctrl+F2) o 'activar' (Ctrl+F3).
    Devuelve popups (orden de transporte, lista de activación) para que se respondan con presionar/escribir_campo."""
    return _correr_script("grabar_activar_abap", id_sesion, {"accion": accion})


@mcp.tool()
def leer_tabla(id_sesion: str, tabla: str, filtros: dict[str, str] | None = None, max_filas: int = 200, ruta_csv: str | None = None) -> dict:
    """Lee una tabla con SE16N en modo visualizar. filtros = {"CAMPO": "valor"} (valor simple, igualdad).
    Devuelve columnas y filas (hasta max_filas) y opcionalmente guarda CSV. Implementado por el script 'leer_tabla'."""
    return _correr_script("leer_tabla", id_sesion, {"tabla": tabla, "filtros": filtros or {}, "max_filas": max_filas, "ruta_csv": ruta_csv})


# ---- Scripts: crear, adaptar, ejecutar ----
def _doc(p: Path) -> str:
    try:
        return (ast.get_docstring(ast.parse(p.read_text(encoding="utf-8"))) or "").strip()
    except Exception as e:  # noqa: BLE001
        return f"(no se pudo leer: {e})"


@mcp.tool()
def listar_scripts() -> dict:
    """Lista los scripts disponibles con su descripción. 'usuario' gana sobre 'base' si se llaman igual."""
    base = {p.stem: _doc(p) for p in sorted(BASE_SCRIPTS.glob("*.py"))}
    user = {p.stem: _doc(p) for p in sorted(USER_SCRIPTS.glob("*.py"))}
    return {
        "carpeta_usuario": str(USER_SCRIPTS),
        "usuario": user,
        "base": {k: v for k, v in base.items()},
        "sobrescritos_por_usuario": sorted(set(base) & set(user)),
    }


@mcp.tool()
def ver_script(nombre: str, origen: str = "efectivo") -> dict:
    """Muestra el código de un script. origen: 'efectivo' (el que se ejecuta), 'base' o 'usuario'."""
    nombre = nombre.removesuffix(".py")
    if origen == "base":
        p = BASE_SCRIPTS / f"{nombre}.py"
    elif origen == "usuario":
        p = USER_SCRIPTS / f"{nombre}.py"
    else:
        p = _ruta_script(nombre)
    if not p or not p.exists():
        raise RuntimeError(f"No existe '{nombre}' ({origen}).")
    return {"ruta": str(p), "codigo": p.read_text(encoding="utf-8")}


@mcp.tool()
def guardar_script(nombre: str, codigo: str) -> dict:
    """Crea un script nuevo o adapta uno existente en la carpeta del usuario (nunca toca los base).
    Debe definir run(session, **args) -> dict, un docstring de módulo que explique uso y argumentos,
    y ESCRIBE = True/False (si modifica datos en SAP). Valida la sintaxis y guarda la versión anterior en historial."""
    nombre = nombre.removesuffix(".py")
    if not nombre.replace("_", "").isalnum():
        raise ValueError("Nombre inválido: usa letras, números y guiones bajos.")
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as e:
        return {"ok": False, "error": f"Sintaxis: línea {e.lineno}: {e.msg}"}
    funcs = {n.name for n in arbol.body if isinstance(n, ast.FunctionDef)}
    avisos = []
    if nombre != "utilidades" and "run" not in funcs:
        return {"ok": False, "error": "Falta la función run(session, **args)."}
    if not ast.get_docstring(arbol):
        avisos.append("Sin docstring de módulo: agrega uso y argumentos.")
    if "ESCRIBE" not in codigo:
        avisos.append("Sin ESCRIBE: se tratará como script que escribe.")
    destino = USER_SCRIPTS / f"{nombre}.py"
    previo = None
    if destino.exists():
        previo = HISTORIAL / f"{nombre}.{_dt.datetime.now():%Y%m%d-%H%M%S}.py"
        shutil.copy2(destino, previo)
    destino.write_text(codigo, encoding="utf-8")
    auditar("guardar_script", None, {"nombre": nombre, "historial": str(previo) if previo else None})
    return {
        "ok": True,
        "ruta": str(destino),
        "version_anterior": str(previo) if previo else None,
        "sobrescribe_base": (BASE_SCRIPTS / f"{nombre}.py").exists(),
        "avisos": avisos,
    }


@mcp.tool()
def ejecutar_script(nombre: str, id_sesion: str, args: dict | None = None) -> dict:
    """Ejecuta un script (usuario o base) contra una sesión. Devuelve resultado, salida impresa y estado de pantalla,
    o el error con traceback para corregirlo con guardar_script."""
    return _correr_script(nombre, id_sesion, args)


@mcp.tool()
def ejecutar_codigo(id_sesion: str, codigo: str) -> dict:
    """Ejecuta código Python ad-hoc contra una sesión, para explorar o probar antes de guardar un script.
    Variables disponibles: session (GuiSession), u (módulo utilidades). Asigna a 'resultado' lo que quieras devolver."""

    def trabajo():
        s = _sesion(id_sesion)
        info = _info(s)
        _escritura()
        sys.modules.pop("utilidades", None)
        import utilidades  # noqa: PLC0415

        ns: dict[str, Any] = {"session": s, "u": utilidades, "resultado": None}
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                exec(compile(codigo, "<ejecutar_codigo>", "exec"), ns)  # noqa: S102
            auditar("ejecutar_codigo", info, {"codigo": codigo})
            return {"ok": True, "resultado": ns.get("resultado"), "salida": buf.getvalue(), **_resumen(s)}
        except Exception as e:  # noqa: BLE001
            auditar("ejecutar_codigo", info, {"codigo": codigo, "error": str(e)}, ok=False)
            return {"ok": False, "error": f"{type(e).__name__}: {e}", "traceback": traceback.format_exc(limit=6),
                    "salida": buf.getvalue(), **_resumen(s)}

    return COM.run(trabajo)


@mcp.tool()
def ver_configuracion() -> dict:
    """Muestra la configuración vigente y las rutas (config, scripts de usuario, log de auditoría)."""
    return {"config": cargar_config(), "archivo_config": str(CONFIG_FILE), "existe": CONFIG_FILE.exists(),
            "scripts_usuario": str(USER_SCRIPTS), "scripts_base": str(BASE_SCRIPTS)}


def main() -> None:
    if sys.platform != "win32":
        print("SAP GUI Scripting solo funciona en Windows.", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
