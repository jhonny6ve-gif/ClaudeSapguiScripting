# Cambios

## 0.2.0
- Equipo SAP: agentes `sap-funcional`, `sap-abap` y `sap-qa`, y skill `sap-desarrollo` que orquesta especificación → desarrollo → prueba → QA → entrega, con ciclo de corrección (máximo 3 rondas) y dos aprobaciones del usuario.
- Plantillas de entregables: EF, ET y dictamen QA en Word (`generar_documento_word`) e informe web HTML autocontenido (`generar_informe_web`), con esqueletos (`ver_plantilla`) y marcas `*BOM`/`*EOM` (`marca_modificacion`).
- Marca configurable en `config.json`: empresa, logos incrustados y colores.
- Herramientas nuevas: `ejecutar_programa` (lista como texto), `crear_programa` (SE38, $TMP o paquete con orden), `textos_seleccion` (creada por el agente ABAP durante la prueba del flujo), `leer_tabla` con `columnas`, `grabar_activar_abap` con `solo` (activa solo los objetos indicados).
- Utilidades: `filas_tabla_control` (recorre table controls con scroll), `activar_solo`, `leer_lista`.
- `generar_documento_word` / `generar_informe_web` rechazan contenido con marcadores `<...>` sin completar; `ver_plantilla` da reglas según el tipo.
- `captura` acepta rutas con `/`; `ejecutar_codigo` devuelve `resultado_parcial` si falla a mitad.
- `marca_modificacion` admite `{usuario}` y `{fecha}` en `ticket_formato`.
- Probado de punta a punta con un programa de demostración: EF → ET → desarrollo → prueba → QA NO CONFORME → corrección → QA CONFORME → entrega.
- Dependencia nueva: `python-docx`.

## 0.1.0
- Primera versión: servidor MCP `sapgui`, skill `sapgui` y agente `sapgui-operador`.
- Herramientas de sesiones, navegación, pantallas, capturas, fuentes ABAP y SE16N.
- Scripts extensibles: base + usuario (el del usuario gana), historial de versiones, ejecución ad-hoc.
- Configuración opcional: sistemas permitidos, solo lectura, tablas bloqueadas y log de auditoría.
