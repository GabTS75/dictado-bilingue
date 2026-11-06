"""Comprueba si el equipo cumple los requisitos de docs/REQUISITOS.md.

Uso:
    python -m dictado.comprobar_equipo

No envía nada a ninguna parte: solo lee datos del propio equipo.
"""

from __future__ import annotations

import ctypes
import os
import platform
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Umbrales (deben coincidir con docs/REQUISITOS.md). Son provisionales.
RAM_MINIMA_GB, RAM_RECOMENDADA_GB = 16, 32
NUCLEOS_MINIMOS, NUCLEOS_RECOMENDADOS = 4, 8
DISCO_MINIMO_GB, DISCO_RECOMENDADO_GB = 15, 25

OK, AVISO, FALLO = "OK   ", "AVISO", "FALLO"


def ram_total_gb() -> float | None:
    """Memoria RAM física total, en GB (None si no se puede determinar)."""
    try:
        if platform.system() == "Windows":
            class MemoriaEstado(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            estado = MemoriaEstado()
            estado.dwLength = ctypes.sizeof(MemoriaEstado)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado))
            return estado.ullTotalPhys / 1024**3
        # Linux / macOS (solo para pruebas de desarrollo)
        paginas = os.sysconf("SC_PHYS_PAGES")
        tam_pagina = os.sysconf("SC_PAGE_SIZE")
        return paginas * tam_pagina / 1024**3
    except (OSError, ValueError, AttributeError):
        return None


def evaluar(valor, minimo, recomendado) -> str:
    if valor is None:
        return AVISO
    if valor < minimo:
        return FALLO
    if valor < recomendado:
        return AVISO
    return OK


def comprobar_microfono() -> tuple[str, str]:
    try:
        import sounddevice as sd  # importación tardía: puede no estar instalado aún
    except (ImportError, OSError) as error:
        return AVISO, f"sounddevice no disponible todavía ({error.__class__.__name__})"
    try:
        entradas = [d for d in sd.query_devices() if d["max_input_channels"] > 0]
    except Exception as error:  # noqa: BLE001 - cualquier fallo de audio se informa
        return AVISO, f"no se pudieron listar dispositivos ({error.__class__.__name__})"
    if not entradas:
        return FALLO, "no se detecta ningún micrófono"
    return OK, f"{len(entradas)} dispositivo(s) de entrada detectado(s)"


def main() -> int:
    filas: list[tuple[str, str, str]] = []

    # Sistema operativo
    sistema = platform.system()
    version = f"{sistema} {platform.release()} ({platform.machine()})"
    estado_so = OK if sistema == "Windows" and platform.machine().lower() in ("amd64", "x86_64") else AVISO
    filas.append((estado_so, "Sistema operativo", version + ("" if estado_so == OK else " - pensado para Windows x64")))

    # Python
    v = sys.version_info
    if (v.major, v.minor) == (3, 12):
        estado_py = OK
    elif (v.major, v.minor) < (3, 12) or (v.major, v.minor) >= (3, 14):
        estado_py = FALLO
    else:
        estado_py = AVISO
    filas.append((estado_py, "Python", f"{v.major}.{v.minor}.{v.micro} (recomendado 3.12)"))

    # RAM
    ram = ram_total_gb()
    filas.append((
        evaluar(ram, RAM_MINIMA_GB, RAM_RECOMENDADA_GB),
        "Memoria RAM",
        f"{ram:.1f} GB (mín. {RAM_MINIMA_GB}, recomendado {RAM_RECOMENDADA_GB})" if ram else "no se pudo leer",
    ))

    # CPU
    nucleos = os.cpu_count()
    filas.append((
        evaluar(nucleos, NUCLEOS_MINIMOS, NUCLEOS_RECOMENDADOS),
        "Procesador",
        f"{nucleos} hilos lógicos (mín. {NUCLEOS_MINIMOS}, recomendado {NUCLEOS_RECOMENDADOS})",
    ))

    # Disco libre en la unidad del proyecto
    libre = shutil.disk_usage(RAIZ).free / 1024**3
    filas.append((
        evaluar(libre, DISCO_MINIMO_GB, DISCO_RECOMENDADO_GB),
        "Disco libre",
        f"{libre:.1f} GB (mín. {DISCO_MINIMO_GB}, recomendado {DISCO_RECOMENDADO_GB})",
    ))

    # Micrófono
    estado_mic, detalle_mic = comprobar_microfono()
    filas.append((estado_mic, "Micrófono", detalle_mic))

    print("Comprobación del equipo\n" + "-" * 60)
    for estado, nombre, detalle in filas:
        print(f"[{estado}] {nombre:<18} {detalle}")
    print("-" * 60)

    hay_fallos = any(e == FALLO for e, _, _ in filas)
    hay_avisos = any(e == AVISO for e, _, _ in filas)
    if hay_fallos:
        print("Resultado: el equipo NO cumple los requisitos mínimos (ver FALLO).")
        return 1
    if hay_avisos:
        print("Resultado: cumple lo mínimo; revisa los AVISO para un rendimiento óptimo.")
        return 0
    print("Resultado: el equipo cumple los requisitos recomendados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
