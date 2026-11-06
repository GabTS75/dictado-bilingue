# Dictado bilingüe local (ES ⇄ EN)

> **Estado: ⏸️ en pausa (después de la Fase 3).** Funciona, está medido y documentado, pero lo dejo aparcado momentánemaente a propósito. Más abajo te cuento por qué y cómo lo pienso retomar.

Este proyecto es en resumen, hablar en un idioma y que el texto aparezca escrito en otro, en la aplicación que tengas abierta: *un correo, un Word, el chat de una reunión*. Todo dentro de mi portátil, sin nube, sin cuentas, sin claves de API y sin que mi voz ni mi texto salgan de casa.

## Por qué lo empecé

Mi inglés es mi punto débil, y no me da vergüenza decirlo. **Quise convertir esa debilidad en un proyecto:** una herramienta mía, pequeña, que pudiera leer línea a línea y explicar sin tropezar. Además, trabajo con información que no debería viajar a servidores de terceros, y las herramientas públicas que encontré no me convencían: *no sabía qué hacían con el audio ni podía auditar su código*. Así que me dije: ***si no puedo fiarme, lo construyo yo***.

Previamente realicé una investigación regular sobre todo este tema y me puse tres reglas desde el primer día, y las he respetado en todo lo que hay en este repo:

1. **Todo local.** La voz y la traducción se procesan en mi equipo.
2. **Código pequeño, comentado y auditable**, pensado para que otra persona lo revise sin fiarse de mí.
3. **Mínimo acceso.** El micrófono solo se abre mientras mantengo el atajo, y del teclado solo se consulta el estado de esas dos teclas, no todo lo que escribo.

## Cómo funciona

Lo imagino como una cabina de interpretación con cuatro puestos, cada uno con una sola tarea:

```text
 Oreja             Transcriptor         Traductor               Mano
 atajo + micro ─►  Whisper (local)  ─►  TranslateGemma local ─►  escribe en la app activa
 (Fase 3 ✅)       (Fase 1 ✅)          (Fase 2 ✅)              (Fase 4 ⏳)
```

| Pieza | Tecnología | Cómo cuido la privacidad |
| :---: | --- | --- |
| Voz → texto | faster-whisper `large-v3-turbo` (CPU, int8) | Sin red; el audio vive solo en RAM y se pone a cero |
| Traducción | TranslateGemma 4b con Ollama en `127.0.0.1` | Le cierro la salida con el cortafuegos de Windows y lo compruebo |
| Atajo | `GetAsyncKeyState`, solo las teclas del atajo | No es un keylogger: sin ganchos ni librerías extra |

## Hasta dónde llegué

| Fase | Qué hice | Estado |
| :---: | --- | --- |
| [1](fases/01-transcripcion/README.md) | Transcripción local y mediciones, también sin WiFi | ✅ |
| [2](fases/02-traduccion/README.md) | Comparar modelos de traducción y blindar Ollama con el cortafuegos | ✅ |
| [3](fases/03-atajo/README.md) | Atajo «mantener para hablar» (Ctrl derecho / Mayús derecho) | ✅ probado en mi equipo |
| [4](fases/04-escritura-en-app/README.md) | Escribir en la aplicación activa, sin portapapeles | ⏳ sin empezar |
| [5](fases/05-calidad-e-instalacion/README.md) | Calidad, configuración, instalación en otro equipo | ⏳ sin empezar |
| [6](fases/06-seguridad-y-auditoria/README.md) | Endurecimiento y guía de auditoría | ⏳ sin empezar |
| [7](fases/07-empaquetado/README.md) | Empaquetado para Windows | ⏳ sin empezar |

Cada carpeta de fase tiene su propio README con el objetivo, cómo reproducirla, los números y las capturas que fui haciendo por el camino.

### Números en mi portátil (Core i7 de 13.ª gen, 32 GB, sin GPU)

- Transcribir 8 s de audio: unos 6,4 s. Y funciona con el WiFi apagado.
- Traducir una frase con `translategemma:4b`: unos 3 s. Con el 12b, casi 9 s, para una calidad que a mí me pareció igual de buena (9,5/10 los dos). Por eso gana el 4b.
- Un dictado de 46 s tardó 27 s en estar traducido. Se puede usar, aunque se nota la espera.

### Lo que no salió tan bien

La verdad es que la parte que más me preocupa no es la traducción, sino la transcripción de mi inglés con acento (risas). En un dictado largo, Whisper se comió un «No»: «No tengo claro si el servidor aguantará la carga» pasó a «Tengo claro…», y la traducción dijo justo lo contrario de lo que yo quería decir. El traductor hizo bien su trabajo con lo que recibió; el fallo estaba antes, en cómo lo dije. Es el tipo de error silencioso que no se ve hasta que es tarde, y por eso la Fase 4 incluía una pantalla de «revisar antes de escribir».

## Por qué lo pongo en pausa

Estoy a puertas de iniciar el tramo final de mi ciclo de ASIR: las prácticas en empresa que son obligatorias, el proyecto final (que es complejo, de los que piden cabeza entera), y los exámenes finales, además de mi vida familiar. No hay hueco para llevar esto al nivel de fiabilidad que me exige, y prefiero cerrarlo con honestidad antes que dejarlo a medias y sin explicar.

También hice un ejercicio de realismo: existen auriculares con traducción en tiempo real que resuelven buena parte de lo que yo buscaba. Pero no cubren lo mismo (ellos te dejan *escuchar* una conversación; yo quería *escribir* un correo) y, sobre todo, no tengo claro qué hacen con el audio. Me quedo con lo que sí me aporta este proyecto: *control total, nada en la nube y muchísimo aprendizaje sobre privacidad por diseño*.

## Cómo retomarlo

Cuando vuelva (no tengo fecha, pero sí ganas), el orden es este. Se puede revisar en detalle: [docs/RETOMAR.md](docs/RETOMAR.md).

1. Revisar si hay modelos de voz y traducción mejores; han cambiado mucho en poco tiempo.
2. Ejecutar el banco de pruebas de transcripción (`python -m dictado.banco_transcripcion`) y decidir con datos si basta con un ajuste o si hay que pasar a `large-v3`.
3. Fase 4: escribir en la aplicación activa, con revisión previa.
4. Fases 5 a 7: pulir, auditar y empaquetar.

## Puesta en marcha (Windows 11, PowerShell)

```powershell
winget install -e --id Python.Python.3.12        # si no tienes Python 3.12
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m dictado.comprobar_equipo               # ¿cumple tu equipo los requisitos?
python -m dictado.descargar_modelos              # único script propio con internet (~3 GB)
```

Después, [Fase 2](fases/02-traduccion/README.md) para Ollama y el cortafuegos, y [Fase 3](fases/03-atajo/README.md) para el uso diario.

## Documentación

- [Plan y resultados](docs/PLAN.md)
- [Requisitos mínimos del equipo](docs/REQUISITOS.md)
- [Principios de confidencialidad y flujo de datos](docs/PRIVACIDAD.md)
- [Cómo retomarlo](docs/RETOMAR.md)
- [Política de seguridad](SECURITY.md)

## Estructura

```text
dictado/                 => Código; cada módulo hace una sola cosa
  privacidad.py          => Bloqueo de red y autotest
  comprobar_equipo.py    => Requisitos mínimos
  descargar_modelos.py   => Único script propio con internet (modelo + huellas SHA-256)
  fase1_transcribir.py   => Grabar y transcribir
  banco_transcripcion.py => Compara ajustes de Whisper con mi voz (WER)
  traductor.py           => Traducción local vía Ollama (solo 127.0.0.1)
  fase2_traducir.py      => Comparador de modelos y prueba voz → traducción
  teclas.py              => Atajos: solo consulta las teclas del atajo
  config.py              => Configuración (por defecto + config.local.json)
  fase3_atajo.py         => Mantener para hablar
fases/                   => Un README por fase, con resultados y capturas
docs/                    => Plan, requisitos, privacidad y cómo retomarlo
pruebas/                 => Frases de ejemplo (mis *.local.txt no se suben)
config.ejemplo.json      => Plantilla de configuración
```

## Licencias de terceros

Los modelos no están en el repositorio. Whisper va con licencia MIT y TranslateGemma con la
[licencia Gemma](https://ai.google.dev/gemma/terms) de Google. Lo documentaré a fondo en la Fase 6.

## Licencia del código

Pendiente de decidir antes de hacerlo público.
