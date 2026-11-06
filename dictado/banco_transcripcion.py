"""Banco de pruebas de transcripción: ¿qué ajuste de Whisper te entiende mejor?

Analogía: es como probar varios audífonos con la MISMA canción. Grabas UNA vez
leyendo un texto conocido, y se prueban varios ajustes sobre ese mismo audio. Como
conocemos el texto correcto, se puede medir el error (WER) y ver qué palabras falla
cada ajuste. Así se decide con datos, no a ojo.

Qué mide:
  * WER: porcentaje de palabras erróneas (sustituidas + borradas + insertadas) sobre
    las del texto de referencia. Menos es mejor.
  * Una lista "esperado -> oído" para ver QUÉ falla (p. ej. un "no" perdido cambia el
    sentido de toda la frase).

Privacidad (igual que la Fase 1): red bloqueada, el audio solo vive en RAM y se pone a
cero al terminar, y el texto solo se muestra en pantalla. Usa frases NO confidenciales.

Uso:
    python -m dictado.banco_transcripcion --idioma es --frases 6
    python -m dictado.banco_transcripcion --idioma en --frases 6
    python -m dictado.banco_transcripcion --idioma es --modelos large-v3-turbo,large-v3
"""

# --- 1) PRIVACIDAD PRIMERO: antes de importar librerías de IA ------------------
from dictado.privacidad import bloquear_red

bloquear_red()

# --- 2) Resto de importaciones -------------------------------------------------
import argparse  # noqa: E402
import difflib  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent

# Pista de vocabulario para Whisper: no es una instrucción, solo contexto de estilo.
_PISTA = {
    "es": "Correo profesional: reunión, informe, servidor, cortafuegos, documentación.",
    "en": "Professional email: meeting, report, server, firewall, documentation.",
}

# Cada ajuste es un diccionario de opciones que sobrescribe las de la "base".
_BASE = dict(beam_size=5, vad_filter=True, vad_parameters={"min_silence_duration_ms": 500},
             condition_on_previous_text=False)


def ajustes(idioma: str) -> dict[str, dict]:
    """Ajustes a comparar. 'actual' es lo que usa hoy el programa."""
    return {
        "actual": {},
        "sin_vad": {"vad_filter": False, "vad_parameters": None},
        "vad_suave": {"vad_parameters": {"min_silence_duration_ms": 1000,
                                         "speech_pad_ms": 600, "threshold": 0.3}},
        "con_pista": {"initial_prompt": _PISTA[idioma]},
        "con_contexto": {"condition_on_previous_text": True},
    }


# ----------------------------- medición del error ------------------------------

def normalizar(texto: str) -> list[str]:
    """Minúsculas y sin signos de puntuación (se conservan letras con tilde y dígitos)."""
    return re.findall(r"[\w']+", texto.lower())


def comparar(esperado: str, oido: str) -> tuple[float, list[str]]:
    """Devuelve (WER en %, lista 'esperado -> oído' con las diferencias)."""
    e, o = normalizar(esperado), normalizar(oido)
    dif, errores = [], 0
    for tipo, i1, i2, j1, j2 in difflib.SequenceMatcher(a=e, b=o, autojunk=False).get_opcodes():
        if tipo == "equal":
            continue
        antes, despues = " ".join(e[i1:i2]), " ".join(o[j1:j2])
        errores += max(i2 - i1, j2 - j1)
        dif.append(f"{antes or '∅'} -> {despues or '∅ (borrado)'}")
    return (100.0 * errores / max(len(e), 1)), dif


# ----------------------------- transcripción -----------------------------------

def transcribir_con(modelo, audio, idioma: str, extra: dict) -> str:
    opciones = {**_BASE, **extra}
    segmentos, _ = modelo.transcribe(audio, language=idioma, task="transcribe", **opciones)
    return " ".join(s.text.strip() for s in segmentos).strip()


def leer_frases(ruta: Path, cuantas: int) -> list[str]:
    lineas = [l.strip() for l in ruta.read_text(encoding="utf-8-sig").splitlines()
              if l.strip() and not l.lstrip().startswith("#")]
    return lineas[:cuantas]


def evaluar(modelo, audio, idioma: str, referencia: str, lista: dict[str, dict]) -> list[dict]:
    """Prueba cada ajuste sobre el MISMO audio. Separado de la E/S para poder testearlo."""
    filas = []
    for nombre, extra in lista.items():
        inicio = time.perf_counter()
        texto = transcribir_con(modelo, audio, idioma, extra)
        segundos = time.perf_counter() - inicio
        wer, dif = comparar(referencia, texto)
        filas.append({"ajuste": nombre, "wer": wer, "segundos": segundos, "dif": dif})
    return filas


def main() -> int:
    from dictado import fase1_transcribir as f1

    parser = argparse.ArgumentParser(description="Compara ajustes de Whisper con tu voz.")
    parser.add_argument("--idioma", choices=["es", "en"], default="es")
    parser.add_argument("--frases", type=int, default=6, help="Cuántas frases de ejemplo leer")
    parser.add_argument("--archivo", type=Path, default=None, help="Frases (por defecto pruebas/ejemplo_<idioma>.txt)")
    parser.add_argument("--segundos", type=float, default=0, help="Duración fija (0 = calculada: 8 s por frase)")
    parser.add_argument("--modelos", default=f1.MODELO_POR_DEFECTO, help="Lista separada por comas")
    parser.add_argument("--hilos", type=int, default=0)
    parser.add_argument("--dispositivo", type=int, default=None)
    args = parser.parse_args()

    archivo = args.archivo or RAIZ / "pruebas" / f"ejemplo_{args.idioma}.txt"
    frases = leer_frases(archivo, args.frases)
    referencia = " ".join(frases)
    segundos = args.segundos or max(10.0, 8.0 * len(frases))

    print("Lee en voz alta, a tu ritmo normal y con pausas naturales, este texto:\n")
    for frase in frases:
        print(f"  {frase}")
    input(f"\nPulsa Intro y empieza a leer ({segundos:g} s de grabación; pitido al empezar)... ")
    audio = f1.grabar(segundos, args.dispositivo)

    try:
        for nombre_modelo in [m.strip() for m in args.modelos.split(",") if m.strip()]:
            if not (f1.MODELOS_DIR / nombre_modelo).exists():
                print(f"\n[{nombre_modelo}] no está descargado: se omite "
                      f"(descárgalo con: python -m dictado.descargar_modelos --modelo {nombre_modelo}).")
                continue
            print(f"\n=== Modelo {nombre_modelo} ===")
            modelo = f1.cargar_modelo(nombre_modelo, args.hilos)
            filas = evaluar(modelo, audio, args.idioma, referencia, ajustes(args.idioma))
            del modelo
            print(f"{'ajuste':<14}{'WER %':>7}{'tiempo':>9}   diferencias (esperado -> oído)")
            for fila in sorted(filas, key=lambda x: x["wer"]):
                resumen = "; ".join(fila["dif"][:8]) + (" ..." if len(fila["dif"]) > 8 else "")
                print(f"{fila['ajuste']:<14}{fila['wer']:>7.1f}{fila['segundos']:>8.1f}s   {resumen}")
    finally:
        audio[:] = 0   # privacidad: el audio se pone a cero pase lo que pase
        del audio
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
