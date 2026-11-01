"""Gravações de valores de medição guardadas com o veículo: cada CSV gravado em Medição com a matrícula (ou o
nº de chassis) preenchida fica também copiado para historico/medicao/<veículo>/, para na visita seguinte o
programa comparar sozinho com a gravação anterior do mesmo controlador.

Nome de cada cópia: AAAAMMDD_HHMMSS_<endereço>.csv (o endereço em hexadecimal, ex.: 01 = motor)."""
import datetime
import logging
import os
import re
import shutil

from .history import history_dir, plate_key

log = logging.getLogger(__name__)

_NAME = re.compile(r"^(\d{8}_\d{6})(?:_\d+)?_([0-9A-F]{2})\.csv$")


def vehicle_key(vehicle):
    """Pasta do veículo: a matrícula sem traços nem espaços, ou o nº de chassis; None sem nenhum dos dois."""
    vehicle = vehicle or {}
    return plate_key(vehicle.get("plate")) or plate_key(vehicle.get("vin")) or None


def vehicle_dir(vehicle, directory=None, create=False):
    key = vehicle_key(vehicle)
    if not key:
        return None
    path = os.path.join(directory or history_dir(), "medicao", key)
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def store(csv_path, vehicle, address, directory=None, when=None):
    """Copia a gravação para a pasta do veículo; devolve o caminho da cópia (None sem matrícula/chassis
    ou se a cópia falhar — a gravação original fica sempre onde o utilizador a guardou)."""
    folder = vehicle_dir(vehicle, directory, create=True)
    if folder is None:
        return None
    stamp = f"{when or datetime.datetime.now():%Y%m%d_%H%M%S}"
    dest, n = os.path.join(folder, f"{stamp}_{address:02X}.csv"), 1
    while os.path.exists(dest):
        n += 1
        dest = os.path.join(folder, f"{stamp}_{n}_{address:02X}.csv")
    try:
        shutil.copyfile(csv_path, dest)
    except OSError:
        log.warning("Não foi possível guardar a gravação com o veículo", exc_info=True)
        return None
    return dest


def for_vehicle(vehicle, address=None, directory=None):
    """Gravações guardadas deste veículo, da mais recente para a mais antiga: [(caminho, data, endereço)]."""
    folder = vehicle_dir(vehicle, directory)
    if folder is None or not os.path.isdir(folder):
        return []
    out = []
    for name in os.listdir(folder):
        m = _NAME.match(name)
        if not m:
            continue
        addr = int(m.group(2), 16)
        if address is not None and addr != address:
            continue
        when = datetime.datetime.strptime(m.group(1), "%Y%m%d_%H%M%S")
        out.append((os.path.join(folder, name), when, addr))
    out.sort(key=lambda r: (r[1], r[0]), reverse=True)
    return out


def previous(vehicle, address, current=None, directory=None):
    """A gravação mais recente do mesmo veículo e controlador antes de `current` (caminho de uma cópia
    guardada por store), ou a mais recente de todas sem `current`. (caminho, data) ou None."""
    rows = for_vehicle(vehicle, address, directory)
    if current is not None:
        cur = os.path.normcase(os.path.abspath(current))
        paths = [os.path.normcase(os.path.abspath(p)) for p, _w, _a in rows]
        if cur in paths:
            rows = rows[paths.index(cur) + 1:]
    return (rows[0][0], rows[0][1]) if rows else None
