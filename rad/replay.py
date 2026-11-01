"""Reproduz uma gravação (.radrec) com o código actual do programa e diz se o resultado é o mesmo.

Corre os mesmos comandos, pela mesma ordem, na thread de comunicação ligada à porta "REPLAY:<ficheiro>", e
compara:
  1. os bytes que o programa envia com os que enviou na gravação (divergências);
  2. o resumo de cada resultado (avarias, identificação, valores...) com o resumo gravado.
Uma gravação feita num carro real passa assim a ser um teste: se uma alteração ao código mudar a forma de falar
com a centralina ou de interpretar a resposta, o teste falha."""
import logging

from . import capture

log = logging.getLogger(__name__)


def run(path, worker_factory=None):
    """Devolve {"ok", "divergences", "mismatches", "commands", "results", "missing", "head"}."""
    head, events = capture.load(path)
    if worker_factory is None:
        from .worker import Worker
        worker_factory = Worker
    w = worker_factory()
    adapter = head.get("adapter") or "kline"
    w.cfg.update({"port": capture.replay_port(path, head.get("transport")), "adapter": adapter,
                  "echo": head.get("echo", "auto"),
                  "baud": head.get("baud", "auto"), "elm_protocol": head.get("elm_protocol", "0")})
    got = []
    errors = []
    w.result.connect(lambda c, d: got.append((c, capture.summarize(c, d))))
    w.state.connect(lambda s, d: got.append(("connect", capture.summarize("connect", d)))
                    if s == "connected" else None)
    w.scan_progress.connect(lambda i, n, it: got.append(("scan_item",
                                                         capture.summarize("autoscan", {"items": [it]}))))
    w.error.connect(lambda c, m: errors.append((c, m)))
    commands = capture.script(events)
    capture.reset_replay()
    for cmd, args in commands:
        try:
            _run_one(w, cmd, args)
        except Exception as e:                       # um erro aqui também é uma diferença em relação à gravação
            log.warning("Reprodução: %s falhou", cmd, exc_info=True)
            errors.append((cmd, str(e)))
    report = _link_report(w)
    try:
        w._close_all()
    except Exception:
        log.debug("Reprodução: fecho", exc_info=True)

    expected = capture.results(events)
    got = [(c, s) for c, s in got if s is not None]
    mismatches = []
    for i, (cmd, summ) in enumerate(expected):
        if i >= len(got):
            mismatches.append({"index": i, "cmd": cmd, "expected": summ, "got": None})
            continue
        if got[i] != (cmd, summ):
            mismatches.append({"index": i, "cmd": cmd, "expected": summ, "got": got[i][1], "got_cmd": got[i][0]})
    recorded_errors = [e.get("cmd") for e in events if e.get("note") == "error"]
    unexpected_errors = [e for e in errors if e[0] not in recorded_errors]
    ok = not report["divergences"] and not mismatches and not unexpected_errors
    return {"ok": ok, "divergences": report["divergences"], "mismatches": mismatches, "commands": len(commands),
            "results": len(expected), "errors": unexpected_errors, "unsent": report.get("unsent", 0),
            "head": head}


def _run_one(w, cmd, args):
    if cmd == "_keep_alive":
        if w.session and w.session.connected:
            w.session.keep_alive()
        return
    if cmd == "_live":
        mode, groups = args
        w.live_mode, w.live_groups = mode, list(groups)
        if w.session and w.session.connected:
            w._poll_live()
        w.live_mode = None
        return
    if cmd == "_obd_live":
        w.live_mode, w.live_groups = "obd", list(args[0])
        if w.obd is not None and w.obd.connected:
            w._poll_obd_live()
        w.live_mode = None
        return
    if cmd == "validation":
        args = (dict(args[0] if args else {}, _replay=True),)
    w._dispatch(cmd, tuple(args))


def _link_report(w):
    """Junta as divergências de todas as portas de reprodução abertas durante a sessão (o programa pode fechar e
    voltar a abrir a porta a meio, por exemplo ao mudar de controlador)."""
    divergences, unsent = [], 0
    for port in capture.OPENED:
        r = port.report()
        divergences += r["divergences"]
        unsent = r["unsent"]                         # o que ficou por enviar na última porta aberta
    capture.reset_replay()
    return {"divergences": divergences, "unsent": unsent}
