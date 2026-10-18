"""Pontuação de saúde do veículo (sem dependências de Qt, usada no programa e no relatório)."""


def health_score(items):
    """0–100 a partir do Auto-Scan: avarias permanentes descontam 9, intermitentes 4,
    módulos sem comunicação 10."""
    if not items:
        return None
    score = 100
    for it in items:
        if it.get("status") != "ok":
            score -= 10
            continue
        for f in it.get("faults", []):
            score -= 4 if f.get("intermittent") else 9
    return max(0, min(100, score))


def health_text(score):
    if score is None:
        return "Sem dados"
    if score >= 85:
        return "Bom estado"
    if score >= 60:
        return "Requer atenção"
    return "Intervenção recomendada"
