"""Sonda do clone HEX-USB / cabos FTDI — para os testes com hardware (ver docs/HEX_USB.md).

    .venv\\Scripts\\python.exe tools\\hex_probe.py                 passos 1–2: só leitura, sem carro
    .venv\\Scripts\\python.exe tools\\hex_probe.py --port D2XX:RT000001 --echo
                                                                  passo 3: eco da linha K (carro, ignição ON)
    .venv\\Scripts\\python.exe tools\\hex_probe.py --port D2XX:RT000001 --ecu 01
                                                                  passos 4–5: identificação + avarias + grupo 1

Nunca escreve nada na centralina nem na EEPROM do cabo: o --ecu só lê identificação, avarias e
o grupo de medição 1. Guarde o resultado (copiar/colar) para comparar entre cabos e carros.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import cable, d2xx, ftdi_direct                  # noqa: E402
from rad.kline import KLine, list_serial_ports           # noqa: E402
from rad.session import ECUSession                       # noqa: E402


def step(title):
    print(f"\n=== {title}")


def main():
    for stream in (sys.stdout, sys.stderr):        # consolas cp1252 / saída redireccionada não rebentam com "→"
        try:
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", help="porta a testar (ex.: D2XX:RT000001, FTDI:0403:FA24:RT000001, COM5)")
    ap.add_argument("--echo", action="store_true", help="teste de eco da linha K (cabo no carro, ignição ON)")
    ap.add_argument("--ecu", help="endereço hexadecimal a identificar (ex.: 01 motor, 17 painel, 03 ABS)")
    ap.add_argument("--baud", default="auto", help="auto | 10400 | 9600 | 4800")
    args = ap.parse_args()

    step("1. Dispositivos USB (Windows PnP)")
    devs = [d for d in cable.list_usb_devices() if "VID_0403" in d["id"].upper() or "ross" in d["name"].lower()]
    for d in devs:
        print(f"  {d['status']:6} {d['name']}  [{d['id']}]  serviço={d.get('service') or '—'}  "
              f"hwid={', '.join(d.get('hwid') or [])}")
    if not devs:
        print("  nenhum dispositivo FTDI/Ross-Tech ligado")
    for f in cable.classify(devs):
        print(f"  → [{f['level']}] {f['title']}" + (f"  (porta {f['com']})" if f.get("com") else ""))

    step("2. Acesso ao chip")
    print(f"  RT-USB.DLL: {d2xx.find_dll() or 'não encontrado'}")
    print(f"  Portas D2XX: {d2xx.list_ports() or '—'}")
    print(f"  Portas USB directo (WinUSB): {ftdi_direct.list_ports() or '—'}")
    print("  Todas as portas: " + ", ".join(p for p, _ in list_serial_ports()))
    if not args.port:
        return 0
    kl = KLine(args.port, echo="auto", log=lambda m: print("  | " + m))
    t = time.perf_counter()
    try:
        kl.open()
    except Exception as e:
        print(f"  FALHOU abrir {args.port}: {e}")
        return 1
    print(f"  {args.port} aberta em {(time.perf_counter() - t) * 1000:.0f} ms"
          + (f" — {kl.ser.info}" if getattr(kl.ser, "info", None) else ""))
    try:
        if args.echo or args.ecu:
            step("3. Eco da linha K (0x55 a 10400 baud)")
            ok = kl.echo_test()
            print("  OK — o cabo vê a linha K" if ok else
                  "  SEM ECO — ignição desligada, cabo fora do carro, ou interface com microcontrolador")
            if not ok:
                return 2
        if args.ecu:
            addr = int(args.ecu, 16)
            step(f"4. Identificação do controlador {addr:02X}")
            s = ECUSession(kl, lambda m: print("  | " + m), args.baud)
            info = s.connect(addr, retry=True)
            for k in ("protocol", "baud", "part", "component", "coding", "wsc"):
                print(f"  {k}: {info.get(k)}")
            step("5. Avarias e grupo 1 (só leitura)")
            for f in s.read_faults():
                print(f"  {f.get('vag')}  {f.get('desc', '')}")
            try:
                g = s.read_group(1)
                print("  grupo 1: " + " | ".join(f"{x['value']} {x['unit']}" for x in g["fields"]))
            except Exception as e:
                print(f"  grupo 1: {e}")
            s.disconnect()
    except Exception as e:
        print(f"  ERRO: {type(e).__name__}: {e}")
        return 3
    finally:
        kl.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
