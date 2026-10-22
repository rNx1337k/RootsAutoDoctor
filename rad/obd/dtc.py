"""Códigos de avaria normalizados (SAE J2012 / ISO 15031-6) e estado das avarias UDS (ISO 14229-1).

Formato de 2 bytes (OBD-II, modos 03/07/0A):
    bits 15-14  sistema: 00 P (motor/transmissão), 01 C (chassis), 10 B (carroçaria), 11 U (rede)
    bits 13-12  1.º dígito (0 = genérico normalizado, 1 = do fabricante, 2/3 = depende do sistema)
    bits 11-0   três dígitos hexadecimais
UDS acrescenta um 3.º byte: o "failure type byte" (FTB), que detalha o tipo de falha.

Descrições: só a ESTRUTURA do código é universal. A descrição de cada código vem de uma base de dados com
origem declarada (`SOURCES`); um código sem descrição na base é apresentado como tal — nunca se inventa um
texto. Os códigos do fabricante (P1xxx, …) só têm descrição se uma base desse fabricante for instalada.
"""
import json
import logging
import os

log = logging.getLogger(__name__)

SYSTEMS = {0: "P", 1: "C", 2: "B", 3: "U"}
SYSTEM_NAMES = {"P": "Motor / transmissão", "C": "Chassis", "B": "Carroçaria", "U": "Rede / comunicação"}

# Fontes das descrições. A base genérica incluída é um resumo, em português, dos títulos dos códigos genéricos
# mais frequentes (SAE J2012 / ISO 15031-6). Outras bases (licenciadas ou do fabricante) podem ser acrescentadas
# como ficheiros JSON em `data/` com o mesmo formato — ver load_database().
SOURCES = {
    "generic": "Base genérica do Roots Auto Doctor — títulos resumidos dos códigos normalizados SAE J2012 / "
               "ISO 15031-6 (só códigos genéricos; confirmar sempre com a documentação do fabricante)",
}

# Títulos resumidos dos códigos genéricos mais comuns.
GENERIC = {
    # Medição de ar e combustível
    "P0087": "Pressão do combustível na rampa demasiado baixa",
    "P0088": "Pressão do combustível na rampa demasiado alta",
    "P0089": "Regulador de pressão do combustível 1 — funcionamento",
    "P0093": "Fuga no sistema de combustível detectada (fuga grande)",
    "P0045": "Válvula de comando da pressão do turbo — circuito aberto",
    "P0046": "Válvula de comando da pressão do turbo — gama/funcionamento",
    "P0068": "Pressão no colector / massa de ar — incoerente com a posição da borboleta",
    "P0069": "Pressão no colector / pressão atmosférica — incoerência",
    "P0100": "Medidor de massa de ar — circuito",
    "P0101": "Medidor de massa de ar — gama/funcionamento",
    "P0102": "Medidor de massa de ar — sinal baixo",
    "P0103": "Medidor de massa de ar — sinal alto",
    "P0105": "Sensor de pressão do colector (MAP) — circuito",
    "P0106": "Sensor de pressão do colector (MAP) — gama/funcionamento",
    "P0107": "Sensor de pressão do colector (MAP) — sinal baixo",
    "P0108": "Sensor de pressão do colector (MAP) — sinal alto",
    "P0110": "Sensor de temperatura do ar de admissão — circuito",
    "P0112": "Sensor de temperatura do ar de admissão — sinal baixo",
    "P0113": "Sensor de temperatura do ar de admissão — sinal alto",
    "P0115": "Sensor de temperatura do líquido de refrigeração — circuito",
    "P0116": "Sensor de temperatura do líquido de refrigeração — gama/funcionamento",
    "P0117": "Sensor de temperatura do líquido de refrigeração — sinal baixo",
    "P0118": "Sensor de temperatura do líquido de refrigeração — sinal alto",
    "P0120": "Sensor de posição da borboleta / pedal A — circuito",
    "P0121": "Sensor de posição da borboleta / pedal A — gama/funcionamento",
    "P0122": "Sensor de posição da borboleta / pedal A — sinal baixo",
    "P0123": "Sensor de posição da borboleta / pedal A — sinal alto",
    "P0128": "Termóstato — temperatura do líquido abaixo da temperatura de regulação",
    "P0130": "Sonda lambda (banco 1, sensor 1) — circuito",
    "P0131": "Sonda lambda (banco 1, sensor 1) — tensão baixa",
    "P0132": "Sonda lambda (banco 1, sensor 1) — tensão alta",
    "P0133": "Sonda lambda (banco 1, sensor 1) — resposta lenta",
    "P0134": "Sonda lambda (banco 1, sensor 1) — sem actividade",
    "P0135": "Aquecimento da sonda lambda (banco 1, sensor 1) — circuito",
    "P0136": "Sonda lambda (banco 1, sensor 2) — circuito",
    "P0141": "Aquecimento da sonda lambda (banco 1, sensor 2) — circuito",
    "P0171": "Mistura demasiado pobre (banco 1)",
    "P0172": "Mistura demasiado rica (banco 1)",
    "P0174": "Mistura demasiado pobre (banco 2)",
    "P0175": "Mistura demasiado rica (banco 2)",
    "P0190": "Sensor de pressão da rampa de combustível — circuito",
    "P0191": "Sensor de pressão da rampa de combustível — gama/funcionamento",
    "P0192": "Sensor de pressão da rampa de combustível — sinal baixo",
    "P0193": "Sensor de pressão da rampa de combustível — sinal alto",
    "P0201": "Injector do cilindro 1 — circuito",
    "P0202": "Injector do cilindro 2 — circuito",
    "P0203": "Injector do cilindro 3 — circuito",
    "P0204": "Injector do cilindro 4 — circuito",
    "P0205": "Injector do cilindro 5 — circuito",
    "P0206": "Injector do cilindro 6 — circuito",
    "P0234": "Pressão do turbo excessiva (sobrepressão)",
    "P0299": "Pressão do turbo insuficiente",
    # Ignição / falhas de combustão
    "P0300": "Falhas de combustão aleatórias / em vários cilindros",
    "P0301": "Falha de combustão no cilindro 1",
    "P0302": "Falha de combustão no cilindro 2",
    "P0303": "Falha de combustão no cilindro 3",
    "P0304": "Falha de combustão no cilindro 4",
    "P0305": "Falha de combustão no cilindro 5",
    "P0306": "Falha de combustão no cilindro 6",
    "P0325": "Sensor de detonação 1 (banco 1) — circuito",
    "P0335": "Sensor de posição da cambota A — circuito",
    "P0340": "Sensor de posição da árvore de cames A (banco 1) — circuito",
    "P0380": "Velas de incandescência — circuito A",
    # Emissões auxiliares
    "P0400": "Recirculação de gases de escape (EGR) — fluxo",
    "P0401": "Recirculação de gases de escape (EGR) — fluxo insuficiente",
    "P0402": "Recirculação de gases de escape (EGR) — fluxo excessivo",
    "P0403": "Recirculação de gases de escape (EGR) — circuito de comando",
    "P0420": "Catalisador (banco 1) — eficiência abaixo do limite",
    "P0430": "Catalisador (banco 2) — eficiência abaixo do limite",
    "P0440": "Sistema de controlo de evaporação (EVAP)",
    "P0442": "Sistema EVAP — fuga pequena detectada",
    "P0455": "Sistema EVAP — fuga grande detectada",
    "P0480": "Ventilador de arrefecimento 1 — circuito de comando",
    # Velocidade, ralenti, entradas
    "P0500": "Sensor de velocidade do veículo A",
    "P0505": "Controlo do ralenti — sistema",
    "P0506": "Ralenti — rotação abaixo do esperado",
    "P0507": "Ralenti — rotação acima do esperado",
    "P0560": "Tensão do sistema",
    "P0562": "Tensão do sistema baixa",
    "P0563": "Tensão do sistema alta",
    # Unidade de comando
    "P0600": "Ligação de comunicação série",
    "P0601": "Unidade de comando — erro de soma de verificação da memória interna",
    "P0606": "Unidade de comando — processador",
    "P0670": "Módulo das velas de incandescência — circuito de comando",
    # Transmissão
    "P0700": "Sistema de comando da transmissão (pedido de luz de avaria)",
    "P0705": "Sensor de gama da transmissão — circuito",
    "P0715": "Sensor de velocidade de entrada / turbina — circuito",
    # P2xxx genéricos
    "P2002": "Filtro de partículas (banco 1) — eficiência abaixo do limite",
    "P2015": "Sensor de posição das borboletas do colector (banco 1) — gama/funcionamento",
    "P2187": "Mistura demasiado pobre ao ralenti (banco 1)",
    "P2279": "Fuga no sistema de admissão de ar",
    "P2452": "Sensor de pressão do filtro de partículas A — circuito",
    "P2463": "Filtro de partículas — acumulação de fuligem",
    # Rede
    "U0001": "Barramento CAN de alta velocidade — comunicação",
    "U0100": "Perda de comunicação com a unidade do motor (ECM/PCM A)",
    "U0101": "Perda de comunicação com a unidade da caixa (TCM)",
    "U0121": "Perda de comunicação com a unidade do ABS",
    "U0140": "Perda de comunicação com o módulo da carroçaria (BCM)",
    "U0155": "Perda de comunicação com o painel de instrumentos",
    # Chassis
    "C0035": "Sensor de velocidade da roda dianteira esquerda — circuito",
    "C0040": "Sensor de velocidade da roda dianteira direita — circuito",
    "C0045": "Sensor de velocidade da roda traseira esquerda — circuito",
    "C0050": "Sensor de velocidade da roda traseira direita — circuito",
}

# Subsistemas dos códigos P0xxx (estrutura definida na norma; serve para orientar quando não há descrição).
P0_GROUPS = {
    "0": "medição de ar/combustível e emissões auxiliares",
    "1": "medição de ar e combustível",
    "2": "medição de ar e combustível (circuito dos injectores)",
    "3": "sistema de ignição ou falhas de combustão",
    "4": "controlo auxiliar de emissões",
    "5": "velocidade do veículo, ralenti e entradas auxiliares",
    "6": "unidade de comando e saídas auxiliares",
    "7": "transmissão",
    "8": "transmissão",
    "9": "transmissão",
    "A": "propulsão híbrida",
}

# Failure Type Byte (UDS, 3.º byte do DTC) — categorias comuns de SAE J2012-DA.
FTB = {
    0x00: "sem informação adicional",
    0x01: "falha eléctrica geral",
    0x02: "falha geral de sinal",
    0x03: "falha de sinal FM/PWM",
    0x04: "falha interna do sistema",
    0x05: "falha de programação do sistema",
    0x06: "falha de algoritmo",
    0x07: "falha mecânica",
    0x08: "falha de mensagem de barramento / sinal",
    0x09: "falha de componente",
    0x11: "curto-circuito à massa",
    0x12: "curto-circuito à bateria",
    0x13: "circuito aberto",
    0x14: "curto-circuito à massa ou circuito aberto",
    0x15: "curto-circuito à bateria ou circuito aberto",
    0x16: "tensão do circuito abaixo do limite",
    0x17: "tensão do circuito acima do limite",
    0x1C: "tensão do circuito fora do intervalo",
    0x29: "sinal inválido",
    0x62: "falha na comparação de sinais",
    0x64: "falha de plausibilidade do sinal",
    0x81: "dados série inválidos recebidos",
    0x87: "mensagem em falta",
}

# Bits do byte de estado UDS (ISO 14229-1, ReadDTCInformation)
UDS_STATUS_BITS = (
    (0x01, "testFailed", "falha presente agora"),
    (0x02, "testFailedThisOperationCycle", "falhou neste ciclo de condução"),
    (0x04, "pendingDTC", "pendente"),
    (0x08, "confirmedDTC", "confirmada (memorizada)"),
    (0x10, "testNotCompletedSinceLastClear", "teste não concluído desde o último apagar"),
    (0x20, "testFailedSinceLastClear", "falhou desde o último apagar"),
    (0x40, "testNotCompletedThisOperationCycle", "teste não concluído neste ciclo"),
    (0x80, "warningIndicatorRequested", "pede luz de aviso"),
)

_extra_db = {}          # código → (descrição, chave da fonte), de bases instaladas em data/


def decode(b1, b2):
    """Dois bytes → código ("P0301"). Os bytes 00 00 não são um código (enchimento das respostas)."""
    system = SYSTEMS[(b1 >> 6) & 0x03]
    first = (b1 >> 4) & 0x03
    return f"{system}{first}{b1 & 0x0F:X}{b2 >> 4:X}{b2 & 0x0F:X}"


def encode(code):
    """Inverso de decode(): "P0301" → (0x03, 0x01)."""
    code = code.strip().upper()
    if len(code) != 5 or code[0] not in "PCBU":
        raise ValueError(f"código de avaria inválido: {code!r}")
    sysbits = "PCBU".index(code[0])
    first = int(code[1], 16)
    if first > 3:
        raise ValueError(f"código de avaria inválido: {code!r}")
    rest = int(code[2:], 16)
    return ((sysbits << 6) | (first << 4) | (rest >> 8)), rest & 0xFF


def is_generic(code):
    """True para os códigos normalizados (iguais em todas as marcas); False para os do fabricante."""
    s, d = code[0], code[1]
    if s == "P":
        return d == "0" or d == "2" or (d == "3" and code[2] in "456789ABCDEF")
    return d in "03"


def category(code):
    """Descrição estrutural do código — sempre verdadeira, mesmo sem base de dados."""
    s = code[0]
    kind = "genérico (normalizado)" if is_generic(code) else "específico do fabricante"
    out = f"{SYSTEM_NAMES[s]} · {kind}"
    if s == "P" and code[1] == "0":
        grp = P0_GROUPS.get(code[2])
        if grp:
            out += f" · {grp}"
    return out


def describe(code):
    """{"code", "desc", "source", "category", "generic"}. desc é None quando nenhuma base conhece o código."""
    desc, src = None, None
    if code in _extra_db:
        desc, src = _extra_db[code]
    elif code in GENERIC:
        desc, src = GENERIC[code], "generic"
    return {"code": code, "desc": desc, "source": SOURCES.get(src) if src else None,
            "category": category(code), "generic": is_generic(code)}


def ftb_text(ftb):
    return FTB.get(ftb, f"tipo de falha 0x{ftb:02X}")


def uds_status_text(status):
    """Lista das frases dos bits activos do byte de estado UDS."""
    return [txt for bit, _name, txt in UDS_STATUS_BITS if status & bit]


def load_database(path, source_key, source_text):
    """Acrescenta uma base de descrições (JSON {"P1234": "texto", ...}) com a fonte declarada.
    Usado para bases licenciadas ou do fabricante; nunca substitui a estrutura do código."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    SOURCES[source_key] = source_text
    n = 0
    for code, text in data.items():
        if code.startswith("_"):            # metadados ("_source", "_version", …)
            continue
        code = code.strip().upper()
        try:
            encode(code)
        except ValueError:
            log.warning("Base %s: código inválido ignorado: %r", source_key, code)
            continue
        _extra_db[code] = (str(text), source_key)
        n += 1
    return n


def load_installed_databases():
    """Carrega os ficheiros rad/obd/data/dtc_*.json (cada um com "_source" a dizer de onde vem)."""
    folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    if not os.path.isdir(folder):
        return 0
    total = 0
    for name in sorted(os.listdir(folder)):
        if not (name.startswith("dtc_") and name.endswith(".json")):
            continue
        path = os.path.join(folder, name)
        try:
            with open(path, encoding="utf-8") as fh:
                meta = json.load(fh).get("_source")
            if not meta:
                log.warning("Base %s sem \"_source\": ignorada (a origem das descrições tem de ser conhecida)", name)
                continue
            total += load_database(path, name[:-5], meta)
        except Exception:
            log.warning("Não foi possível carregar a base de avarias %s", name, exc_info=True)
    return total
