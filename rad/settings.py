"""Definições do programa (porta do cabo, oficina, janela...).

Ficam no registo do Windows. Com a variável RAD_SETTINGS_INI ficam num ficheiro .ini — é o que os
testes usam para não mexer nas definições reais."""
import os

from PySide6.QtCore import QSettings


def app_settings():
    path = os.environ.get("RAD_SETTINGS_INI")
    if path:
        return QSettings(path, QSettings.IniFormat)
    return QSettings("Roots", "RootsAutoDoctor")


# Tamanho da interface (Opções → Ecrã). Aplica-se no arranque, antes de criar a QApplication, com o factor de
# escala do Qt: aumenta letras, botões e mostradores por igual, sem cortar textos.
UI_SCALES = ("1", "1.15", "1.3", "1.5")


def ui_scale(settings=None):
    value = str((settings or app_settings()).value("ui/scale", "1"))
    return value if value in UI_SCALES else "1"


def apply_ui_scale(environ=None):
    """Define QT_SCALE_FACTOR a partir das definições. Se o utilizador já definiu a variável, não mexe.
    Devolve o factor aplicado (ou None)."""
    environ = os.environ if environ is None else environ
    if environ.get("QT_SCALE_FACTOR"):
        return None
    try:
        scale = ui_scale()
    except Exception:                 # definições ilegíveis: arranca no tamanho normal
        return None
    if scale != "1":
        environ["QT_SCALE_FACTOR"] = scale
        return scale
    return None
