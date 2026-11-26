---
name: sap-desarrollo
description: Flujo de desarrollo SAP con equipo de agentes (funcional, ABAP y QA) sobre SAP GUI. Usar cuando el usuario pida llevar un requerimiento SAP de punta a punta - especificar, desarrollar, probar y validar con QA - o diga "/sap-desarrollo", "flujo completo", "con QA", "equipo SAP". Orquesta los subagentes sap-funcional, sap-abap y sap-qa, con ciclo de corrección hasta que QA esté conforme.
---

# Flujo sap-desarrollo

**Tú eres el orquestador.** Los subagentes no pueden lanzar otros subagentes, así que tú llamas a cada uno en su etapa, les pasas lo que necesitan y decides cómo sigue. Trabajan **de a uno**, porque comparten un solo SAP GUI, y cada uno abre su propia sesión.

## Antes de empezar
Confirma con el usuario o toma de lo que ya dijo:
- requerimiento y ticket (número y descripción, para las marcas BOM/EOM);
- sistema y mandante de **desarrollo** y de **pruebas**;
- orden de transporte, si ya existe;
- nombre corto del trabajo.

Crea la carpeta `trabajos/<nombre>/` en el directorio actual y pásales a todos los agentes su **ruta absoluta**. Ahí quedan todos los artefactos, con estos nombres, para que cada agente lea lo anterior sin depender de la memoria de otro:
- `ef.json`, `EF_<ticket>.docx`
- `et.json`, `codigo_propuesto.abap`, `ET_<ticket>.docx`
- `pruebas.json` y las capturas `prueba_rN_casoM_*.png`
- `qa_rN.json`, `QA_<ticket>_RN.docx`
- `informe.json`, `Informe_<ticket>.html`
- `estado.md`

## Tiempo y costo
Cada llamada a un agente arranca sin contexto y tarda minutos. Con el flujo completo, un requerimiento chico lleva unas 6 a 8 llamadas. Para que rinda:
- en cada llamada pasa solo lo necesario: la etapa, las rutas y las observaciones por número;
- pide a los agentes que hagan varios casos en una sola llamada de herramienta;
- en las correcciones, vuelve a llamar solo a quien tiene observaciones;
- si el usuario lo pide o el cambio es trivial, propón el **modo corto**: `sap-abap` redacta la EF y la ET juntas (con la puerta 1 igual) y `sap-qa` ejecuta también los casos de prueba, sin una llamada aparte del funcional.

## Etapas
1. **Especificación**
   - `sap-funcional` redacta la EF (Word).
   - `sap-abap` revisa su factibilidad y redacta la ET (Word).
   - Si alguno devuelve preguntas, házselas al usuario y vuelve a llamarlo.
   - ✋ **Puerta 1:** muestra al usuario un resumen de la EF y la ET y espera su aprobación antes de desarrollar.
2. **Desarrollo:** `sap-abap` desarrolla en el sistema de desarrollo, graba, activa y genera el informe web.
3. **Prueba funcional:** `sap-funcional` ejecuta los casos de la EF y deja `pruebas.json` con evidencia.
   - Si las pruebas son en otro sistema, el transporte suele hacerlo Basis. **Pídeselo al usuario y espera**; no lo saltes.
4. **QA:** `sap-qa` valida y emite el dictamen (Word y las líneas `DICTAMEN:` / `OBSERVACIONES_ABIERTAS:` / `RESPONSABLES:`).
   - **CONFORME** → pasa a la etapa 5.
   - **NO CONFORME** → envía las observaciones por número a su responsable: `sap-abap` (código) o `sap-funcional` (EF o prueba). Repite 2 → 3 → 4 solo con lo afectado.
   - **Límite: 3 rondas de QA.** Si en la tercera sigue NO CONFORME, detente y entrega al usuario el estado, las observaciones abiertas y la causa probable. No sigas iterando por tu cuenta.
5. **Entrega**
   - `sap-abap` actualiza el informe web final: cambios, pruebas, dictamen QA y pendientes (transporte, etc.).
   - ✋ **Puerta 2:** presenta al usuario el resultado (rutas de la EF, la ET, el dictamen y el informe) y los pendientes.

## Reglas del orquestador
- En cada llamada pasa a cada agente: el ticket, el sistema, la carpeta del trabajo, la etapa y, en las correcciones, el número y el texto de cada observación.
- No reescribas tú el trabajo de un agente. Si algo está mal, vuelve a llamarlo con la observación.
- Lleva en `trabajos/<nombre>/estado.md` un registro corto por ronda: etapa, resultado y observaciones abiertas.
- Nunca omitas QA ni declares terminado sin un dictamen CONFORME, salvo que el usuario lo decida de forma explícita.
- Para tareas sueltas que no son un desarrollo completo usa `sapgui-operador`, no este flujo.
