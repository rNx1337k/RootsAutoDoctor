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
