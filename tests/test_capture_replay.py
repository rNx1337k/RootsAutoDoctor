"""Validação da leitura de avarias KW1281 contra uma resposta REAL de uma centralina.

Os bytes abaixo foram lidos de um Audi A3 8L (motor 1.9 TDI, "EDC SG 1536") por um HEX-USB+CAN em modo
VCDS e gravados por USBPcap a 21/10/2026. São a resposta KW1281 em claro da centralina (bloco 0xFC), igual à
que um cabo KKL entrega — não têm nada do protocolo proprietário do cabo. O VCDS mostrou, no mesmo momento,
estas 5 avarias (fotografia): 17552, 18062, 18043, 18044 (35-00), 18045.

Dois níveis de teste, ambos sem carro:
  1. descodificação directa dos bytes reais (prova que byte→código bate com o VCDS);
  2. percurso completo read_faults() através do emulador de centralina do projecto, alimentado com os mesmos
     códigos (prova que a cadeia protocolo→descodificação os extrai bem). Origem dos dados: SIMULADOR a repetir
     uma resposta gravada — nunca se apresenta como leitura ao vivo.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import vag_data
from rad.kline import KLine, SIM_PORT
from rad.session import ECUSession

# Bloco 0xFC gravado (sem o 0xFC inicial nem o 0x03 final): 5 triplos (código alto, código baixo, estado).
CAPTURED_FAULT_BYTES = bytes.fromhex("4490A3 468EA3 467BA3 467C23 467DA3".replace(" ", ""))

# O que o VCDS mostrou no mesmo instante (fotografia de 21/10/2026).
VCDS_PHOTO = [
    ("17552", True),    # P1144 Medidor de massa de ar (G70) — 35-10 intermitente
    ("18062", True),    # P1654 — 35-10 intermitente
    ("18043", True),    # P1635 — 35-10 intermitente
    ("18044", False),   # P1636 — 35-00 (estático, não intermitente)
    ("18045", True),    # P1637 — 35-10 intermitente
]


def _triplets(data):
    return [(((data[i] << 8) | data[i + 1]), data[i + 2]) for i in range(0, len(data) - 2, 3)]


def test_decode_matches_the_vcds_photo():
    got = []
    for code, status in _triplets(CAPTURED_FAULT_BYTES):
        f = vag_data.decode_fault(code, status)
        got.append((f["vag"], f["intermittent"]))
        assert f["elab_code"] == 35, f            # todas "35" (0x23) na foto
    assert got == VCDS_PHOTO


def test_read_faults_full_path_over_recorded_response():
    # Alimenta o emulador KW1281 com exactamente os códigos gravados e corre o read_faults() real.
    from rad import simulator
    original = copy.deepcopy(simulator.ENGINE["faults"])
    simulator.ENGINE["faults"] = [(c, s) for c, s in _triplets(CAPTURED_FAULT_BYTES)]
    try:
        kl = KLine(SIM_PORT, echo="auto")
        kl.open()
        s = ECUSession(kl)
        info = s.connect(0x01)
        assert info["protocol"] == "KW1281"
        assert info["simulated"] is True          # origem: simulador, nunca apresentado como real
        faults = s.read_faults()
        assert [(f["vag"], f["intermittent"]) for f in faults] == VCDS_PHOTO
        assert all(f["elab_code"] == 35 for f in faults)
        s.disconnect()
    finally:
        simulator.ENGINE["faults"] = original


def test_no_faults_block_is_not_mistaken_for_a_fault():
    # FF FF 88 = "sem avarias": não pode aparecer como código 65535
    from rad import simulator
    original = copy.deepcopy(simulator.ENGINE["faults"])
    simulator.ENGINE["faults"] = []
    try:
        kl = KLine(SIM_PORT, echo="auto")
        kl.open()
        s = ECUSession(kl)
        s.connect(0x01)
        assert s.read_faults() == []
        s.disconnect()
    finally:
        simulator.ENGINE["faults"] = original


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("OK", name)
