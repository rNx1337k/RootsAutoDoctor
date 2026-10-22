"""Processo-ponte (D2XX / J2534): uma linha JSON por pedido no stdin, uma por resposta no stdout.

Antes, cada pedido esperava pela resposta com readline() sem limite: um driver bloqueado dentro da DLL
(cabo arrancado a meio, driver com defeito) congelava a thread de comunicação e o fecho do programa.
Agora as respostas chegam por uma thread de leitura e cada pedido tem um tempo máximo; o stderr também é
lido continuamente (um driver que escreva muito no stderr deixava de bloquear o tubo)."""
import collections
import json
import os
import queue
import subprocess
import sys
import threading

from .errors import InterfaceError

NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


class BridgeProcess:
    def __init__(self, args, name):
        self.name = name
        # UTF-8 dos dois lados: com text=True sem codificação, o pai lia na página de código do Windows e a
        # ponte escrevia na que o ambiente lhe desse (ex.: PYTHONIOENCODING=utf-8) — as mensagens de erro da
        # ponte ("DLL não carregou") chegavam corrompidas.
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                                     env=env, creationflags=NO_WINDOW)
        self.args = self.proc.args
        self._lines = queue.Queue()
        self._err = collections.deque(maxlen=40)
        threading.Thread(target=self._pump_out, name=f"{name}-stdout", daemon=True).start()
        self._err_thread = threading.Thread(target=self._pump_err, name=f"{name}-stderr", daemon=True)
        self._err_thread.start()

    def _pump_out(self):
        try:
            for line in self.proc.stdout:
                self._lines.put(line)
        except (OSError, ValueError):
            pass
        self._lines.put(None)                 # fim: a ponte terminou

    def _pump_err(self):
        try:
            for line in self.proc.stderr:
                self._err.append(line)
        except (OSError, ValueError):
            pass

    def stderr_tail(self, n=300):
        return "".join(self._err)[-n:].strip()

    def call(self, req, timeout):
        """Envia um pedido e devolve a resposta (dict). Erros de comunicação com a ponte → InterfaceError."""
        try:
            self.proc.stdin.write(json.dumps(req) + "\n")
            self.proc.stdin.flush()
        except (OSError, ValueError) as e:
            self.kill()
            raise InterfaceError(f"A ponte {self.name} parou: {e}")
        try:
            line = self._lines.get(timeout=timeout)
        except queue.Empty:
            self.kill()
            raise InterfaceError(f"A ponte {self.name} não respondeu em {timeout:.0f} s (pedido '{req.get('op')}'): "
                                 "o driver da interface bloqueou. Desligue e volte a ligar o cabo.")
        if line is None:
            self.wait(1)
            self._err_thread.join(1)          # deixar chegar a última mensagem de erro da ponte
            err = self.stderr_tail()
            raise InterfaceError(f"A ponte {self.name} terminou inesperadamente" + (f": {err}" if err else ""))
        try:
            return json.loads(line)
        except ValueError:
            # p.ex. um driver que escreve no stdout: a conversa com a ponte ficou dessincronizada
            self.kill()
            raise InterfaceError(f"Resposta inválida da ponte {self.name}: {line.strip()[:120]!r}")

    def close(self):
        """Pede à ponte para fechar a interface e terminar; se não terminar em 2 s, é morta."""
        try:
            self.proc.stdin.write(json.dumps({"op": "close"}) + "\n")
            self.proc.stdin.flush()
            self.proc.wait(timeout=2)
        except Exception:
            self.kill()

    def kill(self):
        try:
            self.proc.kill()
        except Exception:
            pass

    def wait(self, timeout=None):
        try:
            return self.proc.wait(timeout=timeout)
        except Exception:
            return None

    def poll(self):
        return self.proc.poll()
