"""Esqueletos de contenido para cada entregable. ver_plantilla(tipo) los devuelve para completarlos."""

EF = {
    "titulo": "Especificación funcional: <qué se pide, en una línea>",
    "subtitulo": "<contexto breve: proceso, sociedad u organización involucrada>",
    "ficha": {
        "Objeto": "<programa, transacción, formulario o proceso>",
        "Módulo": "<SD / MM / FI / ...>",
        "Ticket": "<número y descripción del requerimiento>",
        "Fecha": "<dd.mm.aaaa>",
        "Elaborado por": "<consultor funcional>",
        "Estado": "Borrador para revisión con el desarrollador ABAP",
    },
    "secciones": [
        {"titulo": "Objetivo", "bloques": [{"tipo": "parrafo", "texto": "<qué problema de negocio resuelve>"}]},
        {"titulo": "Situación actual", "bloques": [{"tipo": "parrafo", "texto": "<cómo funciona hoy, según el código o la configuración revisada>"}]},
        {"titulo": "Alcance", "bloques": [{"tipo": "lista", "items": ["<qué incluye>"]}]},
        {"titulo": "Cambios requeridos", "bloques": [
            {"tipo": "tabla", "columnas": ["Nº", "Cambio", "Detalle"], "filas": [["1", "<cambio>", "<detalle>"]]},
            {"tipo": "subseccion", "titulo": "<detalle del cambio 1>", "bloques": [{"tipo": "parrafo", "texto": "<regla, ejemplos>"}]},
        ]},
        {"titulo": "Datos y tablas que intervienen", "bloques": [
            {"tipo": "tabla", "columnas": ["Dato", "Uso", "Mantenimiento"], "filas": [["<tabla-campo>", "<para qué>", "<quién/cómo>"]]}]},
        {"titulo": "Casos de prueba y criterios de aceptación", "bloques": [
            {"tipo": "tabla", "columnas": ["Nº", "Caso", "Resultado esperado"], "filas": [["1", "<caso>", "<resultado>"]]}]},
        {"titulo": "Prerrequisitos de configuración (no son ABAP)", "bloques": [{"tipo": "lista", "items": ["<customizing necesario>"]}]},
        {"titulo": "Fuera de alcance", "bloques": [{"tipo": "lista", "items": ["<qué no incluye>"]}]},
        {"titulo": "Puntos por confirmar", "bloques": [
            {"tipo": "tabla", "columnas": ["Nº", "Punto", "Con quién"], "filas": [["1", "<pregunta>", "<rol>"]]}]},
        {"titulo": "Fuentes", "bloques": [{"tipo": "lista", "items": ["<documentos, reuniones, código revisado>"]}]},
    ],
}

ET = {
    "titulo": "Especificación técnica: <objeto>",
    "subtitulo": "<referencia a la EF>",
    "ficha": {
        "Objeto": "<objetos principales>", "Módulo": "<módulo>", "Ticket": "<ticket>",
        "Orden de transporte": "<orden>", "Paquete": "<paquete>", "Fecha": "<dd.mm.aaaa>",
        "Elaborado por": "<desarrollador ABAP>", "Estado": "Borrador",
    },
    "secciones": [
        {"titulo": "Resumen técnico", "bloques": [{"tipo": "parrafo", "texto": "<qué se construye o modifica y cómo>"}]},
        {"titulo": "Objetos", "bloques": [
            {"tipo": "tabla", "columnas": ["Tipo", "Nombre", "Acción", "Paquete", "Orden"], "filas": [["<PROG/FUGR/CLAS/ENHO>", "<nombre>", "Nuevo/Modificado", "<paquete>", "<orden>"]]}]},
        {"titulo": "Diseño por objeto", "bloques": [
            {"tipo": "subseccion", "titulo": "<objeto>", "bloques": [
                {"tipo": "parrafo", "texto": "<punto de inserción: rutina, línea, enhancement>"},
                {"tipo": "codigo", "codigo": "<código propuesto>"}]}]},
        {"titulo": "Lógica", "bloques": [{"tipo": "lista", "numerada": True, "items": ["<paso de la lógica>"]}]},
        {"titulo": "Manejo de errores y mensajes", "bloques": [
            {"tipo": "tabla", "columnas": ["Situación", "Mensaje", "Tipo"], "filas": [["<caso>", "<clase/número - texto>", "E/W/I"]]}]},
        {"titulo": "Rendimiento y autorizaciones", "bloques": [{"tipo": "lista", "items": ["<accesos a BD, índices, AUTHORITY-CHECK>"]}]},
        {"titulo": "Pruebas unitarias", "bloques": [
            {"tipo": "tabla", "columnas": ["Nº", "Prueba", "Resultado esperado", "Resultado"], "filas": [["1", "<prueba>", "<esperado>", "<OK/NOK>"]]}]},
        {"titulo": "Riesgos y dependencias", "bloques": [{"tipo": "lista", "items": ["<riesgo>"]}]},
    ],
}

QA = {
    "titulo": "Dictamen QA: <objeto / requerimiento>",
    "subtitulo": "<ronda N de validación>",
    "ficha": {
        "Requerimiento": "<ticket>", "Objetos revisados": "<objetos>", "Sistema": "<SID/mandante>",
        "Ronda": "<1, 2, 3>", "Fecha": "<dd.mm.aaaa>", "Revisado por": "QA",
        "Resultado": "CONFORME | NO CONFORME",
    },
    "secciones": [
        {"titulo": "Resultado", "bloques": [{"tipo": "parrafo", "texto": "**CONFORME** / **NO CONFORME**: <motivo en una línea>"}]},
        {"titulo": "Observaciones", "bloques": [
            {"tipo": "tabla", "columnas": ["Nº", "Severidad", "Observación", "Responsable", "Estado"],
             "filas": [["1", "Crítica/Mayor/Menor", "<qué está mal, dónde y por qué>", "ABAP/Funcional", "Abierta/Cerrada"]]}]},
        {"titulo": "Cobertura de la EF", "bloques": [
            {"tipo": "tabla", "columnas": ["Requisito / caso EF", "Evidencia", "Cumple"], "filas": [["<caso>", "<captura, resultado>", "Sí/No"]]}]},
        {"titulo": "Revisión de código", "bloques": [{"tipo": "lista", "items": [
            "Sintaxis y activación", "Marcas de modificación (BOM/EOM)", "Rendimiento (SELECT en LOOP, SELECT *, índices)",
            "Manejo de errores y mensajes", "Autorizaciones", "Código muerto o hardcode no justificado"]}]},
        {"titulo": "Evidencia revisada", "bloques": [{"tipo": "lista", "items": ["<archivo o captura>"]}]},
    ],
}

INFORME = {
    "titulo": "<objeto o requerimiento>", "titulo_acento": "<palabra del título a resaltar>",
    "eyebrow": "<proyecto · sistema · módulo>", "lede": "<qué se hizo y en qué estado está, en dos frases>",
    "etiqueta_franja": "Informe técnico",
    "meta": {"Ticket": "<ticket>", "Sistema": "<SID/mandante>", "Orden": "<orden>", "Fecha": "<dd.mm.aaaa>"},
    "estado": [{"valor": "<n>", "etiqueta": "Cambios aplicados", "tipo": "ok"},
               {"valor": "<n>", "etiqueta": "Pruebas OK", "tipo": "info"},
               {"valor": "<n>", "etiqueta": "Pendientes", "tipo": "warn"},
               {"valor": "<CONFORME>", "etiqueta": "Dictamen QA", "tipo": "acc"}],
    "secciones": [
        {"id": "resumen", "titulo": "Resumen", "bloques": [{"tipo": "parrafo", "texto": "<resumen>"}]},
        {"id": "cambios", "titulo": "Cambios paso a paso", "bloques": [
            {"tipo": "paso", "numero": 1, "titulo": "<qué cambia>", "estado": "[[ok|Activo en DEV]]",
             "donde": {"Objeto": "`<programa>`", "Rutina": "`<FORM / método>`", "Línea": "<n>"},
             "antes": {"desde": 100, "codigo": "<líneas originales tal cual>"},
             "despues": {"codigo": "*BOM <ticket> - <descripción>\n<código nuevo, listo para copiar y pegar>\n*EOM <ticket>"},
             "porque": "**Qué cambia:** <efecto>"}]},
        {"id": "pruebas", "titulo": "Pruebas", "bloques": [
            {"tipo": "tabla", "columnas": ["Nº", "Caso", "Resultado esperado", "Resultado", "Responsable"],
             "filas": [["1", "<caso>", "<esperado>", "[[ok|OK]]", "<rol>"]]}]},
        {"id": "qa", "titulo": "Dictamen QA", "bloques": [{"tipo": "callout", "texto": "<resultado y observaciones abiertas>"}]},
        {"id": "pendientes", "titulo": "Pendientes y siguientes pasos", "bloques": [
            {"tipo": "tabla", "columnas": ["Nº", "Pendiente", "Responsable"], "filas": [["1", "<transporte a calidad, etc.>", "<rol>"]]}]},
    ],
    "pie": ["Fuentes: <código, documentos y reuniones revisados>"],
}

ESQUELETOS = {"ef": EF, "et": ET, "qa": QA, "informe": INFORME}
