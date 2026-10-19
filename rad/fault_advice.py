"""Assistente de diagnóstico: para cada avaria, a gravidade, as causas mais prováveis e o que verificar.

São indicações habituais de oficina para os VAG com linha K (até ~2005). Servem para orientar o
técnico — não substituem a medição nem a documentação do fabricante. Sem Qt: usado na UI, no
relatório e nos testes."""
import re
import unicodedata

from . import vag_data

SEVERITY_TEXT = {"alta": "Gravidade alta", "media": "Gravidade média", "baixa": "Gravidade baixa"}

# --------------------------------------------------------------- por código
_ABS_SENSOR = {
    "system": "Travões / ABS", "severity": "alta",
    "causes": ["Sensor de velocidade sujo ou com folga (limalha no íman)",
               "Anel/roda fónica partida, oxidada ou com dentes em falta",
               "Cablagem do sensor danificada junto à roda (zona de movimento)",
               "Folga excessiva no rolamento da roda"],
    "checks": ["Valores de medição grupo 001: comparar a velocidade das 4 rodas a andar devagar",
               "Medir a resistência do sensor (indutivo ~1–2 kΩ) e o isolamento à massa",
               "Inspeccionar a roda fónica com a roda levantada, a rodar à mão"],
}
_AIRBAG_SQUIB = {
    "system": "Airbags", "severity": "alta",
    "causes": ["Ficha do airbag/pré-tensor mal encaixada (muito comum debaixo dos bancos)",
               "Fita espiral do volante (contacto rotativo) partida",
               "Resistência do circuito fora de gama por mau contacto"],
    "checks": ["Ignição DESLIGADA e bateria desligada antes de mexer em fichas de airbag",
               "Verificar fichas amarelas debaixo dos bancos e no volante",
               "Testar com resistência de simulação (~2–3 Ω) no lugar do detonador — nunca medir o airbag com multímetro"],
}
_IMMO = {
    "system": "Imobilizador", "severity": "alta",
    "causes": ["Chave não adaptada a este carro ou transponder danificado",
               "Bobina de leitura (D2) no canhão de ignição avariada",
               "Unidade de comando do motor substituída sem adaptação ao imobilizador"],
    "checks": ["Experimentar a chave suplente",
               "Valores de medição do painel (17) grupo 081/022: estado do imobilizador e da chave",
               "Adaptação de chaves / motor exige PIN (login) e o procedimento do fabricante"],
}
_INJECTOR = {
    "system": "Injecção", "severity": "media",
    "causes": ["Ficha ou cablagem do injector com mau contacto/oxidação",
               "Bobina do injector em curto ou interrompida",
               "Injector com débito fora de tolerância (desgaste)"],
    "checks": ["Medir a resistência da bobina do injector e comparar com os outros cilindros",
               "Teste guiado 'Equilíbrio dos injectores' (grupo 013) em motores TDI",
               "Verificar a cablagem entre a unidade de comando e o injector"],
}
_SUPPLY = {
    "system": "Alimentação eléctrica", "severity": "media",
    "causes": ["Bateria fraca ou descarregada (tensão baixa no arranque)",
               "Alternador/regulador com carga insuficiente",
               "Massa ou positivo da unidade de comando com mau contacto",
               "Arranques com cabos de bateria ou bateria desligada recentemente"],
    "checks": ["Medir a tensão da bateria em repouso (~12,6 V) e com motor a trabalhar (13,8–14,5 V)",
               "Teste de carga à bateria",
               "Limpar e apertar terminais da bateria e as massas motor-carroçaria"],
}
_ECU_COMM = {
    "system": "Comunicação entre unidades", "severity": "media",
    "causes": ["Unidade de comando referida sem alimentação ou sem massa",
               "Cablagem do barramento (CAN ou linha K) danificada ou com humidade",
               "Codificação errada (unidade espera um módulo que o carro não tem)"],
    "checks": ["Verificar fusíveis e alimentação da unidade indicada",
               "Ligar a essa unidade com o programa: se não responder, o problema está nela ou na cablagem",
               "Confirmar a codificação do gateway / painel"],
}

SPECIFIC = {
    532: _SUPPLY,
    668: _SUPPLY,
    283: _ABS_SENSOR, 285: _ABS_SENSOR, 287: _ABS_SENSOR, 290: _ABS_SENSOR,
    301: {"system": "Travões / ABS", "severity": "alta",
          "causes": ["Motor da bomba de retorno gripado ou com escovas gastas",
                     "Fusível/relé da bomba ABS", "Massa da unidade ABS com mau contacto"],
          "checks": ["Verificar fusível grande da bomba ABS", "Teste de saídas no ABS (03)",
                     "Medir alimentação e massa na ficha da unidade hidráulica"]},
    1276: {"system": "Travões / ABS", "severity": "alta",
           "causes": ["Bomba hidráulica sem alimentação (fusível/relé)", "Motor da bomba avariado",
                      "Mau contacto na ficha da unidade hidráulica"],
           "checks": ["Verificar fusíveis do ABS", "Teste de saídas no ABS (03)"]},
    1130: {"system": "Travões / ABS", "severity": "alta",
           "causes": ["Consequência de outra avaria do ABS (sensor, bomba)", "Tensão de alimentação baixa"],
           "checks": ["Resolver primeiro as outras avarias do ABS", "Verificar a tensão da bateria"]},
    513: {"system": "Motor", "severity": "alta",
          "causes": ["Sensor de rotação (G28) avariado ou sujo", "Folga/distância ao volante do motor incorrecta",
                     "Cablagem do sensor danificada (zona quente)"],
          "checks": ["Valores de medição grupo 001: rotação ao arranque (deve aparecer > 0)",
                     "Medir a resistência do G28 (~1 kΩ em muitos motores)",
                     "Motor pode não pegar ou ir abaixo — verificar antes de mais nada"]},
    515: {"system": "Motor", "severity": "media",
          "causes": ["Sensor Hall (G40) avariado", "Correia de distribuição saltou um dente",
                     "Cablagem do sensor"],
          "checks": ["Confirmar a sincronização da distribuição", "Verificar alimentação 5 V do sensor"]},
    518: {"system": "Admissão", "severity": "media",
          "causes": ["Potenciómetro da borboleta gasto", "Corpo de borboleta sujo",
                     "Falta de ajuste básico depois de limpeza ou desmontagem"],
          "checks": ["Ajuste básico do corpo de borboleta (grupo 060 ou 098 conforme o motor)",
                     "Limpar o corpo de borboleta", "Valores de medição: ângulo da borboleta sem acelerar"]},
    522: {"system": "Arrefecimento", "severity": "media",
          "causes": ["Sensor de temperatura (G62) avariado — muito comum", "Ficha oxidada",
                     "Nível de líquido baixo (sensor no ar)"],
          "checks": ["Comparar a temperatura no grupo 001/004 com a temperatura real do motor frio",
                     "Verificar o nível de líquido de refrigeração", "Substituir o vedante/clip ao trocar o sensor"]},
    523: {"system": "Admissão", "severity": "baixa",
          "causes": ["Sensor de temperatura do ar avariado", "Ficha do sensor desligada ou oxidada"],
          "checks": ["Com o motor frio, a temperatura do ar deve ser próxima da ambiente"]},
    524: {"system": "Ignição", "severity": "media",
          "causes": ["Sensor de detonação com binário de aperto errado", "Ficha do sensor oxidada",
                     "Combustível de baixa qualidade"],
          "checks": ["Apertar o sensor com o binário correcto (normalmente 20 Nm)",
                     "Valores de medição: atraso de ignição por cilindro"]},
    525: {"system": "Emissões", "severity": "media",
          "causes": ["Sonda lambda envelhecida ou contaminada", "Aquecimento da sonda avariado",
                     "Fuga no escape antes da sonda"],
          "checks": ["Valores de medição: tensão da sonda deve oscilar 0,1–0,9 V ao ralenti quente",
                     "Verificar fugas no colector de escape"]},
    537: {"system": "Emissões", "severity": "media",
          "causes": ["Entrada de ar falso na admissão", "Sonda lambda lenta", "Pressão de combustível incorrecta"],
          "checks": ["Procurar fugas de vácuo (tubos, juntas)", "Verificar a pressão de combustível"]},
    543: {"system": "Motor", "severity": "baixa",
          "causes": ["Rotação máxima ultrapassada (redução de mudança, condução)",
                     "Raramente: sinal de rotação com interferência"],
          "checks": ["Normalmente basta apagar; se voltar sem motivo, verificar o sensor de rotação"]},
    553: {"system": "Admissão", "severity": "media",
          "causes": ["Medidor de massa de ar (G70) sujo ou avariado — muito comum", "Fuga na admissão depois do medidor",
                     "Filtro de ar muito sujo"],
          "checks": ["Valores de medição grupo 003: massa de ar real vs pretendida",
                     "Desligar a ficha do medidor e comparar o comportamento do motor",
                     "Verificar tubos da admissão e intercooler"]},
    561: {"system": "Mistura", "severity": "media",
          "causes": ["Entrada de ar falso", "Injectores sujos", "Pressão de combustível baixa",
                     "Medidor de massa de ar desviado"],
          "checks": ["Valores de medição: correcções de mistura (adaptações) ao ralenti e em carga",
                     "Teste de fumo à admissão"]},
    575: {"system": "Turbo / admissão", "severity": "media",
          "causes": ["Sensor de pressão do colector (MAP) avariado", "Fugas no circuito do turbo"],
          "checks": ["Com o motor parado, a pressão deve ser igual à atmosférica (~1000 mbar)"]},
    588: _AIRBAG_SQUIB, 589: _AIRBAG_SQUIB, 1217: _AIRBAG_SQUIB, 1218: _AIRBAG_SQUIB,
    595: {"system": "Airbags", "severity": "alta",
          "causes": ["O carro registou uma colisão com disparo — a unidade de airbag tem de ser substituída"],
          "checks": ["Inspecção completa do sistema de retenção (airbags, pré-tensores, unidade J234)",
                     "Esta avaria não se apaga"]},
    626: {"system": "Pré-aquecimento", "severity": "baixa",
          "causes": ["Lâmpada/LED do painel ou cablagem até ao painel"],
          "checks": ["Teste de saídas no motor (01)", "Verificar a ficha do painel de instrumentos"]},
    771: {"system": "Combustível", "severity": "baixa",
          "causes": ["Bóia do depósito com o potenciómetro gasto", "Ficha da bomba/sensor no depósito"],
          "checks": ["Valores de medição do painel (17): nível de combustível e resistência"]},
    777: {"system": "Admissão", "severity": "alta",
          "causes": ["Potenciómetro do pedal do acelerador gasto", "Ficha do pedal com mau contacto"],
          "checks": ["Valores de medição: percentagem do pedal deve variar suavemente 0–100 %",
                     "Motor pode entrar em modo de emergência (ralenti elevado)"]},
    779: {"system": "Conforto", "severity": "baixa",
          "causes": ["Sensor de temperatura exterior (para-choques) partido ou com humidade"],
          "checks": ["Comparar a leitura com a temperatura real"]},
    849: {"system": "Ignição / canhão", "severity": "baixa",
          "causes": ["Contacto S do canhão de ignição gasto", "Chave a ser retirada sem rodar completamente"],
          "checks": ["Verificar o estado do contacto S nos valores de medição do painel"]},
    955: _IMMO, 956: _IMMO, 1128: _IMMO, 1176: _IMMO, 1177: _IMMO, 1179: _IMMO,
    1042: {"system": "Codificação", "severity": "media",
           "causes": ["Unidade de comando nova ou substituída ainda sem codificação"],
           "checks": ["Codificar a unidade de acordo com o equipamento do carro (separador Codificação)"]},
    1044: {"system": "Codificação", "severity": "media",
           "causes": ["Codificação não corresponde ao equipamento do carro",
                      "Outra unidade foi substituída e a codificação ficou desactualizada"],
           "checks": ["Anotar a codificação actual antes de mexer", "Confirmar o equipamento e corrigir a codificação"]},
    1087: {"system": "Ajuste básico", "severity": "media",
           "causes": ["Bateria desligada ou componente substituído sem ajuste básico"],
           "checks": ["Executar o ajuste básico (separador Ajustes básicos, grupo indicado no manual)"]},
    1247: {"system": "Turbo", "severity": "media",
           "causes": ["Electroválvula N75 avariada ou com membrana rota", "Tubos de vácuo rachados ou trocados",
                      "Ficha da N75 oxidada / cablagem cortada"],
           "checks": ["Medir a resistência da N75 (~14–20 Ω em muitos TDI)",
                      "Teste de saídas: deve ouvir-se o clique da válvula",
                      "Teste guiado 'Pressão do turbo' (grupo 011) a acelerar em 3.ª"]},
    1249: _INJECTOR, 1250: _INJECTOR, 1251: _INJECTOR, 1252: _INJECTOR,
    1257: {"system": "Ralenti", "severity": "media",
           "causes": ["Válvula de ralenti suja ou presa", "Cablagem da válvula"],
           "checks": ["Limpar a válvula / corpo de borboleta", "Teste de saídas"]},
    1259: {"system": "Combustível", "severity": "media",
           "causes": ["Relé da bomba de combustível com soldaduras fissuradas (muito comum)",
                      "Contactos do porta-relés oxidados"],
           "checks": ["Teste de saídas no motor (01): ouvir o relé", "Trocar o relé por um igual e testar"]},
    1262: {"system": "Turbo", "severity": "media",
           "causes": ["Electroválvula de limitação da pressão avariada", "Tubos de vácuo"],
           "checks": ["Teste de saídas", "Verificar tubos de vácuo"]},
    1265: {"system": "EGR", "severity": "media",
           "causes": ["Válvula EGR presa com carvão", "Electroválvula N18 avariada", "Tubos de vácuo"],
           "checks": ["Valores de medição grupo 003: massa de ar real vs pretendida e ciclo EGR",
                      "Limpar a válvula EGR", "Teste de saídas no motor (01)"]},
    1268: {"system": "Injecção (bomba VE)", "severity": "alta",
           "causes": ["Regulador de quantidade (N146) na bomba injectora com desgaste",
                      "Sensor do pistão modulador (G149)", "Ficha da bomba injectora com fuga de gasóleo"],
           "checks": ["Valores de medição grupo 001 campo 3: tensão do pistão modulador",
                      "Inspeccionar a ficha da bomba (gasóleo dentro da ficha)"]},
    1269: {"system": "Injecção (bomba VE)", "severity": "media",
           "causes": ["Válvula de início de injecção (N108) avariada", "Avanço da bomba mal ajustado"],
           "checks": ["Valores de medição grupo 004: início de injecção pretendido vs real"]},
    1312: _ECU_COMM, 1314: _ECU_COMM, 1315: _ECU_COMM, 1316: _ECU_COMM, 1317: _ECU_COMM,
    1321: _ECU_COMM, 1299: _ECU_COMM,
    65535: {"system": "Unidade de comando", "severity": "alta",
            "causes": ["Avaria interna da unidade de comando", "Tensão de alimentação muito baixa durante a leitura"],
            "checks": ["Verificar alimentação e massas da unidade", "Apagar e voltar a ler; se regressar, unidade a reparar/substituir"]},
}

PCODE_ADVICE = {
    "P0101": SPECIFIC[553], "P0102": SPECIFIC[553], "P0103": SPECIFIC[553],
    "P0171": SPECIFIC[561], "P0172": SPECIFIC[561], "P1136": SPECIFIC[561], "P1137": SPECIFIC[561],
    "P0234": {"system": "Turbo", "severity": "media",
              "causes": ["Geometria variável do turbo presa (carvão)", "N75 avariada", "Sensor de pressão do turbo"],
              "checks": ["Grupo 011: pressão pretendida vs real em aceleração", "Verificar a haste de comando do turbo"]},
    "P0299": {"system": "Turbo", "severity": "media",
              "causes": ["Fuga no circuito de pressão (tubos, intercooler)", "Geometria do turbo presa",
                         "N75 ou tubos de vácuo"],
              "checks": ["Grupo 011 a acelerar em 3.ª", "Teste de fumo/pressão ao circuito de admissão"]},
    "P1555": {"system": "Turbo", "severity": "media", "causes": ["Sobrepressão — ver P0234"], "checks": []},
    "P1556": {"system": "Turbo", "severity": "media",
              "causes": ["Pressão abaixo da pretendida: fugas, N75, turbo gasto"], "checks": ["Grupo 011"]},
    "P1557": {"system": "Turbo", "severity": "media",
              "causes": ["Pressão acima da pretendida: geometria presa, N75"], "checks": ["Grupo 011"]},
    "P0300": {"system": "Ignição", "severity": "alta",
              "causes": ["Velas/bobinas gastas", "Injectores", "Entrada de ar falso", "Compressão baixa"],
              "checks": ["Valores de medição de falhas de ignição por cilindro", "Trocar bobinas entre cilindros e ver se a falha acompanha"]},
    "P0401": {"system": "EGR", "severity": "media", "causes": SPECIFIC[1265]["causes"],
              "checks": SPECIFIC[1265]["checks"]},
    "P0420": {"system": "Emissões", "severity": "media",
              "causes": ["Catalisador degradado", "Sonda lambda posterior a ler mal", "Fuga no escape"],
              "checks": ["Comparar o sinal das sondas antes e depois do catalisador"]},
    "P0562": _SUPPLY, "P0563": {"system": "Alimentação eléctrica", "severity": "media",
                                "causes": ["Regulador do alternador avariado (sobrecarga)"],
                                "checks": ["Medir a tensão com motor a 2000 rpm: não deve passar de ~14,8 V"]},
    "P0335": SPECIFIC[513], "P0340": SPECIFIC[515],
    "P0380": {"system": "Pré-aquecimento", "severity": "baixa",
              "causes": ["Vela de incandescência queimada", "Relé das velas", "Cablagem"],
              "checks": ["Medir a resistência de cada vela (< 2 Ω)", "Teste de saídas"]},
    "P1570": SPECIFIC[1177],
}
for _p in ("P0301", "P0302", "P0303", "P0304"):
    PCODE_ADVICE[_p] = PCODE_ADVICE["P0300"]
for _p in ("P0201", "P0202", "P0203", "P0204"):
    PCODE_ADVICE[_p] = _INJECTOR

# ------------------------------------------------ por tipo de avaria (elaboração)
ELAB_HINTS = {
    1: "Curto-circuito ao positivo: procure um fio descarnado a tocar em +12 V ou humidade na ficha.",
    28: "Curto-circuito ao positivo: procure um fio descarnado a tocar em +12 V ou humidade na ficha.",
    2: "Curto-circuito à massa: cablagem a tocar na carroçaria — verifique o isolamento ao longo do fio.",
    29: "Curto-circuito à massa: cablagem a tocar na carroçaria — verifique o isolamento ao longo do fio.",
    3: "Sem sinal: ficha desligada, fio cortado ou componente sem alimentação.",
    5: "Circuito aberto: meça a continuidade entre a unidade de comando e o componente; veja terminais oxidados.",
    26: "Circuito aberto: meça a continuidade entre a unidade de comando e o componente; veja terminais oxidados.",
    36: "Circuito aberto: meça a continuidade entre a unidade de comando e o componente; veja terminais oxidados.",
    6: "Sinal demasiado alto: sensor desligado (puxa para a alimentação) ou valor real fora de gama.",
    7: "Sinal demasiado baixo: curto à massa, alimentação do sensor em falta ou valor real fora de gama.",
    8: "Limite de regulação excedido: o sistema não consegue chegar ao valor pretendido (fugas, componente preso).",
    11: "Limite de regulação não atingido: o sistema não consegue chegar ao valor pretendido.",
    17: "Desvio de regulação: compare o valor pretendido com o real nos valores de medição.",
    9: "Limite de adaptação: a unidade já compensou o máximo que podia — procure a causa mecânica.",
    10: "Limite de adaptação: a unidade já compensou o máximo que podia — procure a causa mecânica.",
    16: "Sinal fora de especificação: compare com os valores de medição e com um componente de referência.",
    27: "Sinal não plausível: o valor não bate certo com outros sensores — sensor degradado ou mau contacto.",
    41: "Sinal não plausível: o valor não bate certo com outros sensores — sensor degradado ou mau contacto.",
    30: "Circuito aberto ou curto ao positivo: verifique a ficha e a cablagem do componente.",
    31: "Circuito aberto ou curto à massa: verifique a ficha e a cablagem do componente.",
    42: "Circuito aberto ou curto-circuito: verifique a ficha e a cablagem do componente.",
    32: "Resistência demasiado alta: mau contacto, terminal oxidado ou componente interrompido.",
    33: "Resistência demasiado baixa: componente em curto interno.",
    20: "Ajuste básico: execute o ajuste básico do componente depois de resolver a causa.",
    34: "Ajuste básico não efectuado: execute o ajuste básico do componente.",
    37: "Unidade de comando avariada: confirme alimentação e massas antes de a substituir.",
    39: "Sem comunicação: verifique alimentação, massa e barramento da unidade indicada.",
    44: "Bloqueado ou sem tensão: verifique a alimentação do componente e se está mecanicamente preso.",
    47: "Programação errada: confirme a codificação/adaptação da unidade.",
}

MODULE_SEVERITY = {0x03: "alta", 0x15: "alta", 0x25: "alta", 0x44: "alta", 0x01: "media",
                   0x02: "media", 0x17: "media", 0x19: "media", 0x22: "media"}

MODULE_SYSTEM = {0x01: "Motor", 0x02: "Caixa de velocidades", 0x03: "Travões / ABS", 0x08: "Climatização",
                 0x09: "Electrónica central", 0x15: "Airbags", 0x16: "Direcção", 0x17: "Painel de instrumentos",
                 0x19: "Rede de bordo", 0x22: "Tracção integral", 0x25: "Imobilizador", 0x35: "Fecho centralizado",
                 0x44: "Direcção assistida", 0x46: "Conforto", 0x55: "Iluminação", 0x56: "Rádio"}

_RANK = {"baixa": 0, "media": 1, "alta": 2}


def advice(fault, address=None):
    """fault: dicionário de vag_data.decode_fault (ou o guardado no histórico).
    Devolve {"severity", "severity_text", "system", "causes", "checks", "notes", "known"}."""
    code = fault.get("code")
    if code is None:
        try:
            code = int(fault.get("vag", ""))
        except (TypeError, ValueError):
            code = None
    entry = SPECIFIC.get(code) or PCODE_ADVICE.get(fault.get("pcode") or "")
    sev = entry["severity"] if entry else MODULE_SEVERITY.get(address, "baixa")
    if entry and address in MODULE_SEVERITY and _RANK[MODULE_SEVERITY[address]] > _RANK[sev]:
        sev = MODULE_SEVERITY[address]
    notes = []
    hint = ELAB_HINTS.get(fault.get("elab_code"))
    if hint:
        notes.append(hint)
    if fault.get("intermittent"):
        notes.append("Intermitente: a avaria não está presente neste momento. Apague e faça um teste de "
                     "estrada; se voltar, investigue as causas abaixo.")
    return {
        "severity": sev,
        "severity_text": SEVERITY_TEXT[sev],
        "system": entry["system"] if entry else MODULE_SYSTEM.get(address, "Geral"),
        "causes": list(entry["causes"]) if entry else [],
        "checks": list(entry["checks"]) if entry else [],
        "notes": notes,
        "known": bool(entry),
    }


def worst_severity(items):
    """Gravidade mais alta entre todas as avarias de uma lista de resultados do Auto-Scan."""
    best = None
    for it in items:
        for f in it.get("faults", []) if it.get("status") == "ok" else []:
            s = advice(f, it.get("address"))["severity"]
            if best is None or _RANK[s] > _RANK[best]:
                best = s
    return best


def _plain(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def lookup_code(text):
    """Interpreta '00532', '532', 'P0299' ou '16683' e devolve uma avaria (como decode_fault) ou None."""
    t = (text or "").strip().upper().replace(" ", "")
    m = re.fullmatch(r"P([01])(\d{3})", t)
    if m:
        code = (16384 if m.group(1) == "0" else 17408) + int(m.group(2))
        return vag_data.decode_fault(code, 0)
    if re.fullmatch(r"\d{3,5}", t):
        code = int(t)
        if code in vag_data.VAG_DTC or vag_data.vag_to_pcode(code):
            return vag_data.decode_fault(code, 0)
    return None


def search_codes(query, limit=8):
    """Procura avarias pelo texto da descrição (ex.: 'turbo', 'abs'). Devolve decode_fault()s."""
    q = _plain(query).strip()
    if len(q) < 3:
        return []
    words = q.split()
    out = []
    for code, desc in vag_data.VAG_DTC.items():
        if code in (0,):
            continue
        if all(w in _plain(desc) for w in words):
            out.append(vag_data.decode_fault(code, 0))
            if len(out) >= limit:
                return out
    for p, desc in vag_data.PCODE_DESC.items():
        if all(w in _plain(f"{p} {desc}") for w in words):
            f = lookup_code(p)
            if f:
                out.append(f)
            if len(out) >= limit:
                break
    return out
