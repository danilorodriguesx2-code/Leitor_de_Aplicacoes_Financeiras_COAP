"""Regressão do preenchimento automático do extrato anterior."""
from __future__ import annotations

import json
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from modules.calculator import calcular
from modules.previous import extrair_overrides_anterior


def test_itauvest_mapeia_impostos_estimados_do_extrato_anterior():
    anterior_fields = {
        "impostos_estimados_anterior": {
            "label": "Impostos Estimados (mes anterior)",
            "source": "impostos_estimados_anterior",
            "manual": True,
        }
    }
    prev_dados = {
        "provisao_irrf_atual": 1218.70,
        "campos_extra": {"impostos_estimados_atual": 1218.70},
    }

    valores = extrair_overrides_anterior(anterior_fields, prev_dados)

    assert valores == {"impostos_estimados_anterior": 1218.70}


def test_itauvest_irrf_usa_valor_anterior_extraido():
    rule = json.loads((BASE_DIR / "rules/itau_itauvest.json").read_text())
    dados_atual = {"campos_extra": {"impostos_estimados_atual": 1500.00}}
    overrides = {"impostos_estimados_anterior": 1218.70}

    calculado = calcular(rule, dados_atual, overrides)

    assert calculado["valores"]["irrf"] == 281.30
