"""Fase 3: mantén una tecla, habla, suéltala y obtén el texto traducido en pantalla.

Todavía NO escribe en otras aplicaciones (eso es la Fase 4): muestra original y
traducción en esta ventana. Sirve para probar el flujo completo con atajo de teclado.

    Mantén la tecla del atajo  ->  se abre el micrófono y se graba (solo en RAM)
    Suelta                     ->  se cierra el micrófono -> Whisper -> traducción -> pantalla

Privacidad:
  * Red bloqueada salvo 127.0.0.1 antes de importar nada más.
  * Solo se consultan las teclas del atajo (ver dictado/teclas.py); se listan al arrancar.
  * El micrófono SOLO está abierto mientras mantienes la tecla.
  * El audio vive en RAM y se pone a cero al terminar; nada se guarda en disco.

Uso:
    python -m dictado.fase3_atajo
    python -m dictado.fase3_atajo --mostrar-config      (audita qué teclas se vigilan y sale)
"""

# --- PRIVACIDAD PRIMERO ---------------------------------------------------------
from dictado.privacidad import bloquear_red

bloquear_red()

# --- Resto de importaciones -----------------------------------------------------
import argparse  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Callable  # noqa: E402

from dictado import config, teclas, traductor  # noqa: E402

FRECUENCIA = 16_000          # Whisper trabaja a 16 kHz, mono
INTERVALO_S = 0.02           # se consulta el atajo 50 veces por segundo
SENTIDOS = {"es-en": ("es", "en"), "en-es": ("en", "es")}


class Grabadora:
    """Graba el micrófono SOLO entre empezar() y parar(). El audio vive en la RAM."""

    def __init__(self, dispositivo: int | None, segundos_maximos: float):
        self._dispositivo = dispositivo
        self._maximo = int(segundos_maximos * FRECUENCIA)
        self._trozos: list = []
        self._muestras = 0
        self._flujo = None

    def empezar(self) -> None:
        import sounddevice as sd  # importación tardía: solo hace falta al grabar

        self._trozos, self._muestras = [], 0

        def al_llegar_audio(datos, frames, tiempo, estado):
            if self._muestras < self._maximo:               # tope: protege la memoria
                self._trozos.append(datos[:, 0].copy())
                self._muestras += len(datos)

        self._flujo = sd.InputStream(samplerate=FRECUENCIA, channels=1, dtype="float32",
                                     device=self._dispositivo, callback=al_llegar_audio)
        self._flujo.start()

    def parar(self):
        import numpy as np

        flujo, self._flujo = self._flujo, None
        if flujo is not None:
            flujo.stop()
            flujo.close()                                    # el micrófono queda cerrado
        audio = np.concatenate(self._trozos) if self._trozos else np.zeros(0, dtype="float32")
        for trozo in self._trozos:
            trozo[:] = 0                                     # se borran las copias intermedias
        self._trozos = []
        return audio


def crear_avisador(activo: bool) -> Callable[[str], None]:
    """Pitido corto al empezar (agudo) y al terminar (grave). Solo Windows (winsound)."""
    if not activo:
        return lambda evento: None
    try:
        import winsound
    except ImportError:
        return lambda evento: None

    def avisar(evento: str) -> None:
        winsound.Beep(880 if evento == "inicio" else 440, 80)

    return avisar


class Asistente:
    """Une las piezas: detector de atajo + grabadora + transcripción + traducción.

    Todas las dependencias se inyectan, así la lógica se puede probar sin micrófono,
    sin Whisper y sin Ollama (ver las pruebas descritas en fases/03-atajo/README.md).
    """

    def __init__(self, cfg: dict, detector: teclas.Detector, grabadora, transcribir: Callable,
                 traducir: Callable, avisar: Callable[[str], None],
                 mostrar: Callable[[str], None] = print, reloj: Callable[[], float] = time.monotonic):
        self.cfg, self.detector, self.grabadora = cfg, detector, grabadora
        self._transcribir, self._traducir, self._avisar = transcribir, traducir, avisar
        self._mostrar, self._reloj = mostrar, reloj
        self._t_inicio: float | None = None

    @property
    def grabando(self) -> bool:
        return self._t_inicio is not None

    def paso(self) -> None:
        """Una vuelta del bucle: consulta el atajo y reacciona."""
        evento = self.detector.sondear()
        if evento is None and self.grabando and self._reloj() - self._t_inicio >= self.cfg["segundos_maximos"]:
            self._mostrar("(límite de duración alcanzado: se procesa lo grabado)")
            evento = self.detector.forzar_fin()
        if evento is None:
            return
        tipo, sentido = evento
        if tipo == "inicio":
            self._iniciar(sentido)
        else:
            self._terminar(sentido)

    def _iniciar(self, sentido: str) -> None:
        origen, destino = SENTIDOS[sentido]
        self._avisar("inicio")                  # el pitido suena ANTES de abrir el micrófono
        self.grabadora.empezar()
        self._t_inicio = self._reloj()
        self._mostrar(f"● Grabando [{origen.upper()}→{destino.upper()}]... suelta la tecla para terminar")

    def _terminar(self, sentido: str) -> None:
        audio = self.grabadora.parar()
        self._avisar("fin")
        self._t_inicio = None
        try:
            self._procesar(sentido, audio)
        finally:
            audio[:] = 0                        # el audio ya no hace falta: se pone a cero
            self.detector.ignorar_hasta_soltar()  # lo pulsado durante el proceso no arranca otra grabación

    def _procesar(self, sentido: str, audio) -> None:
        origen, destino = SENTIDOS[sentido]
        duracion = len(audio) / FRECUENCIA
        if duracion < self.cfg["segundos_minimos"]:
            self._mostrar("(pulsación muy corta: ignorada)")
            return

        self._mostrar(f"Procesando {duracion:.1f} s de audio...")
        inicio = time.perf_counter()
        texto = self._transcribir(audio, origen)
        t_transcripcion = time.perf_counter() - inicio
        if not texto:
            self._mostrar("(no se detectó voz)")
            return

        try:
            resultado = self._traducir(texto, origen, destino)
        except traductor.ErrorOllama as error:
            self._mostrar(f"Error de traducción: {error}")
            self._mostrar(f"--- {origen.upper()} (transcripción, sin traducir) ---\n{texto}")
            return

        self._mostrar(f"\n--- {origen.upper()} (lo que dijiste) ---\n{texto}")
        self._mostrar(f"--- {destino.upper()} (traducción) ---\n{resultado.texto}")
        self._mostrar(
            f"[transcripción {t_transcripcion:.1f} s · traducción {resultado.segundos_traduccion:.1f} s "
            f"· espera total {t_transcripcion + resultado.segundos_traduccion:.1f} s]\n"
        )

    def ejecutar(self, dormir: Callable[[float], None] = time.sleep) -> None:
        try:
            while True:
                self.paso()
                dormir(INTERVALO_S)
        finally:
            if self.grabando:                   # Ctrl+C a mitad de grabación: cerrar el micrófono
                audio = self.grabadora.parar()
                audio[:] = 0
                self._t_inicio = None


def _mostrar_config(cfg: dict, atajos: dict[str, teclas.Atajo]) -> None:
    print("Configuración efectiva:")
    print(json.dumps(cfg, indent=2, ensure_ascii=False))
    print(f"\nTeclas que el programa consulta (y SOLO estas): {', '.join(teclas.teclas_vigiladas(atajos))}")
    for sentido, atajo in atajos.items():
        origen, destino = SENTIDOS[sentido]
        print(f"  mantener {atajo.texto.upper():<14} -> hablas {origen.upper()}, se obtiene {destino.upper()}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fase 3: atajo de teclado 'mantener para hablar'.")
    parser.add_argument("--config", help="Ruta de un archivo de configuración (por defecto config.local.json)")
    parser.add_argument("--mostrar-config", action="store_true", help="Mostrar la configuración y las teclas vigiladas, y salir")
    args = parser.parse_args()

    try:
        cfg = config.cargar(Path(args.config) if args.config else None)
    except ValueError as error:
        print(f"Error de configuración: {error}")
        return 1
    atajos = {sentido: teclas.parsear_atajo(t) for sentido, t in cfg["atajos"].items()}

    if args.mostrar_config:
        _mostrar_config(cfg, atajos)
        return 0

    try:
        lector = teclas.crear_lector_windows()
    except RuntimeError as error:
        print(f"Error: {error}")
        return 1

    # Comprobaciones previas: mejor fallar ahora que después de cargar Whisper.
    try:
        faltan = traductor.modelos_que_faltan([cfg["modelo_traduccion"]])
    except traductor.ErrorOllama as error:
        print(f"Error: {error}")
        return 2
    if faltan:
        print(f"Falta el modelo en Ollama:  ollama pull {faltan[0]}")
        return 1

    from dictado import fase1_transcribir as f1  # reutiliza la Fase 1

    print("Teclas que el programa consulta (y SOLO estas):", ", ".join(teclas.teclas_vigiladas(atajos)))
    print(f"Cargando Whisper '{cfg['modelo_voz']}'...")
    modelo_voz = f1.cargar_modelo(cfg["modelo_voz"], cfg["hilos_cpu"])

    print(f"Preparando la traducción ({cfg['modelo_traduccion']})...")
    try:   # una traducción mínima carga el modelo en RAM: la primera de verdad no espera
        traductor.traducir("Hello.", "en", "es", cfg["modelo_traduccion"], cfg["mantener_modelo"])
    except traductor.ErrorOllama as error:
        print(f"Error: {error}")
        return 2

    asistente = Asistente(
        cfg=cfg,
        detector=teclas.Detector(atajos, lector),
        grabadora=Grabadora(cfg["dispositivo_audio"], cfg["segundos_maximos"]),
        transcribir=lambda audio, idioma: f1.transcribir(modelo_voz, audio, idioma),
        traducir=lambda texto, origen, destino: traductor.traducir(
            texto, origen, destino, cfg["modelo_traduccion"], cfg["mantener_modelo"]),
        avisar=crear_avisador(cfg["sonidos"]),
    )

    print("\nListo. Mantén el atajo, habla y suéltalo. Ctrl+C para salir.")
    for sentido, atajo in atajos.items():
        origen, destino = SENTIDOS[sentido]
        print(f"  mantener {atajo.texto.upper():<14} -> hablas {origen.upper()}, se obtiene {destino.upper()}")
    print()
    try:
        asistente.ejecutar()
    except KeyboardInterrupt:
        print("\nSaliendo...")
    finally:
        traductor.liberar(cfg["modelo_traduccion"])   # libera la RAM del modelo de traducción
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
