"""Capa de privacidad: bloquea cualquier conexión de red que no sea local.

Idea (analogía): es como poner un tapón en la salida de internet del programa.
Solo dejamos pasar el tráfico "de la casa para la casa" (localhost), que más
adelante necesitará el servidor local de traducción.

IMPORTANTE - límites honestos:
  * Esto es una DEFENSA EN PROFUNDIDAD, no una garantía absoluta. Un código
    nativo (C/Rust) dentro de una librería podría saltarse este bloqueo.
  * La verificación real es externa: cortafuegos de Windows, modo avión o
    revisar conexiones con Get-NetTCPConnection (ver docs/PRIVACIDAD.md).

Uso:
    from dictado.privacidad import bloquear_red
    bloquear_red()          # llamar ANTES de importar librerías de IA

Autotest:
    python -m dictado.privacidad
"""

from __future__ import annotations

import ipaddress
import os
import socket

# Variables de entorno que impiden descargas/telemetría de las librerías.
_VARIABLES_OFFLINE = {
    "HF_HUB_OFFLINE": "1",             # huggingface_hub: nunca descargar
    "TRANSFORMERS_OFFLINE": "1",       # transformers: nunca descargar
    "HF_HUB_DISABLE_TELEMETRY": "1",   # sin telemetría de Hugging Face
    "DO_NOT_TRACK": "1",               # convención general de no rastreo
}


class RedBloqueadaError(OSError):
    """Se intentó una conexión a un destino que no es local."""


def _host_es_local(host) -> bool:
    """Devuelve True si `host` es el propio equipo (localhost / 127.x / ::1)."""
    if host is None or host == "":
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", errors="ignore")
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        # Es un nombre de dominio (necesitaría DNS): no es local.
        return False


def _direccion_es_local(direccion) -> bool:
    """Evalúa la dirección que recibe socket.connect()."""
    if not isinstance(direccion, tuple):
        # Sockets de archivo/tubería (AF_UNIX): no salen a la red.
        return True
    return _host_es_local(direccion[0])


_bloqueo_activo = False


def bloquear_red() -> None:
    """Activa el bloqueo de red no local. Es idempotente (se puede llamar varias veces)."""
    global _bloqueo_activo
    if _bloqueo_activo:
        return

    # 1) Variables de entorno: deben fijarse antes de importar las librerías.
    for nombre, valor in _VARIABLES_OFFLINE.items():
        os.environ[nombre] = valor

    # 2) Interceptar connect / connect_ex / getaddrinfo.
    conectar_original = socket.socket.connect
    conectar_ex_original = socket.socket.connect_ex
    resolver_original = socket.getaddrinfo

    def conectar(self, direccion):
        if not _direccion_es_local(direccion):
            raise RedBloqueadaError(f"Conexión bloqueada (no es local): {direccion[0]!r}")
        return conectar_original(self, direccion)

    def conectar_ex(self, direccion):
        if not _direccion_es_local(direccion):
            raise RedBloqueadaError(f"Conexión bloqueada (no es local): {direccion[0]!r}")
        return conectar_ex_original(self, direccion)

    def resolver(host, *args, **kwargs):
        if not _host_es_local(host):
            raise RedBloqueadaError(f"Resolución DNS bloqueada: {host!r}")
        return resolver_original(host, *args, **kwargs)

    socket.socket.connect = conectar
    socket.socket.connect_ex = conectar_ex
    socket.getaddrinfo = resolver
    _bloqueo_activo = True


def _autotest() -> int:
    """Comprueba que el bloqueo funciona. Devuelve 0 si todo es correcto."""
    bloquear_red()
    fallos = 0

    # a) Una IP externa (rango de documentación 192.0.2.0/24) debe bloquearse.
    try:
        socket.create_connection(("192.0.2.1", 80), timeout=1)
        print("FALLO: se permitió una conexión externa por IP")
        fallos += 1
    except RedBloqueadaError:
        print("OK: conexión externa por IP bloqueada")
    except OSError as error:
        print(f"FALLO: error inesperado ({error})")
        fallos += 1

    # b) Un nombre de dominio debe bloquearse antes de consultar el DNS.
    try:
        socket.getaddrinfo("example.com", 443)
        print("FALLO: se permitió resolver un dominio externo")
        fallos += 1
    except RedBloqueadaError:
        print("OK: resolución DNS externa bloqueada")

    # c) Localhost debe seguir permitido (aquí fallará por 'conexión rechazada',
    #    y eso es lo correcto: significa que NO lo bloqueó nuestro filtro).
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=1)
    except RedBloqueadaError:
        print("FALLO: localhost no debería estar bloqueado")
        fallos += 1
    except OSError:
        print("OK: localhost no está bloqueado por el filtro")

    # d) Variables de entorno activas.
    if os.environ.get("HF_HUB_OFFLINE") == "1":
        print("OK: HF_HUB_OFFLINE activo")
    else:
        print("FALLO: HF_HUB_OFFLINE no está activo")
        fallos += 1

    print("\nRESULTADO:", "OK" if fallos == 0 else f"{fallos} fallo(s)")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_autotest())
