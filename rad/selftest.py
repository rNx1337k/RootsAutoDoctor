"""Auto-teste da instalação (sem carro): RootsAutoDoctor.exe --selftest [ficheiro.txt]

Confirma que um PC acabado de instalar tem tudo o que as interfaces precisam: o Python portátil das pontes
(runtime/py32 e py64), a ponte J2534 e a ponte D2XX (com os simuladores) e, se o driver RT-USB da Ross-Tech
estiver instalado, que a ponte de 32 bits carrega o RT-USB.DLL. Não abre a janela nem fala com o carro."""
import os
import platform
import struct
import sys
import time


def run():
    from . import APP_NAME, VERSION, d2xx, j2534
    from .kline import KLine
    from .session import ECUSession

    lines, ok = [], True

    def check(name, fn):
        nonlocal ok
        t = time.perf_counter()
        try:
            detail = fn()
            lines.append(f"OK    {name}: {detail} ({(time.perf_counter() - t) * 1000:.0f} ms)")
        except Exception as e:
            ok = False
            lines.append(f"FALHA {name}: {type(e).__name__}: {e}")

    lines.append(f"{APP_NAME} v{VERSION} — auto-teste {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Windows {platform.version()} · programa de {struct.calcsize('P') * 8} bits · "
                 f"{'compilado' if j2534.is_frozen() else 'código-fonte'} · pasta {j2534.app_root()}")
    for bits in (32, 64):
        check(f"Python portátil {bits} bits", lambda b=bits: j2534.find_python(b))

    def j2534_sim():
        link = j2534.J2534Link("J2534:" + j2534.SIM_DLL)
        link.open()
        try:
            s = ECUSession(link)
            info = s.connect(0x03)
            return f"{info['protocol']}, {len(s.read_faults())} avaria(s) — ponte em {link.proc.args[0]}"
        finally:
            link.close()
    check("Ponte J2534 (simulador)", j2534_sim)

    def d2xx_sim():
        kl = KLine(d2xx.SIM_PORT)
        kl.open()
        try:
            info = ECUSession(kl).connect(0x01)
            return f"{info['part']} — ponte em {kl.ser.proc.args[0]}"
        finally:
            kl.close()
    check("Ponte D2XX (simulador)", d2xx_sim)

    def obd_sim():
        from .obd.elm327 import ELM_SIM_PORT, Elm327Link
        from .obd.session import ObdSession
        s = ObdSession(Elm327Link(ELM_SIM_PORT))
        try:
            info = s.connect()
            n = len(s.read_dtcs()["stored"])
            return f"{info['adapter'].get('version')}, {info['protocol']}, {len(info['ecus'])} centralina(s), {n} avaria(s)"
        finally:
            s.disconnect()
    check("OBD-II / ELM327 (simulador)", obd_sim)

    dll = d2xx.find_dll()
    if dll:
        def rt_usb():
            proc, bits = d2xx._start_bridge(dll)
            try:
                res = proc.call({"op": "list", "dll": dll}, timeout=15)
                if not res.get("ok"):
                    raise RuntimeError(res.get("error", "sem resposta da ponte"))
                devs = ", ".join(f"{d['description']} S/N {d['serial']}" for d in res["devices"]) or "nenhum ligado"
                return f"{dll} ({bits} bits) carregado em {proc.args[0]}; interfaces: {devs}"
            finally:
                proc.close()
        check("Driver RT-USB (HEX-USB)", rt_usb)
    else:
        lines.append("--    Driver RT-USB (HEX-USB): não instalado neste PC (só é preciso para esse cabo)")
    lines.append("RESULTADO: " + ("tudo OK" if ok else "há falhas — envie este ficheiro"))
    return ok, lines


def main(argv):
    out = None
    i = argv.index("--selftest")
    if i + 1 < len(argv):
        out = argv[i + 1]
    ok, lines = run()
    text = "\n".join(lines) + "\n"
    if out is None:
        from .applog import log_dir
        out = os.path.join(log_dir(), "autoteste.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    if sys.stdout is not None:
        try:
            sys.stdout.write(text)
        except Exception:
            pass
    return 0 if ok else 1
