# Cómo retomarlo

Escribo esto para mi yo del futuro, que seguramente habrá olvidado la mitad (risas). Y es que cuando vuelva a abrir el proyecto, lo último que quiero es perder una tarde entendiendo dónde me quedé.

## Dónde lo dejé

- **Fases 1 a 3 terminadas y probadas** en mi portátil con Windows 11: transcribir, traducir y disparar todo con un atajo (Ctrl derecho: hablo español y sale inglés; Mayús derecho: al revés).
- **Todavía no escribe en otras aplicaciones**; muestra el resultado en la consola.
- Ollama tiene la salida de red bloqueada con el cortafuegos (comprobado con `ollama pull`).
- Modelo por defecto: `translategemma:4b`. El 12b queda como opción de calidad máxima.

## Lo pendiente, por orden de importancia

1. **Fiabilidad de la transcripción con mi inglés.** Es el cuello de botella real. Probar el banco (`python -m dictado.banco_transcripcion --idioma en --frases 6`), comparar `large-v3` con `large-v3-turbo` y mirar si ayudan la pista de vocabulario o un VAD más suave.
2. **Fase 4: escribir en la aplicación activa**, sin portapapeles (`SendInput` Unicode), esperando a que suelte el atajo, y con pantalla de «revisar antes de escribir» (original + traducción).
3. **Registro tú/usted y variante `es-ES`.** En EN→ES ambos modelos usan «usted» por defecto y en un correo entre compañeros suena rígido.
4. **Aviso de «Teclas filtro»** al mantener Mayús derecho 8 s: cambiar `en-es` a otra tecla, aunque ya lo desactivé, pero merece recordarlo.
5. **Fases 5 a 7:** instalación en otro equipo, dependencias con huellas (*hashes*), guía de auditoría, empaquetado y, al final, el paquete de solicitud de autorización.

## Pasos concretos para volver a arrancar

```powershell
cd <carpeta-del-proyecto>
.venv\Scripts\Activate.ps1
python -m dictado.privacidad                     # autotest del bloqueo de red: debe terminar en OK
python -m dictado.fase3_atajo --mostrar-config
python -m dictado.fase3_atajo                    # comprobar que todo sigue funcionando
```

Si algo no arranca, verificar:

- ¿Ollama sigue en ejecución y con los modelos? `ollama list`
- ¿Sigue activa la regla del cortafuegos? `Get-NetFirewallRule -DisplayName "Bloquear salida - Ollama*"`
- ¿Python 3.12 y el `.venv` siguen ahí? `py --list`
- Los modelos de Whisper viven en `models/` (no están en el repositorio): `python -m dictado.descargar_modelos`

## Antes de seguir, preguntarme esto

- ¿Han salido modelos de voz o de traducción claramente mejores desde la última vez?
- ¿Mi inglés sigue siendo el problema, o ya me defiendo mejor? (Ojalá lo segundo, +risas)
- ¿Los auriculares con traducción cubren ya lo que necesito, con garantías de privacidad que pueda comprobar?
- ¿Tengo tiempo real para llegar a la Fase 4 sin sacrificar lo importante?

Si las respuestas siguen apuntando a «sí, merece la pena», entonces *¡adelante!*. Y si no, **también habrá valido la pena:** *aprendí a medir, a documentar y a diseñar pensando primero en la privacidad*.
