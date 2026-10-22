"""A matriz de compatibilidade (rad/coverage.py) é a fonte única: o documento tem de estar actualizado, os testes
citados têm de existir e nenhuma combinação pode dizer "confirmado em hardware" na comunicação com a ECU sem
haver prova registada."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from rad import coverage  # noqa: E402


def test_document_is_generated_from_the_matrix():
    with open(os.path.join(ROOT, "docs", "COBERTURA.md"), encoding="utf-8") as fh:
        doc = fh.read().replace("\r\n", "\n")
    assert doc == coverage.markdown(), "docs/COBERTURA.md desactualizado: gerar de novo a partir de rad/coverage.py"


def test_cited_tests_exist():
    for e in coverage.MATRIX:
        for t in e["tests"]:
            assert os.path.exists(os.path.join(ROOT, "tests", t + ".py")), t
        for k, _n in coverage.STAGES:
            assert e[k] in coverage.LEVELS, (e["interface"], k)


def test_no_ecu_communication_claimed_on_hardware_without_evidence():
    # Até haver uma sessão real registada, nenhuma combinação pode dizer que comunicou com uma ECU em hardware.
    assert all(e["ecu"] != coverage.HW for e in coverage.MATRIX)
    hex_row = [e for e in coverage.MATRIX if "HEX-USB+CAN" in e["interface"]][0]
    assert hex_row["ecu"] == coverage.BLOCKED
