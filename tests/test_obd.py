"""OBD-II/EOBD, ISO-TP e UDS: normas, adaptador ELM327 simulado, CAN cru simulado e sessão completa.

Nada aqui precisa de hardware nem de Qt. Os valores de referência das fórmulas e códigos são os exemplos
publicados para SAE J1979 / J2012; o veículo simulado é fictício (VIN RADSML…)."""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad.errors import InterfaceError, NoResponse, OperationUnconfirmed, ProtocolError  # noqa: E402
from rad.obd import dtc, isotp, pids  # noqa: E402
from rad.obd.elm327 import AdapterNotResponding, ELM_SIM_PORT, Elm327Link  # noqa: E402
from rad.obd.j1979 import Obd2, valid_vin  # noqa: E402
from rad.obd.link import NegativeResponse  # noqa: E402
from rad.obd.session import ObdSession, request_id  # noqa: E402
from rad.obd.sim_elm import SimElm327Serial  # noqa: E402
from rad.obd.simvehicle import SIM_VIN, SimCanBus, SimVehicle  # noqa: E402
from rad.obd.uds import UdsClient  # noqa: E402


def _elm(vehicle=None, **kw):
    sim = SimElm327Serial(vehicle or SimVehicle(), **kw)
    link = Elm327Link(ELM_SIM_PORT, serial_factory=lambda port, baud: sim, timeout=1.0, search_timeout=1.0)
    return link, sim


# ------------------------------------------------------------------ normas
def test_dtc_decode_encode():
    assert dtc.decode(0x01, 0x33) == "P0133"
    assert dtc.decode(0xC1, 0x00) == "U0100"
    assert dtc.decode(0x41, 0x23) == "C0123"
    assert dtc.decode(0x92, 0x34) == "B1234"
    assert dtc.decode(0x20, 0x02) == "P2002"
    for code in ("P0133", "U0100", "C0123", "B1234", "P2002", "P3400", "U3FFF"):
        assert dtc.decode(*dtc.encode(code)) == code
    assert dtc.is_generic("P0301") and dtc.is_generic("P2002") and not dtc.is_generic("P1136")
    assert not dtc.is_generic("U1100") and dtc.is_generic("U0100")


def test_dtc_description_is_never_invented():
    d = dtc.describe("P0301")
    assert d["desc"] and "cilindro 1" in d["desc"] and d["source"]
    unknown = dtc.describe("P1136")            # código do fabricante: sem base instalada não há texto
    assert unknown["desc"] is None and unknown["source"] is None
    assert "fabricante" in unknown["category"]
    assert "ignição" in dtc.describe("P0399")["category"]      # estrutura P03xx, mesmo sem descrição


def test_dtc_database_needs_declared_source(tmp=None):
    import json
    import tempfile
    folder = tempfile.mkdtemp()
    p = os.path.join(folder, "db.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"_source": "teste", "P1136": "Mistura pobre (teste)", "XYZ": "inválido"}, fh)
    assert dtc.load_database(p, "teste", "Base de teste") == 1
    d = dtc.describe("P1136")
    assert d["desc"] == "Mistura pobre (teste)" and d["source"] == "Base de teste"
    dtc._extra_db.pop("P1136", None)


def test_pid_formulas():
    assert pids.TABLE[0x0C].decode(bytes([0x1A, 0xF8])) == 1726           # (256·26 + 248) / 4
    assert pids.TABLE[0x05].decode(bytes([0x7B])) == 83
    assert pids.TABLE[0x10].decode(bytes([0x01, 0x90])) == 4.0
    assert pids.TABLE[0x06].decode(bytes([0x80])) == 0
    assert pids.TABLE[0x42].decode(bytes([0x30, 0xD4])) == 12.5
    assert pids.TABLE[0x51].decode(bytes([4])) == "Gasóleo"
    try:
        pids.TABLE[0x0C].decode(b"\x1A")
        raise AssertionError("resposta curta tem de falhar")
    except ValueError:
        pass


def test_supported_pid_bitmap():
    s = pids.bitmap_pids(0x00, bytes([0xBE, 0x1F, 0xA8, 0x13]))
    assert s == {0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x0C, 0x0D, 0x0E, 0x0F, 0x10, 0x11, 0x13, 0x15, 0x1C,
                 0x1F, 0x20}


def test_monitor_status():
    m = pids.decode_monitor_status(0x83, 0x07, 0x65, 0x00)
    assert m["mil"] and m["dtc_count"] == 3 and "gasolina" in m["ignition"]
    names = {x["name"]: x for x in m["monitors"]}
    assert names["Catalisador"]["supported"] and names["Catalisador"]["complete"]
    d = pids.decode_monitor_status(0x00, 0x08, 0x40, 0x40)
    assert not d["mil"] and "diesel" in d["ignition"]
    assert {x["name"]: x for x in d["monitors"]}["Filtro de partículas"] == \
        {"name": "Filtro de partículas", "supported": True, "complete": False, "continuous": False}


def test_vin_validation():
    assert valid_vin(SIM_VIN)
    assert not valid_vin("WVWZZZ1JZ3W38627I")     # I não é permitido
    assert not valid_vin("SHORT")


# ------------------------------------------------------------------ ISO-TP
def test_isotp_roundtrip():
    for n in (1, 7, 8, 13, 20, 100, 4095, 5000):
        msg = bytes(random.randrange(256) for _ in range(n))
        a = isotp.Reassembler()
        frames = isotp.segment(msg)
        out = None
        for f in frames:
            assert len(f) == 8
            out = a.feed(f)
        assert out == msg, n
    assert isotp.segment(b"\x01\x00")[0][:3] == b"\x02\x01\x00"


def test_isotp_errors():
    a = isotp.Reassembler()
    frames = isotp.segment(bytes(20))
    a.feed(frames[0])
    try:
        a.feed(frames[2])
        raise AssertionError("fora de sequência tem de falhar")
    except isotp.IsoTpError:
        pass
    for bad in (b"\x21\x00", b"\x00", b"\x05\x01", b"\x10\x05" + bytes(6), b"\x40"):
        try:
            isotp.Reassembler().feed(bad)
            raise AssertionError(bad)
        except isotp.IsoTpError:
            pass
    assert isotp.st_min_seconds(0x0A) == 0.01 and isotp.st_min_seconds(0xF5) == 0.0005


# ------------------------------------------------------------------ ELM327
def test_elm327_open_and_discover():
    link, sim = _elm()
    d = link.open()
    assert d["version"] == "ELM327 v1.5" and d["simulated"] and d["voltage"] == 12.4
    assert "ATH1" in sim.commands and "ATE0" in sim.commands
    link.connect_vehicle()
    assert link.proto == "6" and link.is_can and "CAN" in link.protocol
    obd = Obd2(link)
    sup = obd.discover()
    assert list(sup) == ["7E8", "7E9"]
    assert 0x0C in sup["7E8"] and 0x0C not in sup["7E9"]
    assert obd.primary_ecu() == "7E8"


def test_elm327_vin_multiframe_and_values():
    link, _ = _elm()
    link.open()
    link.connect_vehicle()
    obd = Obd2(link)
    obd.discover()
    assert obd.vin() == (SIM_VIN, "7E8")
    names = obd.ecu_names()
    assert names["7E8"] == "ECM-EngineControl"
    vals = obd.read_pids([0x05, 0x0C, 0x42, 0x0A, 0xFE])
    assert vals[0x42]["value"] == 12.4 and vals[0x42]["unit"] == "V"
    assert vals[0x0C]["value"] == 0                       # motor parado
    assert "não suportado" in vals[0x0A]["error"]         # o motor simulado não declara o PID 0A
    assert "sem definição" in vals[0xFE]["error"]


def test_elm327_dtcs_and_clear():
    v = SimVehicle(engine_running=True)
    link, _ = _elm(v)
    link.open()
    link.connect_vehicle()
    obd = Obd2(link)
    obd.discover()
    assert obd.read_dtcs("stored") == {"7E8": ["P0401", "P2002"], "7E9": []}
    assert obd.read_dtcs("pending")["7E8"] == ["P0299"]
    assert obd.read_dtcs("permanent")["7E8"] == ["P2002"]
    try:
        obd.clear_dtcs()                                  # motor a trabalhar → recusa (NRC 22)
        raise AssertionError("tinha de recusar")
    except NegativeResponse as e:
        assert e.nrc == 0x22 and "condições" in str(e)
    v.engine_running = False
    assert set(obd.clear_dtcs()) == {"7E8", "7E9"}
    assert obd.read_dtcs("stored")["7E8"] == []
    assert obd.read_dtcs("permanent")["7E8"] == ["P2002"]  # permanentes não se apagam pelo modo 04


def test_elm327_ignition_off_is_not_connected():
    link, _ = _elm(SimVehicle(ignition=False))
    link.open()                                           # o adaptador funciona…
    try:
        link.connect_vehicle()                            # …mas o carro não responde
        raise AssertionError("sem ignição não pode ligar")
    except NoResponse as e:
        assert "ignição" in str(e)
    assert link.proto is None


def test_port_that_is_not_an_elm327():
    sim = SimElm327Serial(mute=True)
    link = Elm327Link("COM7", serial_factory=lambda port, baud: sim, timeout=0.3)
    import rad.obd.elm327 as m
    old = m.BAUDS
    m.BAUDS = (38400,)
    try:
        link.open()
        raise AssertionError("um dispositivo que não responde não é um ELM327")
    except AdapterNotResponding as e:
        assert "nenhum adaptador ELM327 respondeu" in str(e)
        assert isinstance(e, InterfaceError)
    finally:
        m.BAUDS = old


def test_adapter_stops_answering_midway():
    link, sim = _elm()
    link.open()
    link.connect_vehicle()
    sim.die_after = 0
    try:
        link.request(b"\x01\x0C")
        raise AssertionError("tinha de falhar")
    except InterfaceError as e:
        assert "deixou de responder" in str(e)


def test_elm327_baud_detection():
    sim = SimElm327Serial(baud=9600)
    link = Elm327Link("COM9", serial_factory=lambda port, baud: sim, timeout=0.5)
    orig_close = sim.close
    sim.close = lambda: None                              # a mesma porta é reaberta a outra velocidade
    link.open()
    assert link.baud == 9600
    sim.close = orig_close


def test_elm327_parser_non_can_with_checksum():
    link = Elm327Link("X", serial_factory=lambda p, b: None)
    link.proto = "3"
    body = [0x48, 0x6B, 0x10, 0x41, 0x0C, 0x1A, 0xF8]
    line = " ".join(f"{b:02X}" for b in body + [sum(body) & 0xFF])
    bad = " ".join(f"{b:02X}" for b in body + [0x00])
    r = link._parse([line, bad, "SEARCHING...", "BUS INIT: ...OK"])
    assert len(r) == 1 and r[0].ecu == "10" and r[0].data == bytes([0x41, 0x0C, 0x1A, 0xF8])


def test_elm327_parser_no_spaces_and_29bit():
    link = Elm327Link("X", serial_factory=lambda p, b: None)
    link.proto = "6"
    r = link._parse(["7E8064100BE3FA813"])
    assert r[0].ecu == "7E8" and r[0].data.hex() == "4100be3fa813"
    link.proto = "7"
    r = link._parse(["18 DA F1 10 06 41 00 BE 3F A8 13"])
    assert r[0].ecu == "18DAF110" and r[0].data[0] == 0x41


def test_elm327_parser_fuzz():
    link = Elm327Link("X", serial_factory=lambda p, b: None)
    rnd = random.Random(7)
    for proto in ("3", "5", "6", "7"):
        link.proto = proto
        for _ in range(400):
            n = rnd.randrange(0, 14)
            line = " ".join(f"{rnd.randrange(256):02X}" for _ in range(n))
            link._parse([line, "7E8 " + line])            # nunca rebenta: ignora ou interpreta


# ------------------------------------------------------------------ CAN cru + ISO-TP
def test_isotp_link_over_raw_can():
    bus = SimCanBus()
    link = isotp.IsoTpLink(bus, p2=0.02)
    obd = Obd2(link)
    sup = obd.discover()
    assert set(sup) == {"7E8", "7E9"}
    assert obd.vin() == (SIM_VIN, "7E8")                  # multi-trama: FF → Flow Control → CFs
    fc = [d for arb, d in bus.sent if d[0] >> 4 == 3]
    assert fc and all(arb == 0x7E0 for arb, d in bus.sent if d[0] >> 4 == 3)


def test_uds_over_raw_can_with_pending_response():
    bus = SimCanBus()
    bus.vehicle.engine.pending_once.add(0x22)             # 1.ª resposta: 7F 22 78 (pendente)
    u = UdsClient(isotp.IsoTpLink(bus, p2=0.02), "7E0")
    assert u.read_did(0xF190).decode() == SIM_VIN
    ident = u.identification()
    assert ident[0xF190]["value"] == SIM_VIN and 0xF191 not in ident   # F191 não existe → fica de fora
    dt = u.read_dtcs()
    codes = {d["code"]: d for d in dt}
    assert set(codes) == {"P0401", "P2002", "P0299"}
    assert codes["P0401"]["ftb_text"] == "circuito aberto" and "confirmada (memorizada)" in codes["P0401"]["status_text"]
    assert u.dtc_count() == 3
    try:
        u.session(0x02)
        raise AssertionError("a sessão de programação nunca é pedida")
    except ValueError:
        pass


def test_multiframe_request_to_ecu():
    """Pedido UDS com vários identificadores (> 7 bytes): o testador envia FF e espera o Flow Control."""
    bus = SimCanBus()
    link = isotp.IsoTpLink(bus, p2=0.02)
    r = link.request(bytes([0x22, 0xF1, 0x90, 0xF1, 0x87, 0xF1, 0x89, 0xF1, 0x8C]), target="7E0")
    assert r[0].data[0] == 0x62 and SIM_VIN.encode() in r[0].data


def test_raw_can_transport_failures():
    for kw in ({"drop_flow_control": True}, {"corrupt_sequence": True}):
        link = isotp.IsoTpLink(SimCanBus(**kw), p2=0.02, n_cr=0.05)
        try:
            link.request(b"\x09\x02")
            raise AssertionError(kw)
        except NoResponse:
            pass
    bus = SimCanBus(SimVehicle(ignition=False))
    try:
        isotp.IsoTpLink(bus, p2=0.02).request(b"\x01\x00")
        raise AssertionError("sem ignição")
    except NoResponse:
        pass
    bus = SimCanBus()
    bus.close()
    try:
        isotp.IsoTpLink(bus).request(b"\x01\x00")
        raise AssertionError("interface fechada")
    except InterfaceError:
        pass


# ------------------------------------------------------------------ sessão completa
def test_obd_session_connect_steps_and_info():
    link, _ = _elm()
    s = ObdSession(link)
    info = s.connect()
    names = [st[0] for st in info["steps"]]
    assert names[:4] == ["Abrir a interface", "Adaptador respondeu", "Tensão na ficha OBD", "Protocolo do veículo"]
    assert all(st[1] for st in info["steps"])
    assert info["vin"] == SIM_VIN and info["mil"] and info["dtc_count"] == 2 and info["simulated"]
    assert info["ecus"][0]["label"] == "ECM-EngineControl (7E8)" and info["ecus"][0]["uds_target"] == "7E0"
    assert 0x0C in s.live_pids() and 0x51 not in s.live_pids()


def test_obd_session_failures_are_located():
    link, _ = _elm(SimVehicle(ignition=False))
    s = ObdSession(link)
    try:
        s.connect()
        raise AssertionError
    except NoResponse:
        pass
    assert s.steps[1] == ("Adaptador respondeu", True, "ELM327 v1.5 a 38400 baud — simulação")
    assert s.steps[-1][0] == "Comunicação com o veículo" and not s.steps[-1][1]
    assert not s.connected
    v = SimVehicle()
    v.battery = 10.9
    s = ObdSession(_elm(v)[0])
    s.connect()
    volt = [st for st in s.steps if st[0] == "Tensão na ficha OBD"][0]
    assert not volt[1] and "10.9 V" in volt[2]


def test_obd_session_dtcs_clear_and_report_items():
    v = SimVehicle()
    s = ObdSession(_elm(v)[0])
    s.connect()
    d = s.read_dtcs()
    assert [f["code"] for f in d["stored"]] == ["P0401", "P2002"]
    assert d["pending"][0]["kind"] == "pendente" and d["permanent"][0]["code"] == "P2002"
    items = s.report_items(d)
    eng = [i for i in items if i["address"] == 0x7E8][0]
    codes = [f["vag"] for f in eng["faults"]]
    assert codes == ["P0401", "P2002", "P0299"]           # o permanente P2002 não aparece duas vezes
    assert eng["info"]["simulated"] is True
    from rad import report
    html = report.build_html({}, {"plate": "TESTE"}, items, meta={"simulated": True})
    assert "DADOS SIMULADOS" in html and "P0401" in html and "7E8" in html
    r = s.clear_dtcs()
    assert set(r["confirmed_by"]) == {"7E8", "7E9"} and r["after"]["stored"] == []
    assert r["info"]["mil"] is False


def test_obd_session_clear_unconfirmed():
    link, sim = _elm()
    s = ObdSession(link)
    s.connect()

    real = s.obd.read_dtcs

    def broken(kind="stored"):
        raise ProtocolError("ligação perdida")
    s.obd.read_dtcs = broken
    try:
        s.clear_dtcs()
        raise AssertionError
    except OperationUnconfirmed as e:
        assert "aceite" in str(e)
    s.obd.read_dtcs = real


def test_obd_session_uds_info():
    s = ObdSession(_elm()[0])
    s.connect()
    r = s.uds_info("7E0")
    assert r["ident"][0xF190]["value"] == SIM_VIN
    assert {d["code"] for d in r["dtcs"]} == {"P0401", "P2002", "P0299"}
    assert request_id("7E9") == "7E1" and request_id("10") is None


def test_freeze_frame():
    s = ObdSession(_elm()[0])
    s.connect()
    ff = s.freeze_frame()
    assert ff["dtc"] == "P0401" and ff["values"][0x0C]["value"] == 1850 and ff["values"][0x05]["value"] == 86


def test_vag_advice_is_not_applied_to_multibrand_faults():
    from rad import fault_advice
    vag = fault_advice.advice({"vag": "P0401", "pcode": "P0401"})
    obd = fault_advice.advice({"vag": "P0401", "pcode": "P0401", "obd_kind": "stored"}, 0x7E8)
    assert obd["severity"] == "na" and not obd["causes"] and not obd["checks"]
    assert "Motor" in obd["system"] and vag["severity"] != "na"
    from rad import report
    s = ObdSession(_elm()[0])
    s.connect()
    html = report.build_html({}, {}, s.report_items(s.read_dtcs()), meta={"simulated": True})
    assert "N18" not in html and "Gravidade não avaliada".lower() in html
