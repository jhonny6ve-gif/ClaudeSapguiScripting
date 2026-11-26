# Cambios

## 0.2.0
- Equipo SAP: agentes `sap-funcional`, `sap-abap` y `sap-qa`, y skill `sap-desarrollo` que orquesta especificación → desarrollo → prueba → QA → entrega, con ciclo de corrección (máximo 3 rondas) y dos aprobaciones del usuario.
- Plantillas de entregables: EF, ET y dictamen QA en Word (`generar_documento_word`) e informe web HTML autocontenido (`generar_informe_web`), con esqueletos (`ver_plantilla`) y marcas `*BOM`/`*EOM` (`marca_modificacion`).
- Marca configurable en `config.json`: empresa, logos incrustados y colores.
- Dependencia nueva: `python-docx`.

## 0.1.0
- Primera versión: servidor MCP `sapgui`, skill `sapgui` y agente `sapgui-operador`.
- Herramientas de sesiones, navegación, pantallas, capturas, fuentes ABAP y SE16N.
- Scripts extensibles: base + usuario (el del usuario gana), historial de versiones, ejecución ad-hoc.
- Configuración opcional: sistemas permitidos, solo lectura, tablas bloqueadas y log de auditoría.
