# Principios de confidencialidad

La confidencialidad es un **requisito de diseño**, no una función añadida. Cada decisión
del proyecto debe cumplir estos principios; si no los cumple, no se incorpora.

## Los 9 principios

1. **Todo local.** La grabación, la transcripción y la traducción se ejecutan en el propio
   equipo. No se usan servicios en la nube ni claves de API.
2. **Una sola puerta a internet.** Solo `descargar_modelos.py` puede usar la red, y solo
   para bajar los modelos una vez. El resto del programa se ejecuta sin red.
3. **Red bloqueada por código.** Además de no usarla, el programa bloquea cualquier
   conexión que no sea al propio equipo (`localhost`). Ver `dictado/privacidad.py`.
4. **Nada se guarda.** El audio vive solo en memoria RAM y se descarta tras transcribir.
   El texto dictado no se escribe en disco ni en registros (logs).
5. **Sin telemetría ni actualizaciones automáticas.** El programa nunca "llama a casa".
6. **Registros sin contenido.** Si hay logs, solo contienen eventos técnicos (tiempos,
   errores), jamás el texto ni el audio.
7. **Pocas dependencias, fijadas y verificables.** Cada dependencia se justifica, se
   fija a una versión concreta y (antes de publicar) con huellas (*hashes*).
8. **Auditable por terceros.** Código comentado, documentación del flujo de datos y
   guía de verificación para que cualquiera pueda comprobarlo sin fiarse de nosotros.
9. **Mínimo acceso a micrófono y teclado.** El micrófono solo está abierto mientras
   mantienes el atajo. Del teclado solo se consulta el estado de las teclas del atajo
   (nunca lo que escribes), y la lista exacta se muestra al arrancar.

## Flujo de datos (Fases 1 a 3)

En la Fase 3 el disparador es el atajo: al mantenerlo se abre el micrófono; al soltarlo se
cierra y comienza la cadena siguiente. Del teclado solo entra "¿está pulsada la tecla X?"
para las teclas del atajo (`dictado/teclas.py`).

```
Micrófono ──► memoria RAM (audio) ──► Whisper local ──► texto original ──► Ollama (127.0.0.1) ──► texto traducido
                    │                                        │                                         │
                    └── se pone a cero al terminar           └── no se guarda                          └── no se guarda
```

No hay ninguna flecha que salga del equipo.

**Excepción documentada (Fase 2):** Ollama es un programa externo con su propio proceso.
Este proyecto solo le habla por `127.0.0.1`, pero no controla lo que haga Ollama por su
cuenta (por ejemplo, buscar o descargar actualizaciones). Por eso `fases/02-traduccion/README.md` pide
cerrarle la salida con una regla del cortafuegos de Windows una vez descargados los
modelos. Los pasos con internet son, por tanto, solo dos: `descargar_modelos.py` y
`ollama pull`.

## Límites honestos (lo que NO garantizamos)

- **El bloqueo de red en Python es una capa de defensa, no una garantía absoluta.**
  Una librería con código nativo podría saltárselo. Por eso la verificación real es
  externa: ver "Cómo verificarlo tú mismo".
- **Borrado de memoria:** Python no garantiza borrar físicamente la RAM. Ponemos a cero
  los datos de audio en cuanto dejan de hacer falta, pero el sistema operativo puede
  haber copiado páginas de memoria al archivo de paginación.
- **Windows y el portapapeles:** el historial del portapapeles (Win+V) y su sincronización
  en la nube podrían guardar texto. Por eso la Fase 4 escribirá el texto directamente
  (sin portapapeles) y, si hiciera falta usarlo, lo excluirá del historial.
- **Los modelos son de terceros.** Se comprueban con huellas SHA-256 y sus licencias
  se documentarán, pero no hemos auditado sus pesos internos.
- **Antivirus:** un programa que consulta teclas puede ser marcado como sospechoso, aunque
  aquí solo se consultan las del atajo. Es esperable; ver `fases/03-atajo/README.md`.
- **El texto se muestra en la consola** (hasta la Fase 4) y el historial de PowerShell lo
  conserva mientras la ventana siga abierta. Cierra la ventana o usa `cls`.
- **Lo que consulta `GetAsyncKeyState` lo decide este código:** quien lo modifique podría
  consultar más teclas. Por eso `--mostrar-config` lista las teclas vigiladas y la lectura
  está aislada en un único archivo pequeño.

## Cómo verificarlo tú mismo

1. **Autotest del bloqueo:** `python -m dictado.privacidad` debe terminar con "OK".
2. **Comprobar conexiones durante el uso (PowerShell):**
   ```powershell
   Get-NetTCPConnection -OwningProcess (Get-Process python).Id
   ```
   No debe aparecer ninguna conexión a direcciones externas.
3. **Prueba definitiva:** desconectar el Wi-Fi / activar el modo avión y comprobar que
   la transcripción funciona igual.
4. **Cortafuegos de Windows:** crear una regla que bloquee la salida de `python.exe`
   del entorno `.venv` (la descarga de modelos se hace antes de crearla).
5. **Revisar las huellas** de los modelos en `models/whisper/*/SHA256SUMS.txt`.

## Registro de decisiones de privacidad

| Fase | Decisión | Motivo |
|---|---|---|
| 1 | Modelos en `models/` dentro del proyecto, no en la caché global | Portable y auditable |
| 1 | Variables `HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE` activas al ejecutar | Impide descargas accidentales |
| 1 | El audio no se guarda nunca (ni opcionalmente) | Menos superficie de riesgo |
| 1 | Verificado por el usuario: transcripción idéntica con el WiFi desconectado | Prueba definitiva nº 3 de la guía |
| 2 | Motor de traducción: Ollama, solo hablando con 127.0.0.1 y sin proxies | Sin dependencias nuevas; decisión revisable en la Fase 6 |
| 2 | Regla de firewall que bloquea la salida de Ollama (sus dos ejecutables) tras descargar modelos | Ollama no está bajo el bloqueo de red de Python. **Verificado por el usuario**: `ollama pull translategemma:4b` falla con *intento de acceso a un socket no permitido* |
| 2 | Verificado por el usuario: Ollama escucha solo en `127.0.0.1:11434` | Comprobado con `Get-NetTCPConnection` |
| 2 | Frases de prueba propias en `pruebas/*.local.txt`, excluidas de git | Pueden contener datos confidenciales |
| 2 | El texto de errores de Ollama no se muestra | Evita arrastrar texto del usuario a mensajes o registros |
| 3 | Atajo leído con `GetAsyncKeyState` solo para las teclas del atajo; sin ganchos ni librerías | El programa no puede saber qué escribes |
| 3 | Atajos por defecto Ctrl derecho / Mayús derecho; se rechazan `Ctrl+Alt` y `ralt` | En teclados con AltGr (español) `Ctrl+Alt` se activaría al escribir `@`, `#`, `€` |
| 3 | Micrófono abierto solo mientras se mantiene el atajo; pitido de inicio antes de abrirlo | Mínimo acceso; el pitido no se graba |
| 3 | Audio en RAM con tope de 60 s y puesto a cero al terminar (también con `Ctrl+C`) | Sin acumulación ni restos |
| 3 | Configuración en `config.local.json`, fuera de git, con claves estrictas | Una errata no se ignora en silencio |
