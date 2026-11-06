"""Descarga los modelos de voz. ES EL ÚNICO SCRIPT DEL PROYECTO QUE USA INTERNET.

Qué hace:
  1. Descarga el modelo de Whisper a la carpeta `models/whisper/<modelo>/`
     del proyecto (no a la caché global del sistema).
  2. Calcula la huella SHA-256 de cada archivo y la guarda en SHA256SUMS.txt
     para que puedas auditar que los archivos no cambian después.

Uso:
    python -m dictado.descargar_modelos
    python -m dictado.descargar_modelos --modelo medium     (alternativa más ligera)

Después de descargar, el resto del programa funciona sin red.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MODELOS_DIR = RAIZ / "models" / "whisper"
MODELO_POR_DEFECTO = "large-v3-turbo"


def huella_sha256(ruta: Path) -> str:
    """SHA-256 de un archivo, leído por bloques (no carga el archivo entero en RAM)."""
    resumen = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            resumen.update(bloque)
    return resumen.hexdigest()


def escribir_huellas(carpeta: Path) -> Path:
    destino = carpeta / "SHA256SUMS.txt"
    lineas = []
    for archivo in sorted(carpeta.rglob("*")):
        if archivo.is_file() and archivo.name != "SHA256SUMS.txt":
            lineas.append(f"{huella_sha256(archivo)}  {archivo.relative_to(carpeta).as_posix()}")
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino


def main() -> int:
    parser = argparse.ArgumentParser(description="Descarga el modelo de voz (usa internet).")
    parser.add_argument("--modelo", default=MODELO_POR_DEFECTO,
                        help="Nombre del modelo de faster-whisper (por defecto: large-v3-turbo)")
    parser.add_argument("--si", action="store_true", help="No pedir confirmación")
    args = parser.parse_args()

    print("AVISO: este script se conecta a internet para descargar el modelo")
    print(f"       '{args.modelo}' (varios GB). Es el único paso que lo necesita.")
    if not args.si and input("¿Continuar? [s/N] ").strip().lower() not in ("s", "si", "sí", "y", "yes"):
        print("Cancelado.")
        return 1

    # Importación tardía: así el script falla con un mensaje claro si falta la librería.
    from faster_whisper.utils import download_model

    destino = MODELOS_DIR / args.modelo
    destino.mkdir(parents=True, exist_ok=True)
    print("Descargando... (puede tardar según tu conexión)")
    download_model(args.modelo, output_dir=str(destino))

    sumas = escribir_huellas(destino)
    print(f"\nModelo guardado en: {destino}")
    print(f"Huellas SHA-256 en: {sumas}")
    print("Ya puedes desconectarte de internet y ejecutar fase1_transcribir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
