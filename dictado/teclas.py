"""Atajos de "mantener para hablar" leyendo SOLO las teclas del atajo.

Analogía: un espía de teclado (keylogger) es como un portero que apunta todo lo
que dice cada visitante. Aquí hacemos lo contrario: cada pocos milisegundos
preguntamos a Windows únicamente "¿está pulsada la tecla X?" para las 1-3 teclas de
tu atajo. El resto del teclado no lo consultamos nunca, así que este programa no
tiene forma de saber qué escribes.

Cómo se hace: función GetAsyncKeyState de user32.dll, a través de ctypes (incluido
en Python). No se instalan ganchos (hooks) ni librerías de terceros.

Limitaciones que conviene conocer:
  * Solo Windows.
  * No "se come" la pulsación: la aplicación activa también recibe la tecla. Por eso
    los atajos por defecto son teclas modificadoras que casi ninguna aplicación usa
    por sí solas (Ctrl derecho, Mayús derecho).
  * En teclados con AltGr (como el español) Ctrl+Alt equivale a AltGr, que se usa
    para escribir @, #, € ... Por eso se rechazan esas combinaciones.

Probar una combinación sin lanzar nada más:
    python -m dictado.teclas --probar rctrl
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from typing import Callable

# Códigos de tecla virtual de Windows (VK_*). Solo las que tiene sentido usar.
_TECLAS_FIJAS: dict[str, int] = {
    "ctrl": 0x11, "lctrl": 0xA2, "rctrl": 0xA3,
    "alt": 0x12, "lalt": 0xA4, "ralt": 0xA5,
    "shift": 0x10, "lshift": 0xA0, "rshift": 0xA1,
    "win": 0x5B, "lwin": 0x5B, "rwin": 0x5C,
    "space": 0x20, "tab": 0x09, "enter": 0x0D, "esc": 0x1B, "backspace": 0x08,
    "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28,
    "pause": 0x13, "scrolllock": 0x91,
}
_CTRL = {"ctrl", "lctrl", "rctrl"}
_ALT = {"alt", "lalt", "ralt"}


def _codigo_de_tecla(nombre: str) -> int:
    """Convierte 'f9', 'a', '5', 'num3' o un nombre de la tabla en su código VK."""
    if nombre in _TECLAS_FIJAS:
        return _TECLAS_FIJAS[nombre]
    if len(nombre) == 1 and "a" <= nombre <= "z":
        return ord(nombre.upper())            # VK de las letras = su código ASCII en mayúscula
    if len(nombre) == 1 and "0" <= nombre <= "9":
        return ord(nombre)                    # idem para los dígitos de la fila superior
    if nombre.startswith("f") and nombre[1:].isdigit() and 1 <= int(nombre[1:]) <= 24:
        return 0x70 + int(nombre[1:]) - 1     # F1 = 0x70
    if nombre.startswith("num") and nombre[3:].isdigit() and len(nombre) == 4:
        return 0x60 + int(nombre[3:])         # teclado numérico: num0..num9
    raise ValueError(
        f"Tecla desconocida: '{nombre}'. Usa nombres como rctrl, rshift, f9, space, a, 5, num3..."
    )


@dataclass(frozen=True)
class Atajo:
    texto: str                 # forma normalizada, p. ej. "rctrl+space"
    nombres: tuple[str, ...]   # ("rctrl", "space")
    teclas: tuple[int, ...]    # códigos VK correspondientes


def parsear_atajo(texto: str) -> Atajo:
    """Convierte 'RCtrl + Space' en un Atajo. Lanza ValueError si no es válido."""
    nombres = tuple(parte.strip().lower() for parte in str(texto).split("+"))
    if not nombres or any(not n for n in nombres):
        raise ValueError(f"Atajo vacío o mal escrito: '{texto}'")
    if len(set(nombres)) != len(nombres):
        raise ValueError(f"Hay teclas repetidas en el atajo: '{texto}'")
    conjunto = set(nombres)
    if "ralt" in conjunto or (conjunto & _CTRL and conjunto & _ALT):
        raise ValueError(
            f"El atajo '{texto}' se activaría al escribir con AltGr (@, #, €...) en teclados "
            "como el español, donde Ctrl+Alt equivale a AltGr. Elige otra combinación."
        )
    return Atajo(texto="+".join(nombres), nombres=nombres,
                 teclas=tuple(_codigo_de_tecla(n) for n in nombres))


def validar_atajos(atajos: dict[str, Atajo]) -> None:
    """Rechaza atajos iguales o contenidos en otros (se activarían a la vez)."""
    nombres = list(atajos)
    for i, a in enumerate(nombres):
        for b in nombres[i + 1:]:
            ta, tb = set(atajos[a].teclas), set(atajos[b].teclas)
            if ta <= tb or tb <= ta:
                raise ValueError(
                    f"Los atajos de '{a}' ({atajos[a].texto}) y '{b}' ({atajos[b].texto}) se "
                    "solapan: uno contiene al otro. Usa teclas distintas."
                )


def teclas_vigiladas(atajos: dict[str, Atajo]) -> list[str]:
    """Lista exacta de teclas que el programa consulta. Ninguna más."""
    vistas: list[str] = []
    for atajo in atajos.values():
        for nombre in atajo.nombres:
            if nombre not in vistas:
                vistas.append(nombre)
    return vistas


def crear_lector_windows() -> Callable[[int], bool]:
    """Devuelve una función que dice si una tecla (código VK) está pulsada ahora mismo."""
    if sys.platform != "win32":
        raise RuntimeError("La lectura de atajos solo está implementada para Windows.")
    import ctypes

    user32 = ctypes.windll.user32
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short

    def leer(codigo_vk: int) -> bool:
        # El bit más alto del resultado vale 1 si la tecla está pulsada en este instante.
        return bool(user32.GetAsyncKeyState(codigo_vk) & 0x8000)

    return leer


class Detector:
    """Convierte el estado de las teclas en eventos ("inicio"/"fin", nombre_del_atajo).

    Se llama a `sondear()` unas 50 veces por segundo. Es una pequeña máquina de estados:
    ninguna tecla -> atajo pulsado ("inicio") -> atajo soltado ("fin").
    """

    def __init__(self, atajos: dict[str, Atajo], leer_tecla: Callable[[int], bool]):
        self._atajos = atajos
        self._leer = leer_tecla
        self.activo: str | None = None
        self._esperando_soltar: set[str] = set()   # atajos que no deben arrancar hasta soltarse

    def _pulsado(self, nombre: str) -> bool:
        return all(self._leer(vk) for vk in self._atajos[nombre].teclas)

    def sondear(self) -> tuple[str, str] | None:
        if self.activo is not None:
            # Otro atajo pulsado durante la sesión (por accidente) no arrancará al terminar.
            self._esperando_soltar |= {n for n in self._atajos if n != self.activo and self._pulsado(n)}
            if not self._pulsado(self.activo):
                nombre, self.activo = self.activo, None
                return ("fin", nombre)
            return None
        for nombre in self._atajos:
            pulsado = self._pulsado(nombre)
            if nombre in self._esperando_soltar:
                if not pulsado:
                    self._esperando_soltar.discard(nombre)
            elif pulsado:
                self.activo = nombre
                # Si otro atajo está pulsado a la vez, no arrancará al soltar este.
                self._esperando_soltar |= {n for n in self._atajos if n != nombre and self._pulsado(n)}
                return ("inicio", nombre)
        return None

    def forzar_fin(self) -> tuple[str, str] | None:
        """Termina la sesión aunque la tecla siga pulsada; no arranca otra hasta soltarla."""
        if self.activo is None:
            return None
        nombre, self.activo = self.activo, None
        self._esperando_soltar.add(nombre)
        return ("fin", nombre)

    def ignorar_hasta_soltar(self) -> None:
        """Lo que esté pulsado ahora no cuenta como inicio nuevo (se usa tras procesar)."""
        self._esperando_soltar = {n for n in self._atajos if self._pulsado(n)}


def _probar(texto: str, segundos: float) -> int:
    """Muestra en vivo si el atajo está pulsado. Consulta SOLO las teclas de ese atajo."""
    atajo = parsear_atajo(texto)
    lector = crear_lector_windows()
    print(f"Teclas consultadas (y solo estas): {', '.join(atajo.nombres)}")
    print(f"Mantén y suelta '{atajo.texto}' durante {segundos:g} s. Ctrl+C para salir.\n")
    anterior = None
    fin = time.monotonic() + segundos
    try:
        while time.monotonic() < fin:
            ahora = all(lector(vk) for vk in atajo.teclas)
            if ahora != anterior:
                print("PULSADO" if ahora else "suelto")
                anterior = ahora
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Probar un atajo de teclado.")
    parser.add_argument("--probar", metavar="ATAJO", required=True, help="p. ej. rctrl o rshift+space")
    parser.add_argument("--segundos", type=float, default=15.0)
    argumentos = parser.parse_args()
    try:
        raise SystemExit(_probar(argumentos.probar, argumentos.segundos))
    except (ValueError, RuntimeError) as error:
        print(f"Error: {error}")
        raise SystemExit(1)
