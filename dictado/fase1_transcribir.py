"""Fase 1: graba unos segundos de voz y los transcribe EN LOCAL (sin red).

Sirve para medir calidad y velocidad de la transcripción en tu equipo, en
español y en inglés, antes de construir el resto.

Garantías de privacidad de este script:
  * La red está bloqueada (salvo localhost) antes de cargar ninguna librería.
  * El audio solo existe en memoria RAM; no se escribe ningún archivo.
  * El texto solo se muestra en pantalla; no se guarda ni se registra.

Uso:
    python -m dictado.fase1_transcribir --idioma es --segundos 8
    python -m dictado.fase1_transcribir --idioma en --segundos 8
    python -m dictado.fase1_transcribir --listar-dispositivos
"""

# --- 1) PRIVACIDAD PRIMERO: debe ir antes de importar librerías de IA ---------
from dictado.privacidad import bloquear_red

bloquear_red()

# --- 2) Resto de importaciones -------------------------------------------------
import argparse  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
MODELOS_DIR = RAIZ / "models" / "whisper"
MODELO_POR_DEFECTO = "large-v3-turbo"
FRECUENCIA = 16_000  # Whisper trabaja a 16 kHz, mono


def listar_dispositivos() -> None:
    import sounddevice as sd

    print("Dispositivos de entrada (micrófonos):")
    for indice, dispositivo in enumerate(sd.query_devices()):
        if dispositivo["max_input_channels"] > 0:
            print(f"  [{indice}] {dispositivo['name']}")


def grabar(segundos: float, dispositivo: int | None) -> np.ndarray:
    """Graba `segundos` de audio mono a 16 kHz y lo devuelve como vector float32 en RAM."""
    import sounddevice as sd

    print(f"\nGrabando {segundos:g} s... ¡habla ahora!")
    audio = sd.rec(
        int(segundos * FRECUENCIA),
        samplerate=FRECUENCIA,
        channels=1,
        dtype="float32",
        device=dispositivo,
    )
    sd.wait()
    print("Grabación terminada.")
    return audio[:, 0].copy()  # de (n,1) a (n,)


def cargar_modelo(nombre: str, hilos: int):
    from faster_whisper import WhisperModel

    ruta = MODELOS_DIR / nombre
    if not ruta.exists():
        raise SystemExit(
            f"No encuentro el modelo en {ruta}\n"
            "Descárgalo primero con:  python -m dictado.descargar_modelos"
        )
    # int8 en CPU: buen equilibrio entre velocidad y calidad sin GPU.
    return WhisperModel(
        str(ruta), device="cpu", compute_type="int8", cpu_threads=hilos, local_files_only=True
    )


def transcribir(modelo, audio: np.ndarray, idioma: str) -> str:
    segmentos, _info = modelo.transcribe(
        audio,
        language=idioma,              # idioma indicado: más rápido y fiable que autodetectar
        task="transcribe",            # transcribir (NO traducir) en esta fase
        beam_size=5,
        vad_filter=True,              # ignora silencios (evita "texto inventado")
        vad_parameters={"min_silence_duration_ms": 500},
        condition_on_previous_text=False,
    )
    # `segmentos` es un generador: el trabajo real ocurre al recorrerlo.
    return " ".join(s.text.strip() for s in segmentos).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba de transcripción local (Fase 1).")
    parser.add_argument("--idioma", choices=["es", "en"], default="es", help="Idioma que vas a hablar")
    parser.add_argument("--segundos", type=float, default=8.0, help="Duración de la grabación")
    parser.add_argument("--modelo", default=MODELO_POR_DEFECTO, help="Carpeta del modelo en models/whisper/")
    parser.add_argument("--hilos", type=int, default=0, help="Hilos de CPU (0 = automático)")
    parser.add_argument("--dispositivo", type=int, default=None, help="Índice del micrófono")
    parser.add_argument("--listar-dispositivos", action="store_true", help="Mostrar micrófonos y salir")
    args = parser.parse_args()

    if args.listar_dispositivos:
        listar_dispositivos()
        return 0

    inicio = time.perf_counter()
    print(f"Cargando modelo '{args.modelo}' (solo ocurre al iniciar)...")
    modelo = cargar_modelo(args.modelo, args.hilos)
    t_carga = time.perf_counter() - inicio

    audio = grabar(args.segundos, args.dispositivo)

    print("Transcribiendo...")
    inicio = time.perf_counter()
    texto = transcribir(modelo, audio, args.idioma)
    t_transcripcion = time.perf_counter() - inicio

    # Privacidad: poner a cero el audio en cuanto deja de hacer falta
    # (mejor esfuerzo; Python no garantiza el borrado físico de la RAM).
    audio[:] = 0
    del audio

    print("\n--- TEXTO ---")
    print(texto if texto else "(no se detectó voz)")
    print("-------------")
    print(f"Carga del modelo : {t_carga:6.1f} s")
    print(f"Transcripción    : {t_transcripcion:6.1f} s  (para {args.segundos:g} s de audio)")
    print(f"Factor tiempo    : {t_transcripcion / args.segundos:6.2f}  (<1 = más rápido que tu voz)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
