# Fase 4 · Escribir en la aplicación activa

> Estado: ⏸️ **sin empezar, en pausa.** Es lo primero que haré al retomar el proyecto: ver [cómo retomarlo](../../docs/RETOMAR.md).

**Objetivo:** Que el texto traducido aparezca donde tengas el cursor (correo, Word, chat de reunión) sin pasar por el portapapeles.

## Alcance previsto

- Escritura carácter a carácter con `SendInput` (Unicode), sin portapapeles.
- Esperar a que sueltes el atajo antes de escribir, para no mezclar teclas.
- Respaldo con portapapeles **excluido del historial** de Windows (Win+V) si alguna aplicación no admite la escritura directa.
- Pantalla opcional «revisar antes de escribir» con original y traducción (los errores de transcripción pasan a la traducción sin avisar: ver Fase 2).

## Evidencias

*Se añadirán capturas y resultados al completar la fase.*
