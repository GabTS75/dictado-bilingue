# Plan por fases

> **El proyecto está en pausa tras la Fase 3** (prioridad al proyecto final de ASIR, los exámenes y las prácticas). Ver [RETOMAR.md](RETOMAR.md).

Plataforma inicial: **Windows 11** (Linux queda descartado por ahora). Lenguaje: **Python 3.12**.
Dirección: **bidireccional** (ES→EN y EN→ES, seleccionable).

| Fase | Objetivo | Estado |
|---|---|---|
| 0 | Decisiones previas y requisitos | Hecha |
| 1 | Transcripción local de prueba (ES y EN) y mediciones | **Hecha** (ver resultados abajo) |
| 2 | Traducción local en ambos sentidos; comparar modelos con frases reales | **Hecha** (cortafuegos de Ollama verificado; [detalle](../fases/02-traduccion/README.md)) |
| 3 | Atajo de teclado configurable (mantener para hablar) | **Hecha y probada** ([detalle](../fases/03-atajo/README.md)) |
| 4 | Escribir en la aplicación activa (sin portapapeles; respaldo con exclusión del historial) | Pendiente (en pausa) |
| 5 | Calidad: configuración, pruebas, comentarios, README, instalación en otro equipo | Pendiente (en pausa) |
| 6 | Endurecimiento de seguridad y guía de auditoría | Pendiente (en pausa) |
| 7 | Empaquetado para Windows | Pendiente (en pausa) |
| Final | Paquete de solicitud de autorización (tras todas las pruebas) | Pendiente (en pausa) |

## Resultados de la Fase 1 (portátil del usuario, Whisper large-v3-turbo, CPU int8)

- Carga del modelo: 3,4 s · Transcripción: 6,4 s para ~8 s de audio · Calidad subjetiva: 9/10.
- Español: transcripción correcta. Inglés (hablante no nativo): fallos puntuales
  (*these→the*, *thoroughly→thoughtfully*, *mains→main*, *appliance→appliances*).
- Prueba sin red (WiFi desconectado): funciona igual, español e inglés.
- Prueba con 25 s de español: transcripción 7,7 s (6,4 s con 8 s de audio). El tiempo apenas
  crece con la duración porque Whisper trabaja en ventanas fijas de 30 s: compensa dictar
  párrafos completos mejor que frases sueltas.
- Consecuencia de diseño: en la dirección EN→ES los fallos de transcripción pasan a la
  traducción. Ideas a evaluar más adelante: indicar vocabulario/contexto a Whisper
  (`initial_prompt`), probar el modelo `large-v3` completo, y una pantalla opcional de
  "revisar antes de escribir" que muestre texto original y traducción.

## Resultados de la Fase 2 (mismo portátil, CPU, Ollama 0.40.6)

Comparativa con 12 frases de ejemplo por sentido (el usuario valoró ambos modelos con 9,5/10):

| | `translategemma:4b` | `translategemma:12b` |
|---|---|---|
| Carga del modelo (1.ª vez) | 4,9 s (ES→EN) · 6,2 s (EN→ES) | 10,7 s · 11,3 s |
| Traducción media por frase corta | 3,0 s · 2,8 s | 9,1 s · 8,6 s |
| Velocidad | 17,0 · 17,7 tokens/s | 5,7 · 6,1 tokens/s |
| Espera total estimada (6,4 s de voz + traducción) | 9,4 s · 9,2 s | 15,5 s · 15,0 s |

Prueba completa `voz` con 12b (dictado de ~15 s, 3-4 frases): transcripción 7,1 s y 6,6 s,
traducción 14,5 s y 13,7 s, **espera total 21,5 s y 20,3 s**. Con 4b no se midió `voz`.

Decisión del usuario: **4b como modelo por defecto** (la calidad es casi igual y la espera
es mucho menor). 12b queda como opción de "calidad máxima" configurable.

Observaciones de la comparativa (revisión de las capturas):

- 4b tuvo **un error de sentido** en 12 frases ES→EN: "Ya me dirás qué te parece la
  propuesta" → "I'm sure you'll have an opinion on the proposal". 12b lo tradujo bien.
- Desvíos menores de 4b: añadió "AM" a "las diez", "talented" (no estaba) y cambió "estas
  piezas" por "todas las partes". 12b también añade "AM" cuando la hora viene en cifras:
  **resuelve en silencio una ambigüedad**, algo a vigilar en citas y horarios.
- En EN→ES ambos eligen **"usted"** por defecto (inglés no distingue tú/usted). Para
  correos entre compañeros en España suena rígido: pendiente de añadir una opción de
  registro (tú/usted) y probar la variante `es-ES`.
- En la prueba `voz` EN→ES, Whisper transcribió **"Thursday's" como "Saturday"** y
  **"client review" como "the cleaning"**; la traducción dio "sábado" y "limpieza" sin
  avisar. Es el riesgo ya anotado: el error de transcripción pasa a la traducción y el
  usuario solo ve el resultado final. Refuerza la necesidad de la pantalla "revisar antes de
  escribir" (Fase 4) mostrando original y traducción.
- Verificado por el usuario: Ollama escucha solo en `127.0.0.1:11434`.
- **Privacidad verificada:** con la regla de cortafuegos bien creada (rutas reales de `ollama.exe` y
  `ollama app.exe`), `ollama pull translategemma:4b` falla con *intento de acceso a un socket no
  permitido*; lo local sigue funcionando.

## Resultados de la Fase 3 (prueba en Windows real)

- Atajos (Ctrl der. / Mayús der.), pitidos y consola: correctos, sin molestias en otras apps.
- Espera total con 4b: 27,0 s para 46,3 s de dictado ES→EN; 8,1 s para 8,5 s EN→ES.
- Calidad de transcripción en dictado largo: pérdida de palabras y un «No» borrado que invirtió
  el sentido de una frase. Pendiente: banco de pruebas (`banco_transcripcion.py`), `large-v3`,
  y «revisar antes de escribir» (Fase 4).
- Mantener Mayús derecho 8 s activa «Teclas filtro» de Windows: desactivar su acceso rápido.

## Diseño bidireccional

El sentido se define con dos idiomas: `origen` y `destino`.

- ES→EN: `origen=es`, `destino=en`
- EN→ES: `origen=en`, `destino=es`

Whisper recibe siempre el idioma de origen (más rápido y preciso que la autodetección).
El traductor recibe el par de idiomas. En la Fase 3 el cambio de sentido tendrá un
atajo propio.

## Criterios de decisión de la Fase 2 (traducción)

Se compararán, con las mismas 20-30 frases tuyas en ambos sentidos:

1. Naturalidad ("¿lo diría un nativo?")
2. Corrección (sentido, tiempos verbales, registro formal/informal)
3. Tiempo de respuesta en tu equipo
4. Consumo de memoria

## Reglas de desarrollo

- Cada módulo hace una sola cosa y se puede probar por separado.
- Comentarios en español, funciones cortas, nombres claros.
- Ningún cambio se acepta si rompe un principio de [PRIVACIDAD.md](PRIVACIDAD.md).
