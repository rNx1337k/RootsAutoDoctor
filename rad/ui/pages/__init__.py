"""Páginas da aplicação (uma por ficheiro)."""
from .autoscan import AutoScanPage
from .common import FieldCell, GroupCard, ask, btn, card, lbl, page_header
from .history import HistoryPage
from .home import HomePage
from .module import ModulePage
from .module_select import ModuleSelectPage
from .options import OptionsPage

__all__ = ["AutoScanPage", "FieldCell", "GroupCard", "HistoryPage", "HomePage", "ModulePage",
           "ModuleSelectPage", "OptionsPage", "ask", "btn", "card", "lbl", "page_header"]
