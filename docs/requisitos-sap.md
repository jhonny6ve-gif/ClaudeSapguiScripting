# Habilitar SAP GUI Scripting

Para que funcione hay que habilitar el scripting en **dos lados**.

## 1. Servidor SAP (lo hace Basis)

Parámetro de perfil **`sapgui/user_scripting = TRUE`**, en la transacción RZ11 o en el perfil de instancia.

- En RZ11 el cambio es dinámico, pero se pierde al reiniciar si no queda también en el perfil.
- Parámetros relacionados, opcionales:
  - `sapgui/user_scripting_per_user = TRUE` exige además la autorización `S_SCR` (actividad 16) en el rol del usuario.
  - `sapgui/user_scripting_disable_recording`
  - `sapgui/user_scripting_force_notification`

Para comprobarlo, `listar_sesiones` muestra `scripting_bloqueado_por_servidor`. Si sale `true`, el servidor no lo permite.

## 2. Cliente SAP GUI (lo haces tú)

En SAP Logon: **Opciones → Accesibilidad y scripting → Scripting**.
- Marcar **Habilitar scripting**.
- Desmarcar **Notificar si un script se conecta a SAP GUI** y **Notificar si un script abre una conexión**. Si quedan marcadas, SAP GUI muestra un aviso en cada conexión y hay que aceptarlo a mano.

Si la opción aparece deshabilitada, es una política de la empresa (registro de Windows). Consúltalo con tu área de soporte.

## Comprobación rápida

1. Inicia sesión en un sistema con SAP Logon.
2. En Claude: "Lista mis sesiones de SAP".
3. Tiene que aparecer el sistema, el mandante y tu usuario.
