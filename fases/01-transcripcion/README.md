# Fase 1 · Transcripción local

> Estado: ✅ **completada y validada** en mi portátil.

**Objetivo:** convertir voz en texto en el propio equipo, medir tiempos y calidad en español e inglés, y comprobar que funciona **sin red**.

## Cómo funciona

Micrófono → memoria RAM → **faster-whisper** (modelo `large-v3-turbo`, CPU, `int8`) → texto. El audio no se guarda nunca; se descarta tras transcribir.

## Cómo reproducirlo

Ver «Puesta en marcha de la Fase 1» en el [README principal](../../README.md).

```powershell
python -m dictado.comprobar_equipo
python -m dictado.descargar_modelos          # único paso con internet (~3 GB)
python -m dictado.fase1_transcribir --idioma es --segundos 8
```

## Resultados (portátil del proyecto, CPU)

| Prueba | Resultado |
| --- | --- |
| Carga del modelo | 3,4 s (8,4 s en otra ejecución) |
| Transcripción de 8 s de audio | 6,4 s (factor 0,80) |
| Transcripción de 25 s de audio | 7,7 s (factor 0,31) |
| Español | Correcto |
| Inglés (hablante no nativo) | Fallos puntuales: *these→the*, *thoroughly→thoughtfully*, *mains→main*, *appliance→appliances* |
| Sin red (WiFi desconectado) | Idéntico: español e inglés |

Whisper trabaja en ventanas fijas de 30 s, por lo que el tiempo apenas crece con la duración:
conviene dictar párrafos completos.

## Evidencias

Aquí van mis capturas de la comprobación del equipo, la transcripción en español e inglés y la prueba sin WiFi (carpeta `capturas/`).

## Decisión de diseño que arrastra a las siguientes fases

Los errores de transcripción en inglés pasarán a la traducción inglés → español sin avisar. Por eso la [Fase 4](../04-escritura-en-app/README.md) incluirá «revisar antes de escribir».
