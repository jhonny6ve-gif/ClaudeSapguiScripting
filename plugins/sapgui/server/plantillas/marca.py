"""Marca configurable (config.json -> "marca") compartida por las plantillas Word y web."""
from __future__ import annotations

import base64
from pathlib import Path

MARCA_DEFECTO = {
    "empresa": "",                 # aparece en el pie ("Elaborado por ...")
    "logo_izquierdo": "",          # ruta a PNG/JPG/SVG; se incrusta en base64
    "logo_derecho": "",
    "colores": {
        "primario": "#2F6FA3",     # encabezados de tabla, títulos, acentos
        "secundario": "#4C8CC0",
        "acento": "#8FB8DE",       # acento en modo oscuro y tercer tramo de la línea de marca
    },
    "ticket_formato": "{ticket} - {descripcion}",  # se usa en *BOM / *EOM
}


def cargar_marca(cfg: dict | None) -> dict:
    m = {**MARCA_DEFECTO, **((cfg or {}).get("marca") or {})}
    m["colores"] = {**MARCA_DEFECTO["colores"], **(((cfg or {}).get("marca") or {}).get("colores") or {})}
    return m


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mezclar(h: str, con: str = "#FFFFFF", t: float = 0.88) -> str:
    """Mezcla el color h con 'con' en proporción t (t=1 -> 'con')."""
    a, b = hex_rgb(h), hex_rgb(con)
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def data_uri(ruta: str) -> str:
    if not ruta:
        return ""
    p = Path(ruta).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"No existe el logo {p}")
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".svg": "image/svg+xml",
            ".gif": "image/gif", ".webp": "image/webp"}.get(p.suffix.lower(), "image/png")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def bom_eom(marca: dict, ticket: str, descripcion: str = "", usuario: str = "") -> tuple[str, str]:
    """Líneas de comentario de marca de modificación ABAP."""
    import datetime as _dt  # noqa: PLC0415

    txt = marca["ticket_formato"].format(ticket=ticket, descripcion=descripcion, usuario=usuario,
                                         fecha=_dt.date.today().strftime("%d.%m.%Y")).rstrip(" -")
    return f"*BOM {txt}", f"*EOM {ticket}"
