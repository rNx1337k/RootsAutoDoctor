"""Matriz de compatibilidade: o que cada interface consegue fazer com cada protocolo, e com que prova.

É a fonte única para a página "Compatibilidade" da aplicação, para docs/COBERTURA.md e para a versão inglesa
docs/COVERAGE.md (gerados a partir daqui; um teste confirma que os documentos estão actualizados e que os testes
citados existem).

Níveis de prova, do mais forte para o mais fraco — nunca se sobe de nível sem a prova correspondente:
"""

HW = "hardware"          # confirmado numa sessão real com o hardware e o veículo
CAPTURE = "captura"      # validado contra bytes reais de uma centralina (captura USB), sem o cabo do programa
SIM = "simulador"        # implementado e testado com simulador
IMPL = "implementado"    # implementado, sem validação (nem simulador completo)
PARTIAL = "parcial"
BLOCKED = "bloqueado"    # impedido por hardware/firmware fechado, licença ou norma
NONE = "não implementado"

LEVELS = {
    HW: ("Confirmado em hardware real", "ok"),
    CAPTURE: ("Validado com dados reais capturados", "ok"),
    SIM: ("Testado com simulador", "info"),
    IMPL: ("Implementado, não validado", "warn"),
    PARTIAL: ("Parcial", "warn"),
    BLOCKED: ("Bloqueado", "bad"),
    NONE: ("Não implementado", "muted"),
}

# Cada entrada: interface, protocolo, e o estado de cada etapa (detectar / iniciar / comunicar com a ECU /
# interpretar), os serviços, as limitações e os testes que provam o estado.
MATRIX = [
    {
        "interface": "Cabo KKL 409.1 (FTDI / CH340, porta COM)",
        "protocol": "KW1281 (linha K, init 5 baud) — VAG até ~2005",
        "detect": IMPL, "init": SIM, "ecu": SIM, "interpret": CAPTURE,
        "services": "Identificação, avarias (ler/apagar com releitura), blocos de medição, ajuste básico, "
                    "adaptação (com verificação), codificação (com verificação), login, teste de saídas",
        "limits": "Sem validação física com um cabo KKL (o proprietário ainda não tem um). A leitura de avarias foi "
                  "validada contra a resposta real de um Audi A3 8L 1.9 TDI capturada por USBPcap.",
        "tests": ["test_capture_replay", "test_simulator", "test_car_readiness", "test_write_safety"],
    },
    {
        "interface": "Cabo KKL 409.1 (FTDI / CH340, porta COM)",
        "protocol": "KWP2000 / ISO 14230 (linha K) — VAG",
        "detect": IMPL, "init": SIM, "ecu": SIM, "interpret": SIM,
        "services": "Identificação, avarias (ler/apagar), blocos de medição",
        "limits": "Só leitura (escrita devolve 'não suportado' por desenho). Byte de estado das avarias KWP2000 "
                  "descodificado com a tabela KW1281 — por confirmar num carro.",
        "tests": ["test_simulator", "test_robustness"],
    },
    {
        "interface": "Interface J2534 04.04 (PassThru)",
        "protocol": "KWP2000 / ISO 14230 com init 5 baud",
        "detect": IMPL, "init": SIM, "ecu": SIM, "interpret": SIM,
        "services": "Identificação, avarias, blocos de medição",
        "limits": "Testado só com o simulador J2534. KW1281 é recusado (a norma J2534 não permite os tempos por "
                  "byte). ISO 15765 / UDS por J2534 ainda não implementado.",
        "tests": ["test_j2534", "test_bridges"],
    },
    {
        "interface": "Interface J2534 04.04 (PassThru)",
        "protocol": "ISO 15765-4 CAN / UDS",
        "detect": IMPL, "init": NONE, "ecu": NONE, "interpret": SIM,
        "services": "—",
        "limits": "Os serviços OBD-II/UDS já existem (independentes da interface); falta o canal ISO15765 na ponte "
                  "J2534.",
        "tests": [],
    },
    {
        "interface": "Clone HEX-USB+CAN (FTDI 0403:FA24, driver RT-USB ou WinUSB)",
        "protocol": "Microcontrolador do cabo (tramas 53/4D)",
        "detect": HW, "init": HW, "ecu": BLOCKED, "interpret": NONE,
        "services": "Versão do firmware, modo de arranque, teste da linha K feito pelo cabo, repor modo de origem",
        "limits": "A leitura de centralinas passa pelo protocolo próprio do microcontrolador; a captura do arranque "
                  "do VCDS mostra uma troca aparentemente autenticada/cifrada. Não se replica nem contorna: este "
                  "cabo não lê centralinas no Roots Auto Doctor. Modo KKL do firmware testado no carro: sem linha "
                  "K directa.",
        "tests": ["test_hexmcu", "test_hex_capture", "test_usb_transports"],
    },
    {
        "interface": "Ross-Tech HEX-V2 / HEX-NET genuínas",
        "protocol": "Firmware fechado da Ross-Tech",
        "detect": IMPL, "init": BLOCKED, "ecu": BLOCKED, "interpret": BLOCKED,
        "services": "Só detecção e explicação",
        "limits": "Sem interface de programação documentada nem autorização do fabricante.",
        "tests": ["test_cable"],
    },
    {
        "interface": "Autocom / Delphi CDP+ (e clones)",
        "protocol": "Firmware próprio",
        "detect": IMPL, "init": BLOCKED, "ecu": BLOCKED, "interpret": BLOCKED,
        "services": "Só detecção e explicação",
        "limits": "Protocolo do equipamento não documentado. A alternativa legítima é um adaptador aberto "
                  "(ELM327, KKL) ou uma interface J2534.",
        "tests": ["test_cable"],
    },
    {
        "interface": "Adaptador ELM327 (USB / Bluetooth, porta COM)",
        "protocol": "OBD-II / EOBD em ISO 15765-4 CAN (11 e 29 bits)",
        "detect": SIM, "init": SIM, "ecu": SIM, "interpret": SIM,
        "services": "Centralinas OBD, VIN, nome/calibração, luz de avaria e monitores de prontidão, avarias "
                    "memorizadas/pendentes/permanentes, apagar (modo 04, com confirmação e releitura), imagem "
                    "congelada, dados actuais só dos PIDs declarados pela centralina",
        "limits": "Sem validação com um ELM327 físico nem num carro. Clones baratos podem não implementar todos os "
                  "comandos (os opcionais são ignorados e registados).",
        "tests": ["test_obd", "test_obd_worker"],
    },
    {
        "interface": "Adaptador ELM327 (USB / Bluetooth, porta COM)",
        "protocol": "UDS / ISO 14229 (leitura) sobre CAN",
        "detect": SIM, "init": SIM, "ecu": SIM, "interpret": SIM,
        "services": "Identificação normalizada (F187/F189/F18C/F190/F197…), avarias UDS com tipo de falha e "
                    "estado; tratamento de 'resposta pendente' (NRC 78)",
        "limits": "Sem SecurityAccess, escrita, rotinas, controlo de saídas nem programação (por desenho). "
                  "Identificadores específicos do fabricante não incluídos.",
        "tests": ["test_obd"],
    },
    {
        "interface": "Adaptador ELM327 (USB / Bluetooth, porta COM)",
        "protocol": "OBD-II em linha K (ISO 9141-2, ISO 14230-4) e SAE J1850",
        "detect": SIM, "init": IMPL, "ecu": IMPL, "interpret": IMPL,
        "services": "Os mesmos serviços OBD-II (o adaptador escolhe o protocolo)",
        "limits": "Interpretação das linhas com cabeçalho e checksum testada com linhas sintéticas; o simulador só "
                  "imita CAN. Centralinas VAG antigas que só falam KW1281 não respondem por OBD-II.",
        "tests": ["test_obd"],
    },
    {
        "interface": "Adaptador CAN cru (tramas CAN; ex.: SLCAN, SocketCAN)",
        "protocol": "ISO-TP (ISO 15765-2) + OBD-II / UDS",
        "detect": NONE, "init": NONE, "ecu": SIM, "interpret": SIM,
        "services": "ISO-TP completo (segmentação, Flow Control, STmin, pendente 0x78) e os mesmos serviços",
        "limits": "Falta o driver de um adaptador CAN concreto; o transporte está testado com um barramento simulado.",
        "tests": ["test_obd"],
    },
    {
        "interface": "—",
        "protocol": "DoIP (ISO 13400), SAE J1939, CAN-FD",
        "detect": NONE, "init": NONE, "ecu": NONE, "interpret": NONE,
        "services": "—",
        "limits": "Não implementado.",
        "tests": [],
    },
]

STAGES = (("detect", "Detecção"), ("init", "Iniciação"), ("ecu", "Comunicação com a ECU"),
          ("interpret", "Interpretação"))


def level_text(level):
    return LEVELS[level][0]


DOCUMENTS = {"pt": "COBERTURA.md", "en": "COVERAGE.md"}

_DOC_TEXT = {
    "pt": {
        "title": "# Cobertura de interfaces e protocolos",
        "generated": "Gerado a partir de `rad/coverage.py` (não editar à mão). Níveis de prova: ",
        "stages": "Detectar o cabo no USB ≠ abrir a interface ≠ comunicar com uma centralina ≠ interpretar bem a "
                  "resposta. Cada etapa tem o seu próprio nível.",
        "columns": ("Interface", "Protocolo", "Serviços", "Limitações", "Testes"),
        "footer": "**Nenhuma combinação está confirmada em hardware real com comunicação a uma centralina.** O que "
                  "está confirmado em hardware é a parte do cabo HEX que não depende do carro (USB, abertura, "
                  "microcontrolador).",
    },
    "en": {
        "title": "# Interface and protocol coverage",
        "generated": "Generated from `rad/coverage.py` (do not edit by hand). Evidence levels: ",
        "stages": "Seeing the cable on USB ≠ opening the interface ≠ talking to an ECU ≠ interpreting the answer "
                  "correctly. Each stage has its own level.",
        "columns": ("Interface", "Protocol", "Services", "Limitations", "Tests"),
        "footer": "**No combination is confirmed on real hardware communicating with an ECU.** What is confirmed on "
                  "hardware is the part of the HEX cable that does not depend on the car (USB, opening, "
                  "microcontroller).",
    },
}


def markdown(lang="pt"):
    """Texto de docs/COBERTURA.md (lang="pt") ou docs/COVERAGE.md (lang="en", para o GitHub).
    A versão inglesa usa as traduções do catálogo (rad/i18n_en.py), as mesmas da página Compatibilidade."""
    if lang == "en":
        from .i18n_en import EN
        t = lambda s: EN.get(s, s)  # noqa: E731
    else:
        t = lambda s: s  # noqa: E731
    text = _DOC_TEXT[lang]
    c_iface, c_proto, c_serv, c_lim, c_tests = text["columns"]
    out = [
        text["title"],
        "",
        text["generated"] + "; ".join(f"**{t(v[0])}**" for v in LEVELS.values()) + ".",
        "",
        text["stages"],
        "",
        f"| {c_iface} | {c_proto} | " + " | ".join(t(n) for _k, n in STAGES) + f" | {c_serv} | {c_lim} | {c_tests} |",
        "|---|---|" + "---|" * len(STAGES) + "---|---|---|",
    ]
    for e in MATRIX:
        tests = ", ".join(f"`{x}`" for x in e["tests"]) or "—"
        out.append(f"| {t(e['interface'])} | {t(e['protocol'])} | "
                   + " | ".join(t(level_text(e[k])) for k, _n in STAGES)
                   + f" | {t(e['services'])} | {t(e['limits'])} | {tests} |")
    out.append("")
    out.append(text["footer"])
    out.append("")
    return "\n".join(out)
