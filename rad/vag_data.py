"""Dados VAG: endereços de módulos, códigos de avaria, tipos de avaria e
fórmulas dos valores de medição (blocos de 3 bytes: fórmula, a, b)."""

# --------------------------------------------------------------- módulos VAG
VAG_MODULES = {
    0x01: "Electrónica do motor",
    0x02: "Caixa automática",
    0x03: "ABS / travões",
    0x05: "Acesso e arranque (Kessy)",
    0x06: "Banco passageiro",
    0x07: "Unidade de comando/visor",
    0x08: "Ar condicionado / Climatronic",
    0x09: "Electrónica central",
    0x11: "Electrónica do motor 2",
    0x13: "Regulação de distância (ACC)",
    0x14: "Amortecimento das rodas",
    0x15: "Airbags",
    0x16: "Electrónica coluna direcção",
    0x17: "Painel de instrumentos",
    0x18: "Aquecimento auxiliar",
    0x19: "Gateway CAN",
    0x22: "Tracção integral (Haldex)",
    0x25: "Imobilizador",
    0x26: "Tejadilho eléctrico",
    0x29: "Luz esquerda",
    0x34: "Regulação de nível",
    0x35: "Fecho centralizado",
    0x36: "Banco condutor",
    0x37: "Navegação",
    0x39: "Luz direita",
    0x41: "Bomba de gasóleo",
    0x44: "Direcção assistida",
    0x45: "Vigilância do habitáculo",
    0x46: "Módulo de conforto",
    0x47: "Sistema de som",
    0x52: "Porta passageiro",
    0x53: "Travão de estacionamento",
    0x55: "Faróis xénon / regulação",
    0x56: "Rádio",
    0x57: "Sintonizador TV",
    0x61: "Bateria",
    0x62: "Porta traseira esquerda",
    0x65: "Pressão dos pneus",
    0x67: "Comando de voz",
    0x69: "Atrelado",
    0x72: "Porta traseira direita",
    0x75: "Telemática",
    0x76: "Ajuda de estacionamento",
    0x77: "Telefone",
}

# Endereços varridos no Auto-Scan (os mais comuns nos VAG até ~2005)
AUTOSCAN_ADDRESSES = [0x01, 0x02, 0x03, 0x08, 0x09, 0x15, 0x16, 0x17, 0x19, 0x22,
                      0x25, 0x35, 0x36, 0x37, 0x44, 0x45, 0x46, 0x55, 0x56, 0x76, 0x77]


def module_name(address):
    return VAG_MODULES.get(address, "Controlador desconhecido")


# ------------------------------------------------------- códigos de avaria VAG
VAG_DTC = {
    0: "Nenhuma avaria detectada",
    281: "Sensor de velocidade do veículo (G68)",
    283: "Sensor de velocidade ABS dianteiro esq. (G47)",
    285: "Sensor de velocidade ABS dianteiro dir. (G45)",
    287: "Sensor de velocidade ABS traseiro dir. (G44)",
    290: "Sensor de velocidade ABS traseiro esq. (G46)",
    301: "Bomba de retorno ABS (V39)",
    513: "Sensor de rotação do motor (G28)",
    515: "Sensor Hall (G40)",
    516: "Interruptor de ralenti (F60)",
    518: "Sensor de posição da borboleta (G69)",
    522: "Sensor de temperatura do líquido de refrigeração (G62)",
    523: "Sensor de temperatura do ar de admissão (G42)",
    524: "Sensor de detonação 1 (G61)",
    525: "Sonda lambda (G39)",
    532: "Tensão de alimentação B+",
    537: "Regulação lambda",
    543: "Rotação máxima do motor excedida",
    553: "Medidor de massa de ar (G70)",
    561: "Adaptação da mistura",
    562: "Sensor de nível/temperatura do óleo (G266)",
    575: "Pressão no colector de admissão",
    577: "Controlo de detonação cilindro 1",
    588: "Detonador airbag condutor (N95)",
    589: "Detonador airbag passageiro (N131)",
    595: "Dados de colisão memorizados",
    597: "Roda fónica",
    625: "Sinal de velocidade",
    626: "Luz de aviso das velas (K29)",
    668: "Tensão de alimentação terminal 30",
    771: "Sensor do nível de combustível (G)",
    777: "Sensor do pedal do acelerador (G79)",
    779: "Sensor de temperatura exterior (G17)",
    1039: "Sensor de temperatura do líquido de refrigeração (G2)",
    1044: "Unidade de comando mal codificada",
    1087: "Ajuste básico não efectuado",
    1119: "Sinal de reconhecimento de mudança",
    1126: "Sinal de rotação do motor",
    1128: "Bobina de leitura do imobilizador (D2)",
    1130: "Funcionamento do ABS",
    1176: "Chave — sinal demasiado baixo",
    1177: "Unidade de comando do motor (imobilizador)",
    1179: "Programação de chaves",
    1217: "Detonador airbag lateral condutor (N199)",
    1218: "Detonador airbag lateral passageiro (N200)",
    1242: "Andares de saída na unidade de comando",
    1247: "Electroválvula de regulação da pressão do turbo (N75)",
    1257: "Válvula de controlo do ralenti (N71)",
    1259: "Relé da bomba de combustível (J17)",
    1262: "Electroválvula de limitação da pressão do turbo",
    1265: "Válvula EGR (N18)",
    1268: "Regulador da quantidade de injecção (N146)",
    1269: "Válvula do início de injecção (N108)",
    1276: "Bomba hidráulica ABS (V64)",
    1312: "Barramento de dados do grupo motopropulsor",
    1314: "Unidade de comando do motor",
    1316: "Unidade de comando do ABS",
}

# Descrições de alguns P-codes (VAG 16xxx/17xxx mapeiam para P0xxx/P1xxx)
PCODE_DESC = {
    "P0100": "Circuito do medidor de massa de ar",
    "P0101": "Medidor de massa de ar — gama/funcionamento",
    "P0105": "Circuito do sensor de pressão do colector (MAP)",
    "P0110": "Circuito do sensor de temperatura do ar de admissão",
    "P0115": "Circuito do sensor de temperatura do líquido de refrigeração",
    "P0120": "Circuito do sensor de posição da borboleta/pedal",
    "P0170": "Ajuste de combustível (banco 1)",
    "P0234": "Sobrepressão do turbo",
    "P0300": "Falhas de ignição aleatórias",
    "P0301": "Falha de ignição cilindro 1",
    "P0302": "Falha de ignição cilindro 2",
    "P0303": "Falha de ignição cilindro 3",
    "P0304": "Falha de ignição cilindro 4",
    "P0335": "Circuito do sensor da cambota",
    "P0340": "Circuito do sensor da árvore de cames",
    "P0380": "Circuito das velas de incandescência",
    "P0400": "Fluxo EGR",
    "P0401": "Fluxo EGR insuficiente",
    "P0420": "Eficiência do catalisador abaixo do limite",
    "P0500": "Sensor de velocidade do veículo",
    "P0560": "Tensão do sistema",
    "P0600": "Ligação de comunicação série",
    "P0605": "Erro de memória da unidade de comando",
    "P1555": "Pressão do turbo — limite superior excedido",
    "P1556": "Regulação da pressão do turbo — desvio negativo",
    "P1557": "Regulação da pressão do turbo — desvio positivo",
    "P1570": "Unidade de comando do motor bloqueada (imobilizador)",
    "P1650": "Barramento de dados — falta mensagem do painel de instrumentos",
}

# Tipos de avaria (status & 0x7F)
FAULT_ELABORATION = {
    0: "-",
    1: "Curto-circuito ao positivo",
    2: "Curto-circuito à massa",
    3: "Sem sinal",
    4: "Avaria mecânica",
    5: "Entrada aberta",
    6: "Sinal demasiado alto",
    7: "Sinal demasiado baixo",
    8: "Limite de regulação excedido",
    9: "Limite de adaptação excedido",
    10: "Limite de adaptação não atingido",
    11: "Limite de regulação não atingido",
    12: "Limite de adaptação (mult.) excedido",
    13: "Limite de adaptação (mult.) não atingido",
    14: "Limite de adaptação (adit.) excedido",
    15: "Limite de adaptação (adit.) não atingido",
    16: "Sinal fora de especificação",
    17: "Desvio de regulação",
    18: "Limite superior",
    19: "Limite inferior",
    20: "Avaria no ajuste básico",
    21: "Tempo de criação de pressão dianteiro demasiado longo",
    22: "Tempo de redução de pressão dianteiro demasiado longo",
    23: "Tempo de criação de pressão traseiro demasiado longo",
    24: "Tempo de redução de pressão traseiro demasiado longo",
    25: "Estado de interruptor indefinido",
    26: "Saída aberta",
    27: "Sinal não plausível",
    28: "Curto-circuito ao positivo",
    29: "Curto-circuito à massa",
    30: "Circuito aberto ou curto ao positivo",
    31: "Circuito aberto ou curto à massa",
    32: "Resistência demasiado alta",
    33: "Resistência demasiado baixa",
    34: "Ajuste básico não efectuado",
    35: "-",
    36: "Circuito aberto",
    37: "Unidade de comando avariada",
    38: "Limite de adaptação excedido (2)",
    39: "Sem comunicação",
    40: "Avaria eléctrica no circuito",
    41: "Sinal não plausível (2)",
    42: "Circuito aberto/curto-circuito",
    43: "Curto-circuito entre si",
    44: "Bloqueado ou sem tensão",
    45: "Velocidade demasiado alta",
    46: "Velocidade demasiado baixa",
    47: "Programação errada",
    48: "Avaria interna",
}


def vag_to_pcode(code):
    """Converte um código VAG de 5 dígitos para P-code OBD-II (quando aplicável)."""
    if 16384 <= code <= 17383:
        return f"P0{code - 16384:03d}"
    if 17408 <= code <= 18407:
        return f"P1{code - 17408:03d}"
    return ""


def dtc_description(code):
    if code in VAG_DTC:
        return VAG_DTC[code]
    p = vag_to_pcode(code)
    if p:
        return f"{p} — {PCODE_DESC.get(p, 'código OBD-II (ver manual)')}"
    return "Descrição não disponível na base de dados"


def decode_fault(code, status):
    elab = status & 0x7F
    return {
        "code": code,
        "vag": f"{code:05d}",
        "pcode": vag_to_pcode(code),
        "desc": dtc_description(code),
        "elab_code": elab,
        "elab": FAULT_ELABORATION.get(elab, f"Tipo {elab:02d}"),
        "intermittent": bool(status & 0x80),
        "status": status,
    }


# --------------------------------------------------------- valores de medição
def _ascii(*vals):
    return "".join(chr(v) if 0x20 <= v < 0x7F else "." for v in vals)


FORMULAS = {
    1: lambda a, b: (a * b / 5, "/min"),
    2: lambda a, b: (a * 0.002 * b, "%"),
    3: lambda a, b: (a * 0.002 * b, "°"),
    4: lambda a, b: (abs(b - 127) * 0.01 * a, "° APMS" if b > 127 else "° AAPMS"),
    5: lambda a, b: (a * (b - 100) * 0.1, "°C"),
    6: lambda a, b: (0.001 * a * b, "V"),
    7: lambda a, b: (0.01 * a * b, "km/h"),
    8: lambda a, b: (0.1 * a * b, ""),
    9: lambda a, b: ((b - 127) * 0.02 * a, "°"),
    10: lambda a, b: ("QUENTE" if b else "FRIO", ""),
    11: lambda a, b: (0.0001 * a * (b - 128) + 1, ""),
    12: lambda a, b: (0.001 * a * b, "Ω"),
    13: lambda a, b: ((b - 127) * 0.001 * a, "mm"),
    14: lambda a, b: (0.005 * a * b, "bar"),
    15: lambda a, b: (0.01 * a * b, "ms"),
    16: lambda a, b: (format(a & b, "08b"), "bin"),
    17: lambda a, b: (_ascii(a, b), ""),
    18: lambda a, b: (0.04 * a * b, "mbar"),
    19: lambda a, b: (a * b * 0.01, "l"),
    20: lambda a, b: (a * (b - 128) / 128, "%"),
    21: lambda a, b: (0.001 * a * b, "V"),
    22: lambda a, b: (0.001 * a * b, "ms"),
    23: lambda a, b: (b / 256 * a, "%"),
    24: lambda a, b: (0.001 * a * b, "A"),
    25: lambda a, b: (b * 1.421 + a / 182, "g/s"),
    26: lambda a, b: (b - a, "°C"),
    27: lambda a, b: (abs(b - 128) * 0.01 * a, "° APMS" if b > 128 else "° AAPMS"),
    28: lambda a, b: (b - a, ""),
    29: lambda a, b: ("1º mapa" if b < a else "2º mapa", ""),
    30: lambda a, b: (b / 12 * a, "° KW"),
    31: lambda a, b: (b / 2560 * a, "°C"),
    32: lambda a, b: (b - 256 if b > 128 else b, ""),
    33: lambda a, b: (100 * b / a if a else 100 * b, "%"),
    34: lambda a, b: ((b - 128) * 0.01 * a, "kW"),
    35: lambda a, b: (0.01 * a * b, "l/h"),
    36: lambda a, b: (a * 2560 + b * 10, "km"),
    37: lambda a, b: (f"{b}", "(estado)"),
    38: lambda a, b: ((b - 128) * 0.001 * a, "° KW"),
    39: lambda a, b: (b / 256 * a, "mg/H"),
    40: lambda a, b: (b * 0.1 + 25.5 * a - 400, "A"),
    41: lambda a, b: (b + a * 255, "Ah"),
    42: lambda a, b: (b * 0.1 + 25.5 * a - 400, "kW"),
    43: lambda a, b: (b * 0.1 + 25.5 * a, "V"),
    44: lambda a, b: (f"{a:02d}:{b:02d}", "h"),
    45: lambda a, b: (0.1 * a * b / 100, ""),
    46: lambda a, b: ((a * b - 3200) * 0.0027, "° KW"),
    47: lambda a, b: ((b - 128) * a, "ms"),
    48: lambda a, b: (b + a * 255, ""),
    49: lambda a, b: (b / 4 * a * 0.1, "mg/H"),
    50: lambda a, b: ((b - 128) / (0.01 * a) if a else 0, "mbar"),
    51: lambda a, b: ((b - 128) / 255 * a, "mg/H"),
    52: lambda a, b: (b * 0.02 * a - a, "Nm"),
    53: lambda a, b: ((b - 128) * 1.4222 + 0.006 * a, "g/s"),
    54: lambda a, b: (a * 256 + b, ""),
    55: lambda a, b: (a * b / 200, "s"),
    56: lambda a, b: (a * 256 + b, "WSC"),
    57: lambda a, b: (a * 256 + b + 65536, "WSC"),
    58: lambda a, b: (1.0225 * (256 - b) if b > 128 else 1.0225 * b, "/s"),
    59: lambda a, b: ((a * 256 + b) / 32768, ""),
    60: lambda a, b: ((a * 256 + b) * 0.01, "s"),
    61: lambda a, b: ((b - 128) / a if a else 0, ""),
    62: lambda a, b: (0.256 * a * b, "S"),
    63: lambda a, b: (_ascii(a, b) + "?", ""),
    64: lambda a, b: (a + b, "Ω"),
    65: lambda a, b: (0.01 * a * (b - 127), "mm"),
    66: lambda a, b: (a * b / 511.12, "V"),
    67: lambda a, b: (640 * a + b * 2.5, "°"),
    68: lambda a, b: ((256 * a + b) / 7.365, "°/s"),
    69: lambda a, b: ((256 * a + b) * 0.3254, "bar"),
    70: lambda a, b: ((256 * a + b) * 0.192, "m/s²"),
}


def format_number(v):
    if isinstance(v, str):
        return v
    v = float(v)
    if v == int(v) and abs(v) < 1e9:
        return str(int(v))
    av = abs(v)
    if av >= 100:
        return f"{v:.1f}"
    if av >= 10:
        return f"{v:.2f}"
    return f"{v:.3f}"


def decode_value(formula, a, b):
    fn = FORMULAS.get(formula)
    if fn is None:
        return {"value": f"{a}/{b}", "unit": f"(fórm. {formula})", "formula": formula,
                "a": a, "b": b, "numeric": None}
    try:
        val, unit = fn(a, b)
    except Exception:
        return {"value": "?", "unit": "", "formula": formula, "a": a, "b": b, "numeric": None}
    numeric = None if isinstance(val, str) else float(val)
    return {"value": format_number(val), "unit": unit, "formula": formula,
            "a": a, "b": b, "numeric": numeric}


def decode_triplets(data):
    """Decodifica um bloco de medição: sequência de (fórmula, a, b)."""
    fields = []
    for i in range(0, len(data) - 2, 3):
        fields.append(decode_value(data[i], data[i + 1], data[i + 2]))
    return fields[:4]
