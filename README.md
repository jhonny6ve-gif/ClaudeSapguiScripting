# ClaudeSapguiScripting

Plugin para **Claude Code** que permite a Claude operar **SAP GUI for Windows** mediante **SAP GUI Scripting**: ejecutar transacciones, leer y llenar pantallas, leer y modificar fuentes ABAP, consultar tablas con SE16N, tomar capturas y **crear o adaptar sus propios scripts** cuando las herramientas incluidas no alcanzan.

Claude trabaja sobre las sesiones que **tú ya abriste** en SAP Logon. El plugin no inicia sesión ni maneja contraseñas, y todo lo que se hace en SAP queda registrado con tu usuario y tus autorizaciones.

## Qué incluye

| Componente | Para qué |
|---|---|
| **Servidor MCP `sapgui`** (Python) | Las herramientas que Claude usa para manejar SAP GUI |
| **Skill `sapgui`** | El método de trabajo: explorar antes de actuar, manejo de popups, particularidades de los editores |
| **Agente `sapgui-operador`** | Subagente al que Claude delega tareas completas en SAP |

### Herramientas

- **Sesiones**: `listar_sesiones`, `abrir_sesion`, `cerrar_sesion`
- **Navegación**: `ejecutar_transaccion`, `enviar_tecla`, `seleccionar_menu`
- **Pantallas**: `leer_pantalla` (árbol de controles con sus IDs), `leer_campo`, `escribir_campo`, `presionar`, `barra_estado`, `captura`
- **ABAP**: `leer_fuente_abap`, `reemplazar_fuente_abap` (no graba), `grabar_activar_abap`
- **Tablas**: `leer_tabla` (SE16N con filtros y máximo de filas)
- **Scripts propios**: `listar_scripts`, `ver_script`, `guardar_script`, `ejecutar_script`, `ejecutar_codigo`
- **Configuración**: `ver_configuracion`

## Requisitos

1. **Windows** con **SAP GUI for Windows** 7.50 o superior.
2. **SAP GUI Scripting habilitado** en el servidor y en el cliente. Ver [docs/requisitos-sap.md](docs/requisitos-sap.md).
3. **[uv](https://docs.astral.sh/uv/)**. La primera vez instala Python y las dependencias (`mcp`, `pywin32`) de forma automática:
   ```powershell
   winget install --id astral-sh.uv
   ```
4. **Claude Code** (CLI, app de escritorio o extensión del IDE).

## Instalación

En Claude Code:

```
/plugin marketplace add jhonny6ve-gif/ClaudeSapguiScripting
```
```
/plugin install sapgui@claude-sapgui-scripting
```

Después reinicia Claude Code. Para comprobar que funciona, abre SAP Logon, inicia sesión en un sistema y pídele a Claude:

> Lista mis sesiones de SAP

### Otros clientes MCP (Claude Desktop, etc.)

Clona el repositorio y agrega el servidor a la configuración MCP del cliente:

```json
{
  "mcpServers": {
    "sapgui": {
      "command": "uv",
      "args": ["run", "--script", "C:/ruta/ClaudeSapguiScripting/plugins/sapgui/server/sapgui_mcp.py"]
    }
  }
}
```

## Ejemplos de uso

- "Abre una sesión nueva en DEV, entra a SE38 y descarga el fuente del programa RSPARAM."
- "En QAS mandante 200 consulta T001 con BUKRS = 1000 y muéstrame la moneda."
- "En el programa Z_MI_REPORTE cambia el texto del título en la línea 12, verifica la sintaxis y muéstrame el resultado sin grabar."
- "Toma una captura de la pantalla actual de mi sesión de DEV."
- "Crea un script que lea los datos de cabecera de un usuario en SU01 y guárdalo para reutilizarlo."

## Scripts propios: crear y adaptar

Las herramientas fijas cubren lo más común. Para todo lo demás, Claude escribe **scripts en Python** que puede reutilizar:

- Los **scripts base** vienen con el plugin, en `plugins/sapgui/server/scripts_base/`.
- Los **scripts del usuario** viven en `%USERPROFILE%\.sapgui-claude\scripts\`. Esa carpeta queda fuera del plugin, así que las actualizaciones no la tocan.
- Si un script del usuario se llama igual que uno base, **se usa el del usuario**. Así se adapta un script existente (por ejemplo, para otro idioma o versión de SAP) sin modificar el original.
- Cada vez que se guarda una versión nueva, la anterior queda en `scripts\historial\`.

Forma de un script:

```python
"""Qué hace, argumentos y qué devuelve."""
import utilidades as u

ESCRIBE = False   # True si modifica datos en SAP


def run(session, nombre):
    u.tx(session, "SE38")
    session.findById("wnd[0]/usr/ctxtRS38M-PROGRAMM").text = nombre
    ...
    return {"resultado": "..."}
```

## Configuración (opcional)

Por defecto **todo está habilitado**. Para restringir, crea `%USERPROFILE%\.sapgui-claude\config.json` (hay un ejemplo en [config.ejemplo.json](plugins/sapgui/server/config.ejemplo.json)):

```json
{
  "sistemas_permitidos": ["DEV", "QAS/200"],
  "solo_lectura": false,
  "tablas_bloqueadas": ["USR02"],
  "log_auditoria": "C:/Users/TU_USUARIO/.sapgui-claude/auditoria.jsonl"
}
```

| Clave | Efecto |
|---|---|
| `sistemas_permitidos` | Solo se puede operar en esos SID o SID/mandante. Vacío = todos |
| `solo_lectura` | Bloquea escribir campos, presionar botones, teclas, menús, scripts con `ESCRIBE = True` y `ejecutar_codigo` |
| `tablas_bloqueadas` | `leer_tabla` las rechaza |
| `log_auditoria` | Archivo JSONL con cada acción (hora, sistema, usuario, detalle). Activado por defecto; `""` lo desactiva |

La carpeta base se puede cambiar con la variable de entorno `SAPGUI_CLAUDE_HOME`.

## ⚠️ Advertencias

- Con la configuración por defecto, Claude puede **grabar y activar en cualquier sistema donde tengas sesión, incluido productivo**. Se recomienda configurar `sistemas_permitidos`.
- Todo lo que se hace queda registrado en SAP **con tu usuario**. Revisa las políticas de tu empresa o de tu cliente sobre automatización y uso de IA antes de usarlo.
- `solo_lectura` limita las herramientas, pero **no es una barrera de seguridad**: `ejecutar_codigo` y los scripts son Python y pueden hacer cualquier cosa que haga SAP GUI Scripting. Lo que de verdad limita el acceso son tus autorizaciones en SAP.
- SAP GUI Scripting depende de la pantalla: si cambia un dynpro, el idioma o la versión, un script puede fallar. En ese caso se adapta.

## Estructura

```
.claude-plugin/marketplace.json
plugins/sapgui/
  .claude-plugin/plugin.json
  .mcp.json
  server/sapgui_mcp.py           servidor MCP
  server/scripts_base/           utilidades.py y scripts incluidos
  server/config.ejemplo.json
  skills/sapgui/SKILL.md
  agents/sapgui-operador.md
docs/requisitos-sap.md
```

## Licencia

[MIT](LICENSE). Este proyecto no está afiliado a SAP SE. SAP y SAP GUI son marcas registradas de SAP SE.
