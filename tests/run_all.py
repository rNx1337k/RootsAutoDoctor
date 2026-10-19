"""Corre todos os testes (tests/test_*.py) e mostra um resumo no fim.

Ao contrário de encadear os ficheiros, um teste que falha não impede os outros de correr.
Os ficheiros também funcionam com pytest:  python -m pytest tests
"""
import glob
import importlib.util
import os
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))


def main(pattern=""):
    passed, failed = 0, []
    t0 = time.perf_counter()
    for path in sorted(glob.glob(os.path.join(HERE, "test_*.py"))):
        name = os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception:
            failed.append((name, traceback.format_exc()))
            print(f"ERRO   {name} (não foi possível carregar)")
            continue
        for fn_name, fn in list(vars(mod).items()):
            if not fn_name.startswith("test_") or not callable(fn) or pattern not in f"{name}.{fn_name}":
                continue
            try:
                fn()
            except Exception:
                failed.append((f"{name}.{fn_name}", traceback.format_exc()))
                print(f"FALHOU {name}.{fn_name}")
            else:
                passed += 1
                print(f"OK     {name}.{fn_name}")
    for test, tb in failed:
        print(f"\n===== {test} =====\n{tb}")
    print(f"\n{passed} passaram, {len(failed)} falharam ({time.perf_counter() - t0:.1f} s)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
