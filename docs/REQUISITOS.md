# Requisitos del equipo

> **Estado: provisionales.** Las cifras se han estimado a partir del tamaño de los modelos
> y de la documentación de las herramientas. Se confirmarán o corregirán con las
> mediciones reales de las Fases 1 y 2 (y se actualizará este documento).

El script `python -m dictado.comprobar_equipo` verifica estos puntos automáticamente.

## Resumen

| Componente | Mínimo (funciona) | Recomendado (rendimiento óptimo) |
|---|---|---|
| Sistema operativo | Windows 10/11 de 64 bits | Windows 11 de 64 bits |
| Procesador | 4 núcleos, x64 con AVX2 | 8 o más núcleos, Intel 12.ª gen / AMD Ryzen 5000 o superior |
| Memoria RAM | 16 GB | 32 GB |
| Disco libre | 15 GB | 25 GB (SSD) |
| GPU dedicada | No necesaria | Opcional: acelera mucho la transcripción y la traducción |
| Micrófono | Cualquiera reconocido por Windows | Micrófono de diadema o con cancelación de ruido |
| Python | 3.12 | 3.12 |
| Red | Solo para la instalación inicial | Ninguna durante el uso |

## Por qué estos valores

- **RAM:** el modelo de voz ocupa unos 3 GB y el modelo de traducción, según su tamaño,
  entre ~3 GB (modelos pequeños) y ~8 GB o más (modelos medianos). Sumado al sistema y
  a tus aplicaciones abiertas (Word, navegador, videollamada), 16 GB obliga a usar
  modelos pequeños; con 32 GB se pueden usar modelos medianos de mejor calidad.
- **Disco:** los modelos se descargan una vez y se guardan en la carpeta `models/`
  del proyecto (unos 3 GB de voz + el modelo de traducción).
- **CPU:** sin GPU, todo se ejecuta en el procesador. Más núcleos y más generación
  reducen la espera entre soltar la tecla y ver el texto.
- **Python 3.12:** algunas dependencias de transcripción (ctranslate2) no publican
  todavía paquetes para versiones más nuevas como 3.14.

## Qué esperar sin GPU (equipos tipo portátil con i7 de 13.ª generación y 32 GB)

La transcripción y la traducción funcionan, pero con una espera de unos segundos tras
soltar la tecla. Las cifras exactas se medirán en la Fase 1 y 2 y se anotarán aquí:

| Medida (frase de ~8 s) | Resultado |
|---|---|
| Carga del modelo de voz (una vez al iniciar) | **3,4 s** (medido, Fase 1) |
| Transcripción (Whisper large-v3-turbo, CPU int8) | **6,4 s** (medido, Fase 1) |
| Traducción de una frase corta con `translategemma:4b` | **~3 s** (medido, Fase 2) |
| Traducción de una frase corta con `translategemma:12b` | **~9 s** (medido, Fase 2) |
| Espera total estimada (voz + traducción) con 4b | **~9 s** (estimada; `voz` solo medido con 12b) |
| Espera total medida con 12b (dictado de ~15 s) | **20-21 s** (medido, Fase 2) |

Medido en un portátil Lenovo IdeaPad Slim 5 16IRH10 (Core i7 de 13.ª gen, 32 GB de
RAM DDR5, sin GPU dedicada), Windows 11 y Python 3.12. Cada ejecución arranca en frío
(carga el modelo y transcribe una sola vez), así que en una aplicación que se quede
abierta las siguientes transcripciones podrían ser algo más rápidas (a confirmar).

Nota sobre el "factor tiempo" (0,80 con 8 s de audio): Whisper procesa el audio en
ventanas fijas de 30 s, así que el tiempo **no** crece en proporción a lo que hablas.
**Confirmado con una prueba de 25 s de audio:** la transcripción tardó 7,7 s (factor
0,31), frente a 6,4 s con 8 s de audio. Es decir, con 3 veces más audio el tiempo solo
subió un 20 %. La carga del modelo salió en 8,4 s en esa ejecución (3,4 s en las
anteriores): varía de una ejecución a otra, probablemente por la caché del disco (sin
verificar), y solo se paga una vez al arrancar. Por encima de 30 s de audio cabe esperar
que se sume otra ventana (sin medir).

### Modelos de traducción (tamaños de la biblioteca de Ollama)

| Modelo | Tamaño |
|---|---|
| `translategemma:4b` | 3,3 GB |
| `translategemma:12b` | 8,1 GB |
| `translategemma:27b` | 17 GB (no recomendado en CPU) |

## Si tu equipo no llega al mínimo

- Usar un modelo de voz más pequeño (`small` o `medium`): menos preciso pero más ligero.
- Usar un modelo de traducción pequeño.
- Cerrar aplicaciones pesadas durante el dictado.
