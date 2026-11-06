"""Configuración del programa: valores por defecto + archivo opcional config.local.json.

El archivo `config.local.json` (en la carpeta del proyecto) es tuyo: no se versiona
(el .gitignore ignora `config.local.*`). Solo hay que poner lo que quieras cambiar;
lo demás toma el valor por defecto. Ver `config.ejemplo.json` y fases/03-atajo/README.md.

Cualquier clave desconocida o valor inválido se rechaza con un mensaje claro, para que
una errata (por ejemplo "atjos") no se ignore en silencio.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from dictado import teclas

RAIZ = Path(__file__).resolve().parent.parent
RUTA_LOCAL = RAIZ / "config.local.json"
SENTIDOS_VALIDOS = ("es-en", "en-es")

DEFECTO: dict = {
    # Mantén la tecla -> hablas en el primer idioma -> se obtiene el segundo.
    # Teclas modificadoras de la derecha: casi ninguna aplicación las usa por sí solas.
    "atajos": {"es-en": "rctrl", "en-es": "rshift"},
    "modelo_traduccion": "translategemma:4b",
    "modelo_voz": "large-v3-turbo",
    "hilos_cpu": 0,                    # 0 = automático
    "dispositivo_audio": None,         # None = micrófono por defecto de Windows
    "segundos_minimos": 0.4,           # pulsaciones más cortas se ignoran (accidentes)
    "segundos_maximos": 60.0,          # tope de grabación (protege la memoria)
    "mantener_modelo": "30m",          # cuánto tiempo deja Ollama el modelo en RAM tras usarlo
    "sonidos": True,                   # pitido al empezar y al terminar de grabar
}


def _validar(cfg: dict) -> None:
    atajos = cfg["atajos"]
    if not isinstance(atajos, dict) or not atajos:
        raise ValueError("'atajos' debe ser un diccionario con al menos un atajo")
    desconocidos = set(atajos) - set(SENTIDOS_VALIDOS)
    if desconocidos:
        raise ValueError(f"Sentidos no válidos en 'atajos': {sorted(desconocidos)}. Usa {SENTIDOS_VALIDOS}")
    teclas.validar_atajos({sentido: teclas.parsear_atajo(t) for sentido, t in atajos.items()})

    for clave in ("modelo_traduccion", "modelo_voz"):
        if not isinstance(cfg[clave], str) or not cfg[clave].strip():
            raise ValueError(f"'{clave}' debe ser un texto no vacío")
    if not isinstance(cfg["hilos_cpu"], int) or isinstance(cfg["hilos_cpu"], bool) or cfg["hilos_cpu"] < 0:
        raise ValueError("'hilos_cpu' debe ser un entero >= 0")
    dispositivo = cfg["dispositivo_audio"]
    if dispositivo is not None and (not isinstance(dispositivo, int) or isinstance(dispositivo, bool)):
        raise ValueError("'dispositivo_audio' debe ser null o el número del micrófono")
    minimo, maximo = cfg["segundos_minimos"], cfg["segundos_maximos"]
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (minimo, maximo)):
        raise ValueError("'segundos_minimos' y 'segundos_maximos' deben ser números")
    if not (0.1 <= minimo < maximo <= 300):
        raise ValueError("Se exige 0.1 <= segundos_minimos < segundos_maximos <= 300")
    if not isinstance(cfg["mantener_modelo"], str) or not re.fullmatch(r"\d+[smh]", cfg["mantener_modelo"]):
        raise ValueError("'mantener_modelo' debe tener la forma '30m', '1h' o '90s'")
    if not isinstance(cfg["sonidos"], bool):
        raise ValueError("'sonidos' debe ser true o false")


def cargar(ruta: Path | None = None) -> dict:
    """Devuelve la configuración efectiva (defecto + archivo local), ya validada."""
    cfg = copy.deepcopy(DEFECTO)
    ruta = ruta or RUTA_LOCAL
    if ruta.exists():
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8-sig"))  # utf-8-sig: tolera el BOM del Bloc de notas
        except json.JSONDecodeError as error:
            raise ValueError(f"{ruta.name} no es un JSON válido (línea {error.lineno}, columna {error.colno})") from None
        if not isinstance(datos, dict):
            raise ValueError(f"{ruta.name} debe contener un objeto JSON (datos entre llaves)")
        extraños = set(datos) - set(DEFECTO)
        if extraños:
            raise ValueError(f"Claves desconocidas en {ruta.name}: {sorted(extraños)}. Válidas: {sorted(DEFECTO)}")
        cfg.update(datos)   # 'atajos' se reemplaza entero: así puedes dejar solo un sentido
    _validar(cfg)
    return cfg
