"""Parâmetros OBD-II normalizados (SAE J1979 / ISO 15031-5, modo 01 e 02).

Cada parâmetro tem a fórmula da norma. Só se pede à centralina um PID que ela própria declarou suportar (PIDs
0x00/0x20/0x40/… devolvem um mapa de bits): o programa nunca assume que um PID existe em todos os carros.

A, B, C, D = 1.º, 2.º, 3.º e 4.º bytes de dados da resposta.
"""

from ..i18n import tr, tr_data


class Pid:
    __slots__ = ("pid", "source_name", "unit", "size", "fn", "lo", "hi", "source_short")

    def __init__(self, pid, name, unit, size, fn, lo=None, hi=None, short=None):
        self.pid, self.source_name, self.unit, self.size, self.fn = pid, name, unit, size, fn
        self.lo, self.hi = lo, hi          # gama da norma (para escalas de gráficos/instrumentos)
        self.source_short = short or name

    @property
    def name(self):
        return tr_data(self.source_name)

    @property
    def short(self):
        return tr_data(self.source_short)

    def decode(self, data):
        if len(data) < self.size:
            raise ValueError(tr("PID {pid:02X}: esperava {size} byte(s), recebeu {n}",
                                pid=self.pid, size=self.size, n=len(data)))
        value = self.fn(*data[:self.size])
        return tr_data(value) if isinstance(value, str) else value     # tipo de combustível, norma OBD


def _pct(a):
    return round(a * 100 / 255, 1)


def _trim(a):
    return round((a - 128) * 100 / 128, 1)


def _u16(a, b):
    return 256 * a + b


FUEL_TYPES = {1: "Gasolina", 2: "Metanol", 3: "Etanol", 4: "Gasóleo", 5: "GPL", 6: "GNC", 7: "Propano",
              8: "Eléctrico", 9: "Bi-combustível gasolina", 10: "Bi-combustível metanol",
              11: "Bi-combustível etanol", 12: "Bi-combustível GPL", 13: "Bi-combustível GNC",
              14: "Bi-combustível propano", 15: "Bi-combustível eléctrico", 16: "Híbrido gasolina",
              17: "Híbrido etanol", 18: "Híbrido gasóleo", 19: "Híbrido eléctrico", 23: "Híbrido gasóleo"}

OBD_STANDARDS = {1: "OBD-II (CARB)", 2: "OBD (EPA)", 3: "OBD e OBD-II", 4: "OBD-I", 5: "Sem OBD",
                 6: "EOBD (Europa)", 7: "EOBD e OBD-II", 8: "EOBD e OBD", 9: "EOBD, OBD e OBD-II",
                 10: "JOBD (Japão)", 11: "JOBD e OBD-II", 12: "JOBD e EOBD", 13: "JOBD, EOBD e OBD-II",
                 17: "EMD", 18: "EMD+", 19: "HD OBD-C", 20: "HD OBD", 21: "WWH OBD", 23: "HD EOBD-I",
                 24: "HD EOBD-I N", 25: "HD EOBD-II", 26: "HD EOBD-II N", 28: "OBDBr-1", 29: "OBDBr-2",
                 30: "KOBD", 31: "IOBD I", 32: "IOBD II", 33: "HD EOBD-IV"}

TABLE = {p.pid: p for p in [
    Pid(0x04, "Carga calculada do motor", "%", 1, _pct, 0, 100, "Carga"),
    Pid(0x05, "Temperatura do líquido de refrigeração", "°C", 1, lambda a: a - 40, -40, 215, "Temp. líquido"),
    Pid(0x06, "Correcção de mistura curta — banco 1", "%", 1, _trim, -100, 99.2, "STFT B1"),
    Pid(0x07, "Correcção de mistura longa — banco 1", "%", 1, _trim, -100, 99.2, "LTFT B1"),
    Pid(0x08, "Correcção de mistura curta — banco 2", "%", 1, _trim, -100, 99.2, "STFT B2"),
    Pid(0x09, "Correcção de mistura longa — banco 2", "%", 1, _trim, -100, 99.2, "LTFT B2"),
    Pid(0x0A, "Pressão do combustível (relativa)", "kPa", 1, lambda a: 3 * a, 0, 765, "Pressão comb."),
    Pid(0x0B, "Pressão absoluta no colector de admissão", "kPa", 1, lambda a: a, 0, 255, "MAP"),
    Pid(0x0C, "Rotação do motor", "rpm", 2, lambda a, b: _u16(a, b) / 4, 0, 16383.75, "Rotação"),
    Pid(0x0D, "Velocidade do veículo", "km/h", 1, lambda a: a, 0, 255, "Velocidade"),
    Pid(0x0E, "Avanço da ignição (cilindro 1)", "°", 1, lambda a: a / 2 - 64, -64, 63.5, "Avanço"),
    Pid(0x0F, "Temperatura do ar de admissão", "°C", 1, lambda a: a - 40, -40, 215, "Temp. ar"),
    Pid(0x10, "Massa de ar (MAF)", "g/s", 2, lambda a, b: _u16(a, b) / 100, 0, 655.35, "MAF"),
    Pid(0x11, "Posição absoluta da borboleta", "%", 1, _pct, 0, 100, "Borboleta"),
    Pid(0x1C, "Norma OBD do veículo", "", 1, lambda a: OBD_STANDARDS.get(a) or tr("tipo {n}", n=a)),
    Pid(0x1F, "Tempo desde o arranque", "s", 2, _u16, 0, 65535, "Tempo motor"),
    Pid(0x21, "Distância com a luz de avaria acesa", "km", 2, _u16, 0, 65535, "Dist. c/ MIL"),
    Pid(0x22, "Pressão na rampa (relativa ao vácuo do colector)", "kPa", 2,
        lambda a, b: round(_u16(a, b) * 0.079, 1), 0, 5177.3, "Pressão rampa rel."),
    Pid(0x23, "Pressão na rampa de combustível (diesel / injecção directa)", "kPa", 2,
        lambda a, b: _u16(a, b) * 10, 0, 655350, "Pressão rampa"),
    Pid(0x2C, "EGR comandada", "%", 1, _pct, 0, 100, "EGR cmd"),
    Pid(0x2D, "Erro da EGR", "%", 1, _trim, -100, 99.2, "Erro EGR"),
    Pid(0x2F, "Nível de combustível", "%", 1, _pct, 0, 100, "Combustível"),
    Pid(0x30, "Aquecimentos desde que as avarias foram apagadas", "", 1, lambda a: a, 0, 255, "Aquecimentos"),
    Pid(0x31, "Distância desde que as avarias foram apagadas", "km", 2, _u16, 0, 65535, "Dist. desde apagar"),
    Pid(0x33, "Pressão atmosférica", "kPa", 1, lambda a: a, 0, 255, "Pressão atm."),
    Pid(0x3C, "Temperatura do catalisador — banco 1, sensor 1", "°C", 2,
        lambda a, b: round(_u16(a, b) / 10 - 40, 1), -40, 6513.5, "Temp. cat."),
    Pid(0x42, "Tensão da unidade de comando", "V", 2, lambda a, b: round(_u16(a, b) / 1000, 3), 0, 65.535,
        "Tensão ECU"),
    Pid(0x43, "Carga absoluta", "%", 2, lambda a, b: round(_u16(a, b) * 100 / 255, 1), 0, 25700, "Carga abs."),
    Pid(0x44, "Relação ar/combustível comandada (lambda)", "λ", 2, lambda a, b: round(_u16(a, b) * 2 / 65536, 3),
        0, 2, "Lambda cmd"),
    Pid(0x45, "Posição relativa da borboleta", "%", 1, _pct, 0, 100, "Borboleta rel."),
    Pid(0x46, "Temperatura ambiente", "°C", 1, lambda a: a - 40, -40, 215, "Temp. ambiente"),
    Pid(0x47, "Posição absoluta da borboleta B", "%", 1, _pct, 0, 100, "Borboleta B"),
    Pid(0x49, "Posição do pedal do acelerador D", "%", 1, _pct, 0, 100, "Pedal D"),
    Pid(0x4A, "Posição do pedal do acelerador E", "%", 1, _pct, 0, 100, "Pedal E"),
    Pid(0x4C, "Actuador da borboleta comandado", "%", 1, _pct, 0, 100, "Borboleta cmd"),
    Pid(0x4D, "Tempo com a luz de avaria acesa", "min", 2, _u16, 0, 65535, "Tempo c/ MIL"),
    Pid(0x4E, "Tempo desde que as avarias foram apagadas", "min", 2, _u16, 0, 65535, "Tempo desde apagar"),
    Pid(0x51, "Tipo de combustível", "", 1, lambda a: FUEL_TYPES.get(a) or tr("tipo {n}", n=a)),
    Pid(0x5C, "Temperatura do óleo do motor", "°C", 1, lambda a: a - 40, -40, 210, "Temp. óleo"),
    Pid(0x5D, "Início da injecção", "°", 2, lambda a, b: round(_u16(a, b) / 128 - 210, 2), -210, 301.99,
        "Início injecção"),
    Pid(0x5E, "Consumo de combustível do motor", "L/h", 2, lambda a, b: _u16(a, b) / 20, 0, 3276.75, "Consumo"),
    Pid(0x61, "Binário pedido pelo condutor", "%", 1, lambda a: a - 125, -125, 130, "Binário pedido"),
    Pid(0x62, "Binário real do motor", "%", 1, lambda a: a - 125, -125, 130, "Binário real"),
    Pid(0x63, "Binário de referência do motor", "Nm", 2, _u16, 0, 65535, "Binário ref."),
]}

# PIDs que só fazem sentido como texto (não entram em gráficos/instrumentos).
TEXT_PIDS = {0x1C, 0x51}
# PIDs de informação (lidos uma vez, não em contínuo).
INFO_PIDS = {0x1C, 0x51, 0x21, 0x30, 0x31, 0x4D, 0x4E}

# Monitores de prontidão (PID 01, bytes C/D)
SPARK_MONITORS = ("Catalisador", "Catalisador aquecido", "Sistema de evaporação", "Ar secundário",
                  "Refrigerante do A/C", "Sonda lambda", "Aquecimento da sonda lambda", "EGR / VVT")
DIESEL_MONITORS = ("Catalisador NMHC", "NOx / SCR", None, "Pressão do turbo", None,
                   "Sensor dos gases de escape", "Filtro de partículas", "EGR / VVT")
CONTINUOUS_MONITORS = ("Falhas de combustão", "Sistema de combustível", "Componentes")


def bitmap_pids(base, data):
    """Mapa de bits de 4 bytes dos PIDs 0x00/0x20/0x40… → conjunto dos PIDs suportados."""
    out = set()
    for i in range(32):
        if data[i // 8] & (0x80 >> (i % 8)):
            out.add(base + i + 1)
    return out


def decode_monitor_status(a, b, c, d):
    """PID 01: luz de avaria, número de avarias e monitores de prontidão.
    Cada monitor: {"name", "supported", "complete"}."""
    diesel = bool(b & 0x08)
    monitors = []
    for i, name in enumerate(CONTINUOUS_MONITORS):
        sup = bool(b & (1 << i))
        monitors.append({"name": tr_data(name), "supported": sup, "complete": sup and not (b & (1 << (i + 4))),
                         "continuous": True})
    names = DIESEL_MONITORS if diesel else SPARK_MONITORS
    for i, name in enumerate(names):
        if name is None:
            continue
        sup = bool(c & (1 << i))
        monitors.append({"name": tr_data(name), "supported": sup, "complete": sup and not (d & (1 << i)),
                         "continuous": False})
    ignition = tr("compressão (diesel)") if diesel else tr("faísca (gasolina)")
    return {"mil": bool(a & 0x80), "dtc_count": a & 0x7F, "ignition": ignition, "monitors": monitors}


def name(pid):
    p = TABLE.get(pid)
    return p.name if p else tr("PID {pid:02X} (sem definição no programa)", pid=pid)
