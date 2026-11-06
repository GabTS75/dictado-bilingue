"""Fase 2: traducción local ES <-> EN. Compara modelos y prueba "voz -> texto traducido".

Dos modos:

  comparar  Traduce una lista de frases con varios modelos y los pone lado a lado,
            con tiempos. Sirve para ELEGIR el modelo con TUS frases.
  voz       Graba tu voz, la transcribe (Whisper, Fase 1) y la traduce.
            Es la experiencia completa, todavía sin atajo de teclado ni escritura
            en otras aplicaciones (eso llega en las Fases 3 y 4).

Privacidad:
  * La red está bloqueada (salvo 127.0.0.1) antes de importar nada más.
  * No se guarda audio ni texto: todo se muestra en pantalla y se descarta.

Ejemplos:
    python -m dictado.fase2_traducir comparar --sentido es-en
    python -m dictado.fase2_traducir comparar --sentido en-es --modelos translategemma:4b,translategemma:12b
    python -m dictado.fase2_traducir voz --sentido es-en --segundos 15
"""

# --- PRIVACIDAD PRIMERO ---------------------------------------------------------
from dictado.privacidad import bloquear_red

bloquear_red()

# --- Resto de importaciones -----------------------------------------------------
import argparse  # noqa: E402
import statistics  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

from dictado import traductor  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SENTIDOS = {"es-en": ("es", "en"), "en-es": ("en", "es")}
MODELOS_POR_DEFECTO = "translategemma:4b,translategemma:12b"
MODELO_VOZ_POR_DEFECTO = "translategemma:12b"


def leer_frases(ruta: Path) -> list[str]:
    """Una frase por línea. Se ignoran líneas vacías y las que empiezan por '#'."""
    # utf-8-sig: el Bloc de notas de Windows suele añadir una marca (BOM) al guardar.
    lineas = ruta.read_text(encoding="utf-8-sig").splitlines()
    return [l.strip() for l in lineas if l.strip() and not l.strip().startswith("#")]


def comprobar_modelos(modelos: list[str]) -> bool:
    """Verifica que Ollama responde y que los modelos están instalados."""
    faltan = traductor.modelos_que_faltan(modelos)
    if not faltan:
        return True
    print("Faltan estos modelos en Ollama:")
    for modelo in faltan:
        print(f"  - {modelo}      ->  ollama pull {modelo}")
    print("(Descargar es un paso con internet. Ver fases/02-traduccion/README.md.)")
    return False


def comparar(args: argparse.Namespace) -> int:
    origen, destino = SENTIDOS[args.sentido]
    modelos = [m.strip() for m in args.modelos.split(",") if m.strip()]
    ruta = Path(args.frases) if args.frases else RAIZ / "pruebas" / f"ejemplo_{origen}.txt"
    if not ruta.exists():
        print(f"No encuentro el archivo de frases: {ruta}")
        return 1
    frases = leer_frases(ruta)
    if not frases:
        print("El archivo de frases está vacío.")
        return 1
    if not comprobar_modelos(modelos):
        return 1

    print(f"Sentido: {origen.upper()} -> {destino.upper()}   |   {len(frases)} frases   |   modelos: {', '.join(modelos)}")
    print("Valora cada traducción: ¿la diría un nativo? ¿Es correcta, natural y mantiene el tono?\n")

    estadisticas = {m: {"cargas": [], "tiempos": [], "velocidades": []} for m in modelos}
    try:
        for numero, frase in enumerate(frases, 1):
            print(f"[{numero}/{len(frases)}] {origen.upper()}: {frase}")
            for modelo in modelos:
                r = traductor.traducir(frase, origen, destino, modelo)
                e = estadisticas[modelo]
                e["cargas"].append(r.segundos_carga)
                e["tiempos"].append(r.segundos_traduccion)
                e["velocidades"].append(r.tokens_por_segundo)
                print(f"   {modelo:<22} ({r.segundos_traduccion:4.1f} s) {r.texto}")
            print()
    finally:
        for modelo in modelos:  # liberar RAM aunque se interrumpa con Ctrl+C
            traductor.liberar(modelo)

    print("RESUMEN (media por frase; la carga del modelo se cuenta aparte)")
    print(f"{'modelo':<22} {'carga':>8} {'traducción':>12} {'tokens/s':>9}  {'espera estimada*':>17}")
    for modelo, e in estadisticas.items():
        media = statistics.mean(e["tiempos"])
        espera = args.t_transcripcion + media
        print(f"{modelo:<22} {max(e['cargas']):>6.1f} s {media:>10.1f} s {statistics.mean(e['velocidades']):>9.1f}  {espera:>15.1f} s")
    print(f"* espera estimada = {args.t_transcripcion:g} s de transcripción (tu medida de la Fase 1) + traducción media.")
    return 0


def voz(args: argparse.Namespace) -> int:
    origen, destino = SENTIDOS[args.sentido]
    if not comprobar_modelos([args.modelo]):  # antes de grabar: no perder tu tiempo
        return 1

    from dictado import fase1_transcribir as f1  # reutiliza la Fase 1

    print(f"Cargando Whisper '{args.modelo_voz}'...")
    modelo_voz = f1.cargar_modelo(args.modelo_voz, args.hilos)
    audio = f1.grabar(args.segundos, args.dispositivo)

    print("Transcribiendo...")
    inicio = time.perf_counter()
    texto = f1.transcribir(modelo_voz, audio, origen)
    t_transcripcion = time.perf_counter() - inicio

    audio[:] = 0  # el audio ya no hace falta: se pone a cero (mejor esfuerzo)
    del audio

    if not texto:
        print("(no se detectó voz)")
        return 0

    print(f"Traduciendo con {args.modelo}...")
    # El modelo queda 10 min en RAM para que la siguiente traducción sea más rápida.
    r = traductor.traducir(texto, origen, destino, args.modelo)

    print(f"\n--- {origen.upper()} (lo que dijiste) ---\n{texto}")
    print(f"\n--- {destino.upper()} (traducción) ---\n{r.texto}\n")
    print(f"Transcripción: {t_transcripcion:5.1f} s")
    print(f"Traducción   : {r.segundos_traduccion:5.1f} s   (carga del modelo: {r.segundos_carga:.1f} s, solo la 1.ª vez)")
    print(f"Espera total : {t_transcripcion + r.segundos_traduccion:5.1f} s   (desde que dejas de hablar)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Fase 2: traducción local ES <-> EN.")
    sub = parser.add_subparsers(dest="modo", required=True)

    p1 = sub.add_parser("comparar", help="Comparar modelos con una lista de frases")
    p1.add_argument("--sentido", choices=SENTIDOS, required=True, help="es-en o en-es")
    p1.add_argument("--modelos", default=MODELOS_POR_DEFECTO, help="Modelos de Ollama separados por comas")
    p1.add_argument("--frases", help="Archivo de frases (por defecto, pruebas/ejemplo_<idioma>.txt)")
    p1.add_argument("--t-transcripcion", type=float, default=6.4,
                    help="Segundos de transcripción medidos en la Fase 1 (para estimar la espera total)")
    p1.set_defaults(funcion=comparar)

    p2 = sub.add_parser("voz", help="Grabar voz, transcribir y traducir")
    p2.add_argument("--sentido", choices=SENTIDOS, required=True, help="es-en o en-es")
    p2.add_argument("--modelo", default=MODELO_VOZ_POR_DEFECTO, help="Modelo de traducción en Ollama")
    p2.add_argument("--modelo-voz", default="large-v3-turbo",
                    help="Carpeta del modelo Whisper en models/whisper/")
    p2.add_argument("--segundos", type=float, default=12.0, help="Duración de la grabación")
    p2.add_argument("--hilos", type=int, default=0, help="Hilos de CPU para Whisper (0 = automático)")
    p2.add_argument("--dispositivo", type=int, default=None, help="Índice del micrófono")
    p2.set_defaults(funcion=voz)

    args = parser.parse_args()
    try:
        return args.funcion(args)
    except traductor.ErrorOllama as error:
        print(f"\nError: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
