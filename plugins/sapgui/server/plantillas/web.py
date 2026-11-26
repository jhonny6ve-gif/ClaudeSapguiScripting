"""Informe web (HTML de un solo archivo, sin recursos externos) a partir de un JSON por secciones.

Estructura del contenido (todas las claves son opcionales salvo 'titulo'):
{
  "titulo": "Ajuste del programa Z_EJEMPLO", "titulo_acento": "Z_EJEMPLO",
  "eyebrow": "Proyecto X · ECC 6.0 · SD", "lede": "Resumen en una o dos frases.",
  "etiqueta_franja": "Informe técnico",
  "meta": {"Sistema": "DEV/100", "Ticket": "1234", "Fecha": "26.11.2026"},
  "estado": [{"valor": "3", "etiqueta": "Cambios", "tipo": "ok|warn|info|acc"}],
  "secciones": [{"id": "resumen", "titulo": "Resumen", "bloques": [ ...bloques... ]}],
  "pie": ["Elaborado por ...", "Fuentes: ..."]
}
Bloques: parrafo{texto} · lista{items} · tabla{columnas, filas, num:[índices de columnas numéricas]}
· callout{texto, aviso:bool} · flujo{pasos, resaltado:[índices]} · tarjetas{items:[{titulo, texto}]}
· codigo{titulo, codigo, desde (nº de la primera línea del fuente original; muestra numeración), variante: antes|despues|plano, copiar:bool}
· paso{numero, titulo, estado, donde:{etiqueta: valor}, antes:{codigo, desde}, despues:{codigo}, porque, check}
Texto en línea: `código`, **negrita** y pills [[ok|Texto]] (ok, warn, crit, info, muted).
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from string import Template

from .marca import data_uri, mezclar

CSS = (Path(__file__).parent / "informe.css").read_text(encoding="utf-8")

KW = sorted(set("""DATA TYPE TYPES AND IS NOT INITIAL SELECT SINGLE INTO FROM WHERE IF ENDIF ELSE ELSEIF CLEAR CALL FUNCTION
EXPORTING IMPORTING EXCEPTIONS TABLES MESSAGE WITH RETURN READ TABLE KEY LOOP AT ENDLOOP APPEND TO CONCATENATE SEPARATED
BY OR MODIFY BEGIN END OF FOR ALL ENTRIES FORM ENDFORM CASE WHEN ENDCASE OTHERS WRITE PARAMETERS SELECT-OPTIONS
SELECTION-SCREEN CHECKBOX DEFAULT SORTED UNIQUE COMMIT WORK WAIT ROLLBACK SPLIT CONDENSE CONTINUE EXIT PERFORM USING
CHANGING INITIALIZATION START-OF-SELECTION END-OF-SELECTION SORT MOVE-CORRESPONDING TRANSPORTING NO FIELDS BINARY SEARCH
DESCRIBE LINES ULINE AUTHORITY-CHECK OBJECT ID FIELD METHOD ENDMETHOD CLASS ENDCLASS DEFINITION IMPLEMENTATION PUBLIC
PRIVATE PROTECTED SECTION METHODS CREATE REF NEW VALUE INLINE FIELD-SYMBOLS ASSIGNING ASSIGN UNASSIGN TRY CATCH ENDTRY
RAISE RAISING DO ENDDO WHILE ENDWHILE CHECK REPORT PROGRAM INCLUDE CONSTANTS STATICS INSERT DELETE UPDATE LIKE EQ NE GT
LT GE LE IN BETWEEN UP ROWS ORDER GROUP HAVING INNER JOIN LEFT OUTER ON AS""".split()), key=len, reverse=True)
_KW_RE = re.compile(r"(?<![\w&;~\-/])(" + "|".join(re.escape(k) for k in KW) + r")(?![\w&~\-])")


def _inline(t: str) -> str:
    e = html.escape(str(t))
    e = re.sub(r"\[\[(ok|warn|crit|info|muted)\|([^\]]+)\]\]", r'<span class="pill \1">\2</span>', e)
    e = re.sub(r"`([^`]+)`", r"<code>\1</code>", e)
    e = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", e)
    return e


def _abap_linea(linea: str) -> str:
    if linea.lstrip().startswith("*"):
        return f'<span class="c">{html.escape(linea)}</span>'
    # comentario en línea con comillas dobles fuera de literales simples
    codigo, coment = linea, ""
    dentro = False
    for i, ch in enumerate(linea):
        if ch == "'":
            dentro = not dentro
        elif ch == '"' and not dentro:
            codigo, coment = linea[:i], linea[i:]
            break
    e = _KW_RE.sub(lambda m: f'<span class="k">{m.group(1)}</span>', html.escape(codigo, quote=False))
    if coment:
        e += f'<span class="c">{html.escape(coment, quote=False)}</span>'
    return e


class _Ctx:
    def __init__(self) -> None:
        self.n_code = 0
        self.n_chk = 0

    def code_id(self) -> str:
        self.n_code += 1
        return f"c{self.n_code}"

    def chk_id(self) -> str:
        self.n_chk += 1
        return f"chk{self.n_chk}"


def _codigo(ctx: _Ctx, b: dict) -> str:
    var = b.get("variante", "plano")
    lineas = str(b.get("codigo", "")).replace("\r\n", "\n").rstrip("\n").split("\n")
    desde = b.get("desde")
    if desde is not None:
        cuerpo = "\n".join(f'<span class="ln">{int(desde) + i}</span>{_abap_linea(l)}' for i, l in enumerate(lineas))
    else:
        cuerpo = "\n".join(_abap_linea(l) for l in lineas)
    titulo = b.get("titulo") or {"antes": "Antes", "despues": "Después"}.get(var, "Código")
    if var == "antes" and desde is not None and "línea" not in titulo.lower():
        titulo += f" · línea {desde}"
    copiar = b.get("copiar", var != "antes")
    cid = ctx.code_id()
    clase = {"antes": " before", "despues": " after"}.get(var, "")
    boton = f'<button class="copy" type="button" data-copy="{cid}">Copiar</button>' if copiar else ""
    return (f'<div class="codeblock"><div class="codebar{clase}"><span>{html.escape(titulo)}</span>{boton}</div>'
            f'<pre id="{cid}">{cuerpo}</pre></div>')


def _bloque(ctx: _Ctx, b: dict) -> str:
    t = b.get("tipo", "parrafo")
    if t == "parrafo":
        return f"<p>{_inline(b.get('texto', ''))}</p>"
    if t == "lista":
        return '<ul class="plain">' + "".join(f"<li>{_inline(i)}</li>" for i in b.get("items", [])) + "</ul>"
    if t == "tabla":
        num = set(b.get("num", []))
        th = "".join(f"<th>{_inline(c)}</th>" for c in b.get("columnas", []))
        td_num = ' class="num"'
        trs = "".join(
            "<tr>" + "".join(f"<td{td_num if j in num else ''}>{_inline(c)}</td>" for j, c in enumerate(f)) + "</tr>"
            for f in b.get("filas", [])
        )
        return f'<div class="tablewrap"><table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'
    if t == "callout":
        cls = "callout warn" if b.get("aviso") else "callout"
        return f'<div class="{cls}"><p>{_inline(b.get("texto", ""))}</p></div>'
    if t == "flujo":
        hl = set(b.get("resaltado", []))
        partes = [f'<span class="box{" hl" if i in hl else ""}">{_inline(p)}</span>' for i, p in enumerate(b.get("pasos", []))]
        return '<div class="flow">' + '<span class="arr">→</span>'.join(partes) + "</div>"
    if t == "tarjetas":
        return '<div class="grid2">' + "".join(
            f'<div class="card"><h3>{_inline(i.get("titulo", ""))}</h3><p>{_inline(i.get("texto", ""))}</p></div>'
            for i in b.get("items", [])) + "</div>"
    if t == "codigo":
        return _codigo(ctx, b)
    if t == "paso":
        partes = []
        chk = ""
        if b.get("check", "Aplicado"):
            chk = f'<label class="done"><input type="checkbox" id="{ctx.chk_id()}"> {html.escape(b.get("check", "Aplicado"))}</label>'
        partes.append(f'<div class="step-head"><div class="left"><span class="step-no">{html.escape(str(b.get("numero", "")))}</span>'
                      f'<h3>{_inline(b.get("titulo", ""))}</h3> {_inline(b.get("estado", ""))}</div>{chk}</div>')
        if b.get("donde"):
            partes.append('<dl class="where">' + "".join(f"<dt>{_inline(k)}</dt><dd>{_inline(v)}</dd>" for k, v in b["donde"].items()) + "</dl>")
        if b.get("antes"):
            partes.append(_codigo(ctx, {**b["antes"], "variante": "antes"}))
        if b.get("despues"):
            partes.append(_codigo(ctx, {**b["despues"], "variante": "despues"}))
        if b.get("porque"):
            partes.append(f'<div class="why"><p>{_inline(b["porque"])}</p></div>')
        for extra in b.get("bloques", []):
            partes.append(_bloque(ctx, extra))
        cls = "step optional" if b.get("opcional") else "step"
        return f'<div class="{cls}">' + "".join(partes) + "</div>"
    raise ValueError(f"Tipo de bloque desconocido: {t}")


_JS = """(function () {
  var KEY = '%s';
  var state = {};
  try { state = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { state = {}; }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} }
  function sync(cb) { var step = cb.closest('.step'); if (step) step.classList.toggle('is-done', cb.checked); }
  document.querySelectorAll('input[type="checkbox"]').forEach(function (cb) {
    if (state[cb.id]) cb.checked = true;
    sync(cb);
    cb.addEventListener('change', function () { state[cb.id] = cb.checked; save(); sync(cb); });
  });
  document.querySelectorAll('button.copy').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var pre = document.getElementById(btn.getAttribute('data-copy'));
      var text = pre.innerText;
      function done(msg) { btn.textContent = msg; setTimeout(function () { btn.textContent = 'Copiar'; }, 1600); }
      function fallback() {
        var r = document.createRange(); r.selectNodeContents(pre);
        var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
        done('Seleccionado: Ctrl+C');
      }
      try { navigator.clipboard.writeText(text).then(function () { done('Copiado'); }, fallback); } catch (e) { fallback(); }
    });
  });
})();"""


def _slug(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60] or "informe"


def generar(contenido: dict, marca: dict, ruta: str) -> str:
    ctx = _Ctx()
    col = marca["colores"]
    css = Template(CSS).substitute(
        primario=col["primario"], secundario=col["secundario"], acento=col["acento"],
        primario_suave=mezclar(col["primario"], "#FFFFFF", 0.88),
        acento_oscuro=mezclar(col["acento"], "#101317", 0.82),
    )
    titulo = str(contenido.get("titulo", "Informe"))
    acento = contenido.get("titulo_acento")
    h1 = html.escape(titulo)
    if acento and acento in titulo:
        h1 = h1.replace(html.escape(acento), f"<span>{html.escape(acento)}</span>", 1)

    li, ri = data_uri(marca.get("logo_izquierdo", "")), data_uri(marca.get("logo_derecho", ""))
    franja = ""
    if li or ri or contenido.get("etiqueta_franja"):
        img = lambda u, lado: f'<img class="logo {lado}" src="{u}" alt="">' if u else '<span class="logo"></span>'
        franja = (f'<div class="brandbar" role="banner"><div class="brandbar-in">{img(li, "left")}'
                  f'<span class="brandbar-tag">{html.escape(contenido.get("etiqueta_franja", ""))}</span>{img(ri, "right")}</div>'
                  '<div class="brandrule" aria-hidden="true"><span></span><span></span><span></span></div></div>')

    meta = "".join(f"<span>{html.escape(str(k))}: <b>{_inline(v)}</b></span>" for k, v in (contenido.get("meta") or {}).items())
    estado = ""
    if contenido.get("estado"):
        estado = '<div class="status">' + "".join(
            f'<div class="stat {html.escape(e.get("tipo", "info"))}"><span class="v">{html.escape(str(e.get("valor", "")))}</span>'
            f'<span class="l">{_inline(e.get("etiqueta", ""))}</span></div>' for e in contenido["estado"]) + "</div>"

    secs, toc = [], []
    for i, s in enumerate(contenido.get("secciones", []), 1):
        sid = s.get("id") or _slug(s.get("titulo", f"s{i}"))
        toc.append(f'<li><a href="#{sid}">{html.escape(s.get("titulo", ""))}</a></li>')
        cuerpo = "".join(_bloque(ctx, b) for b in s.get("bloques", []))
        secs.append(f'<section id="{sid}"><h2><span class="n">{i:02d}</span>{html.escape(s.get("titulo", ""))}</h2>{cuerpo}</section>')

    pie_items = list(contenido.get("pie") or [])
    if marca.get("empresa") and not any("Elaborado" in p for p in pie_items):
        pie_items.insert(0, f"Elaborado por {marca['empresa']}.")
    if ctx.n_chk:
        pie_items.append("Las casillas se guardan solo en tu navegador.")
    pie = "<footer>" + "".join(f"<span>{_inline(p)}</span>" for p in pie_items) + "</footer>" if pie_items else ""

    doc = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(titulo)}</title>
<style>
{css}</style>
</head>
<body>
{franja}
<div class="shell">
  <nav class="toc" aria-label="Índice"><p>Contenido</p><ol>{''.join(toc)}</ol></nav>
  <main>
    <header class="top">
      {f'<div class="eyebrow">{_inline(contenido["eyebrow"])}</div>' if contenido.get("eyebrow") else ''}
      <h1>{h1}</h1>
      {f'<p class="lede">{_inline(contenido["lede"])}</p>' if contenido.get("lede") else ''}
      {f'<div class="meta">{meta}</div>' if meta else ''}
    </header>
    {estado}
    {''.join(secs)}
    {pie}
  </main>
</div>
<script>
{_JS % _slug(titulo)}
</script>
</body>
</html>
"""
    p = Path(ruta).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(doc, encoding="utf-8")
    return str(p)
