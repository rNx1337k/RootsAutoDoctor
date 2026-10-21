"""Acesso directo por USB (libusb/WinUSB) a interfaces com chip FTDI que não têm porta COM.

Caso típico: os clones "Ross-Tech HEX-USB" (VID 0403, PID FA24). Por dentro têm um FT232R da FTDI,
mas o PID próprio faz com que o driver VCP da FTDI não os reconheça — o Windows mostra-os sem driver
e sem porta COM. Instalando o driver genérico WinUSB (com o Zadig), o chip FTDI fica acessível pelo
libusb e este módulo apresenta-o ao resto do programa como se fosse uma porta série (`FtdiSerial`).

O que este módulo NÃO faz: não fala com nenhum firmware da Ross-Tech nem envia comandos proprietários.
Só usa os pedidos de controlo normais do chip FTDI (velocidade, BREAK, DTR/RTS, latência), os mesmos que
o driver VCP usa. Isto só chega ao carro se o TX/RX do FT232R estiver ligado ao transceptor da linha K
(cabo "dumb", como um KKL). Se houver um microcontrolador entre o FTDI e a ficha OBD, o teste de eco
falha e a interface não pode ser usada assim.

Portas aparecem na lista como "FTDI:<vid>:<pid>:<n.º de série>", por exemplo "FTDI:0403:FA24:RT000001".
Dependências opcionais: pyftdi (+ pyusb) e libusb-package (traz o libusb-1.0.dll).
"""
import logging
import time

from .errors import InterfaceError, KLineError

log = logging.getLogger(__name__)

PREFIX = "FTDI:"
FTDI_VID = 0x0403

# PIDs normais da FTDI: com o driver VCP oficial já aparecem como porta COM.
VCP_PIDS = {0x6001, 0x6010, 0x6011, 0x6014, 0x6015}

# Interfaces conhecidas com chip FTDI e PID próprio (VID 0403).
KNOWN_DIRECT = {
    (FTDI_VID, 0xFA24): "Ross-Tech HEX-USB (clone)",
}

# bcdDevice → chip (valores fixos do silício FTDI)
CHIPS = {0x0200: "FT232AM", 0x0400: "FT232BM", 0x0500: "FT2232C", 0x0600: "FT232R",
         0x0700: "FT2232H", 0x0800: "FT4232H", 0x0900: "FT232H", 0x1000: "FT-X"}


def chip_name(bcd):
    return CHIPS.get(bcd, f"FTDI (bcdDevice {bcd:04X})" if bcd is not None else "FTDI")


def is_ftdi_port(port):
    return bool(port) and port.startswith(PREFIX)


def make_port(vid, pid, serial):
    return f"{PREFIX}{vid:04X}:{pid:04X}:{serial or ''}"


def parse_port(port):
    """'FTDI:0403:FA24:RT000001' → (0x0403, 0xFA24, 'RT000001' | None)."""
    try:
        _, vid, pid, serial = port.split(":", 3)
        return int(vid, 16), int(pid, 16), (serial or None)
    except ValueError:
        raise KLineError(f"Porta USB inválida: {port}")


class DependencyMissing(KLineError):
    """pyftdi / pyusb / libusb não estão instalados."""


def _backend():
    """Backend libusb-1.0. Carregar primeiro pelo libusb-package faz o pyusb guardar a DLL em cache,
    e o pyftdi passa a encontrá-la sem ser preciso pôr o libusb-1.0.dll no PATH."""
    try:
        import usb.backend.libusb1  # noqa: F401
    except ImportError:
        raise DependencyMissing("Falta o pyusb. Instale com: pip install pyftdi libusb-package")
    be = None
    try:
        import libusb_package
        be = libusb_package.get_libusb1_backend()
    except ImportError:
        pass
    if be is None:
        import usb.backend.libusb1
        be = usb.backend.libusb1.get_backend()
    if be is None:
        raise DependencyMissing("libusb-1.0 não encontrado. Instale com: pip install libusb-package")
    return be


def list_devices():
    """Interfaces FTDI acessíveis por libusb (driver WinUSB/libusbK instalado):
    [{vid, pid, serial, product, chip, port, known}]. Vazio se faltarem dependências."""
    try:
        be = _backend()
        import usb.core
        import usb.util
    except (DependencyMissing, ImportError):
        return []
    out = []
    try:
        devs = list(usb.core.find(find_all=True, idVendor=FTDI_VID, backend=be))
    except Exception:
        log.warning("libusb: não foi possível enumerar os dispositivos USB", exc_info=True)
        return []
    for d in devs:
        # Inclui também FTDI normais (PID 6001...) se tiverem WinUSB em vez do driver VCP.
        try:
            serial = usb.util.get_string(d, d.iSerialNumber) if d.iSerialNumber else None
            product = usb.util.get_string(d, d.iProduct) if d.iProduct else ""
        except Exception:
            continue                       # sem driver WinUSB: o libusb não o consegue abrir
        finally:
            try:
                usb.util.dispose_resources(d)
            except Exception:
                pass
        out.append({"vid": d.idVendor, "pid": d.idProduct, "serial": serial, "product": product or "",
                    "chip": chip_name(d.bcdDevice), "port": make_port(d.idVendor, d.idProduct, serial),
                    "known": KNOWN_DIRECT.get((d.idVendor, d.idProduct))})
    return out


def list_ports():
    """[(port, descrição)] para a lista de portas."""
    out = []
    for d in list_devices():
        name = d["known"] or d["product"] or "Interface FTDI"
        out.append((d["port"], f"USB directo — {name} [{d['chip']}, VID {d['vid']:04X} PID {d['pid']:04X}"
                               f"{', S/N ' + d['serial'] if d['serial'] else ''}]"))
    return out


def _open_ftdi(vid, pid, serial):
    _backend()
    try:
        from pyftdi.ftdi import Ftdi
    except ImportError:
        raise DependencyMissing("Falta o pyftdi. Instale com: pip install pyftdi libusb-package")
    dev = Ftdi()
    dev.open(vid, pid, serial=serial)
    return dev


class FtdiSerial:
    """Imitação mínima de serial.Serial sobre o pyftdi — só o que o KLine usa
    (baudrate, timeout, break_condition, dtr, rts, read, write, reset_input_buffer, close).
    Todos os erros USB (cabo desligado, driver retirado...) passam a KLineError."""

    LATENCY_MS = 1                         # o driver VCP usa 16 ms por omissão; a linha K quer pouco

    def __init__(self, port, baudrate=10400, timeout=0.5, opener=None):
        self.port = port
        self._vid, self._pid, self._serial = parse_port(port)
        self._opener = opener or _open_ftdi
        self._timeout = timeout
        self._baud = baudrate
        self._break = False
        self.dev = None
        self.open()

    # ---------------------------------------------------------------- abrir/fechar
    def _guard(self, what, fn, *args):
        if self.dev is None:
            raise InterfaceError(f"{self.port}: interface fechada")
        try:
            return fn(*args)
        except KLineError:
            raise
        except Exception as e:
            raise InterfaceError(f"{what}: {e} — o cabo foi desligado?") from e

    def open(self):
        try:
            self.dev = self._opener(self._vid, self._pid, self._serial)
        except KLineError:
            raise
        except Exception as e:
            raise KLineError(_explain_open_error(self.port, e)) from e
        try:
            self.dev.set_line_property(8, 1, "N")
            self.dev.set_flowctrl("")
            self.dev.set_baudrate(self._baud)
            self.dev.set_latency_timer(self.LATENCY_MS)
            self.dev.set_break(False)
            self.dev.purge_buffers()
        except Exception as e:
            self.close()
            raise KLineError(f"Não foi possível configurar o chip FTDI: {e}") from e

    def close(self):
        d, self.dev = self.dev, None
        if d is None:
            return
        try:
            d.set_break(False)
        except Exception:
            pass
        try:
            d.close()
        except Exception:
            log.warning("%s: erro ao fechar", self.port, exc_info=True)

    @property
    def is_open(self):
        return self.dev is not None

    # ---------------------------------------------------------------- propriedades pyserial
    @property
    def baudrate(self):
        return self._baud

    @baudrate.setter
    def baudrate(self, baud):
        self._guard("Mudar velocidade", self.dev.set_baudrate, int(baud))
        self._baud = int(baud)

    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, t):
        self._timeout = t

    @property
    def break_condition(self):
        return self._break

    @break_condition.setter
    def break_condition(self, on):
        self._guard("BREAK", self.dev.set_break, bool(on))
        self._break = bool(on)

    @property
    def dtr(self):
        return None

    @dtr.setter
    def dtr(self, on):
        self._guard("DTR", self.dev.set_dtr, bool(on))

    @property
    def rts(self):
        return None

    @rts.setter
    def rts(self, on):
        self._guard("RTS", self.dev.set_rts, bool(on))

    # ---------------------------------------------------------------- dados
    def read(self, size=1):
        data = bytearray()
        end = None if self._timeout is None else time.perf_counter() + self._timeout
        while len(data) < size:
            chunk = self._guard("Leitura USB", self.dev.read_data, size - len(data))
            if chunk:
                data.extend(chunk)
                continue
            if end is not None and time.perf_counter() >= end:
                break
            time.sleep(0.001)
        return bytes(data)

    def write(self, data):
        return self._guard("Escrita USB", self.dev.write_data, bytes(data))

    def reset_input_buffer(self):
        self._guard("Limpar buffer", self.dev.purge_rx_buffer)

    def reset_output_buffer(self):
        self._guard("Limpar buffer", self.dev.purge_tx_buffer)


def _explain_open_error(port, e):
    msg = str(e)
    low = msg.lower()
    if isinstance(e, DependencyMissing):
        return msg
    if "access" in low or "busy" in low or "errno 13" in low:
        return (f"A interface {port} está a ser usada por outro programa (VCDS, outra janela?). "
                "Feche-o e tente de novo.")
    if "not found" in low or "no such device" in low or "no backend" in low or "unknown" in low:
        return (f"Interface {port} não encontrada. Confirme que está ligada e que tem o driver WinUSB "
                "(Zadig) instalado.")
    if "not supported" in low or "notimplemented" in low or "errno 40" in low:
        return (f"O Windows não deixa o libusb abrir {port}: falta o driver WinUSB. Instale-o com o Zadig "
                "(ver README → HEX-USB clone).")
    return f"Não foi possível abrir {port}: {msg}"
