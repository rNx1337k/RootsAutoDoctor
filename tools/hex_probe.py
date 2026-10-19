"""Sonda do clone HEX-USB / cabos FTDI — para os testes com hardware (ver docs/HEX_USB.md).

    .venv\\Scripts\\python.exe tools\\hex_probe.py                 passos 1–2: só leitura, sem carro
    .venv\\Scripts\\python.exe tools\\hex_probe.py --port D2XX:RT000001 --echo
                                                                  passo 3: eco da linha K (carro, ignição ON)
    .venv\\Scripts\\python.exe tools\\hex_probe.py --port D2XX:RT000001 --ecu 01
                                                                  passos 4–5: identificação + avarias + grupo 1
    .venv\\Scripts\\python.exe tools\\hex_probe.py --port D2XX:RT000001 --mcu
                                                                  microcontrolador do clone HEX: versão e modo
                                                                  (só leitura, basta o USB)
    .venv\\Scripts\\python.exe tools\\hex_probe.py --port D2XX:RT000001 --set-mode kkl --yes
                                                                  põe o clone HEX em modo KKL ("dumb");
                                                                  --set-mode inteligente repõe o original

Nunca escreve nada na centralina: o --ecu só lê identificação, avarias e o grupo de medição 1.
Só o --set-mode (com --yes) muda uma definição do cabo: o modo de arranque do microcontrolador, o mesmo
que a opção "Boot in Intelligent Mode" do VCDS; reverte-se com --set-mode inteligente. Guarde o resultado (copiar/colar) para comparar entre cabos e carros.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rad import cable, d2xx, ftdi_direct, hexmcu          # noqa: E402
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
    ap.add_argument("--mcu", action="store_true", help="clone HEX: procura o microcontrolador (só leitura)")
    ap.add_argument("--set-mode", choices=("kkl", "inteligente"), help="clone HEX: muda o modo de arranque")
    ap.add_argument("--yes", action="store_true", help="confirma o --set-mode")
    ap.add_argument("--kline-test", action="store_true", help="clone HEX: tensão K1/K2 vista pelo cabo (só leitura)")
    ap.add_argument("--no-echo", action="store_true", help="tenta a centralina mesmo sem eco (eco detectado no init)")
    ap.add_argument("--raw", action="store_true", help="mostra todos os bytes trocados com a linha K")
    ap.add_argument("--lines", help="DTR,RTS a usar, ex.: 0,1 (por defeito 0,0 no cabo HEX)")
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
    kl = KLine(args.port, echo="auto", log=lambda m: print("  | " + m), raw_log=args.raw)
    if args.lines:
        kl.lines = tuple(x.strip() == "1" for x in args.lines.split(","))
    t = time.perf_counter()
    try:
        kl.open()
    except Exception as e:
        print(f"  FALHOU abrir {args.port}: {e}")
        return 1
    print(f"  {args.port} aberta em {(time.perf_counter() - t) * 1000:.0f} ms"
          + (f" — {kl.ser.info}" if getattr(kl.ser, "info", None) else ""))
    try:
        if args.mcu or args.set_mode:
            step("HEX. Microcontrolador do clone (DTR/RTS desligados)")
            mcu = hexmcu.HexMcu(kl.ser, log=print)
            res = mcu.probe()
            print("  " + hexmcu.describe(res))
            if res["found"] and args.kline_test:
                kt = hexmcu.kline_test(mcu)
                print("  Linha K vista pelo cabo: " + ("sem resposta" if kt is None else hexmcu.describe_kline(kt)))
            if args.set_mode:
                if not res["found"]:
                    print("  Modo não mudado: o microcontrolador não respondeu")
                    return 4
                if not args.yes:
                    print("  Acrescente --yes para mudar mesmo o modo de arranque do cabo")
                    return 4
                target = hexmcu.MODE_DUMB if args.set_mode == "kkl" else hexmcu.MODE_SMART
                now = mcu.set_mode(target)
                print(f"  Modo de arranque agora: {hexmcu.MODE_NAMES.get(now, now)}")
                mcu.reset(boot=1.0)
            kl.set_baud(10400)
            kl.set_lines(*hexmcu.HEX_LINES)
        if args.echo or args.ecu:
            step("3. Eco da linha K (0x55 a 10400 baud)")
            ok = kl.echo_test()
            print("  OK — o cabo vê a linha K" if ok else
                  "  SEM ECO — ignição desligada, cabo fora do carro, ou interface com microcontrolador")
            if not ok and not args.no_echo:
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
