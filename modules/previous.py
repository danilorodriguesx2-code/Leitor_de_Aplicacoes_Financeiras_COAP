"""Preenchimento automático de campos do extrato anterior."""
from __future__ import annotations


# O nome à esquerda é o campo manual da regra atual; o nome à direita é
# procurado no resultado extraído do extrato anterior.
PREVIOUS_FIELD_MAP = {
    "rend_prov_anterior": "rendimentos_provisionados_atual",
    "prov_irrf_anterior": "provisao_irrf_atual",
    "prov_iof_anterior": "provisao_iof_atual",
    # Itauvest chama a provisão de IRRF de "Impostos Estimados".
    "impostos_estimados_anterior": "impostos_estimados_atual",
}


def extrair_overrides_anterior(anterior_fields: dict, prev_dados: dict) -> dict:
    """Converte o resultado do extrato anterior em overrides da regra atual."""
    extra = prev_dados.get("campos_extra", {}) or {}
    valores = {}
    for campo_anterior, origem in PREVIOUS_FIELD_MAP.items():
        if campo_anterior not in anterior_fields:
            continue
        valor = prev_dados.get(origem)
        if valor in (None, ""):
            valor = extra.get(origem, 0.0)
        try:
            valores[campo_anterior] = float(valor or 0.0)
        except (ValueError, TypeError):
            valores[campo_anterior] = 0.0
    return valores
