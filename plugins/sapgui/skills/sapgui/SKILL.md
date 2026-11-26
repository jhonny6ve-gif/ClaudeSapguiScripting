---
name: sapgui
description: Método de trabajo para operar SAP GUI for Windows con las herramientas MCP "sapgui" (SAP GUI Scripting). Usar siempre que el usuario pida hacer algo en SAP desde su SAP GUI abierto - ejecutar transacciones, leer o llenar pantallas, leer o modificar fuentes ABAP (SE38/SE37/SE24), consultar tablas (SE16N), tomar capturas, o crear o adaptar scripts de automatización SAP.
---

# Operar SAP GUI con las herramientas `sapgui`

Las herramientas trabajan sobre las sesiones que el usuario **ya abrió** en SAP Logon. Nunca pidas, escribas ni guardes contraseñas: el login lo hace la persona.

## Flujo base
1. `listar_sesiones` para ver los sistemas, mandantes y usuarios conectados. Si el sistema que se necesita no aparece, pide al usuario que inicie sesión.
2. `abrir_sesion(sistema, mandante)` para trabajar en una ventana **nueva**, sin tocar las del usuario. Al terminar, `cerrar_sesion`.
3. `ejecutar_transaccion(id, "SE38")`.
4. **Antes de leer o escribir en una pantalla que no conoces**, usa `leer_pantalla(id, desde="wnd[0]/usr")` para obtener los IDs exactos. No adivines IDs.
5. Después de cada acción revisa `barra_estado` y los `popups` que devuelve la herramienta. Mensaje tipo `E` o `A` = error: detente y explícalo.
6. `captura` cuando el usuario necesite ver la pantalla o cuando el árbol de controles no alcance para entenderla.

## Antes de reaccionar
- Si el mensaje es tipo W (advertencia), léelo y decide antes de seguir con Enter.
- Un popup puede ser una orden de transporte, una confirmación o una pregunta de grabar. Lee su título y sus botones (`leer_pantalla(desde="wnd[1]")`) antes de presionar nada.
- Grabar, activar, liberar, contabilizar o borrar cambian datos reales. Si el usuario no pidió esa acción concreta, pregúntale antes.

## Fuentes ABAP
- `leer_fuente_abap(id, nombre, tipo="programa"|"funcion")`. Los includes de métodos de clase (`ZCL_X=====...CM001`) se leen como `programa`.
- Para modificar:
  1. Lee el fuente.
  2. Arma los bloques con los números de línea del fuente **original**.
  3. Ejecuta `reemplazar_fuente_abap`, que no graba.
  4. Revisa el resultado y la verificación de sintaxis.
  5. `grabar_activar_abap("grabar")`, responde el popup de la orden si aparece.
  6. `grabar_activar_abap("activar")`.
  7. Relee el fuente y compáralo con lo esperado.
- El editor ABAP cuenta CR y LF por separado: envía el texto solo con LF (los scripts base ya lo hacen).
- Si al entrar SAP pregunta por cambios sin grabar de un intento anterior, la respuesta segura es **No** (descarta).

## Tablas
- `leer_tabla(id, tabla, filtros={"CAMPO": "valor"}, max_filas=200)`. Pide siempre filtros concretos y un máximo de filas razonable: no leas tablas completas.

## Cuando las herramientas fijas no alcanzan: scripts
1. `listar_scripts`: puede que ya exista uno que sirva.
2. Si no existe:
   1. Explora la pantalla con `leer_pantalla`.
   2. Prueba los pasos con `ejecutar_codigo` (variables `session` y `u` = utilidades; asigna a `resultado` lo que quieras devolver).
   3. Cuando funcione, guárdalo con `guardar_script`.
3. Si existe pero no calza (otra versión de SAP, otro dynpro, otro idioma):
   1. Míralo con `ver_script`.
   2. Guarda una versión adaptada **con el mismo nombre** usando `guardar_script`. La copia del usuario reemplaza a la base y la versión anterior queda en `historial`.
   3. Vuelve a probarlo con `ejecutar_script`.
4. Si `ejecutar_script` falla, devuelve un traceback. Corrige el script y repite. No dejes scripts rotos guardados.

Plantilla de un script:
```python
"""Qué hace, argumentos y qué devuelve."""
import utilidades as u

ESCRIBE = False   # True si modifica datos en SAP


def run(session, argumento1, argumento2="por defecto"):
    u.tx(session, "SU01")
    session.findById("wnd[0]/usr/ctxtSUID_ST_BNAME-BNAME").text = argumento1
    session.findById("wnd[0]/tbar[1]/btn[7]").press()   # Visualizar
    u.esperar(session)
    return {"titulo": session.findById("wnd[0]").Text, **u.barra_estado(session)}
```
Funciones de `utilidades`: `tx`, `enter`, `esperar`, `buscar` (findById sin error), `existe`, `hijos`, `barra_estado`, `popup`, `botones_popup`, `responder_popup_no_grabar`, `buscar_tipo`, `editor_abap`, `leer_editor`, `leer_grid`.

## Particularidades de SAP GUI Scripting
- Los IDs son relativos a la sesión: `wnd[0]/usr/ctxtCAMPO`. Prefijos: `txt` campo de texto, `ctxt` campo con ayuda F4, `chk` checkbox, `rad` radio, `btn` botón, `tbl` table control, `cntl…/shellcont/shell` controles (ALV, editor, árbol), `tabs/tabp` pestañas.
- Barra estándar: `wnd[0]/tbar[0]/btn[3]` Atrás, `btn[11]` Grabar; barra de aplicación `wnd[0]/tbar[1]/btn[8]` Ejecutar.
- Los table controls (`tbl…`) solo muestran las filas visibles. Para llegar a otras, mueve `verticalScrollbar.position` y vuelve a buscar el control.
- ALV grid (`GuiShell` subtipo `GridView`): `GetCellValue(fila, columna)`; mueve `firstVisibleRow` para que carguen las filas.
- Editor de líneas de SAPscript (SE71): Enter **inserta** una línea encima del cursor y puede mover el scroll, y las filas después del final no son editables. Método: crea primero las filas necesarias, vuelve el scroll a 0, reescribe el bloque completo y relee para comparar.
- `ejecutar_transaccion` usa `/n`, que en el editor ABAP **descarta sin preguntar** los cambios no grabados. Antes de cambiar de transacción, graba lo que quieras conservar.
- Para crear un programa nuevo usa el script `crear_programa` (atributos, paquete `$TMP` u otro con orden, y código opcional).
- Los textos de la interfaz dependen del idioma de logon. Compara contra IDs y nombres técnicos, no contra textos, siempre que se pueda.

## Configuración
`ver_configuracion` muestra `%USERPROFILE%\.sapgui-claude\config.json`, que es opcional y permite:
- `sistemas_permitidos`: por ejemplo `["DEV", "QAS/200"]`; vacío = todos.
- `solo_lectura`.
- `tablas_bloqueadas`.
- `log_auditoria`.

Si una herramienta responde que está bloqueada por configuración, explícaselo al usuario. No intentes rodear la restricción.
