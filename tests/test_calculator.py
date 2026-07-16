"""Testes para modules/calculator.py."""
from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pytest
from modules.calculator import _safe_eval, resolver_campos, calcular


# =============================================================================
# _safe_eval
# =============================================================================

class TestSafeEval:
    def test_soma(self):
        assert _safe_eval("a + b", {"a": 10, "b": 5}) == 15.0

    def test_subtracao(self):
        assert _safe_eval("a - b", {"a": 10, "b": 5}) == 5.0

    def test_multiplicacao(self):
        assert _safe_eval("a * b", {"a": 3, "b": 4}) == 12.0

    def test_divisao(self):
        assert _safe_eval("a / b", {"a": 10, "b": 2}) == 5.0

    def test_funcao_abs(self):
        assert _safe_eval("abs(a)", {"a": -10}) == 10.0

    def test_funcao_round(self):
        assert _safe_eval("round(a, 2)", {"a": 1.2345}) == 1.23

    def test_expressao_composta(self):
        assert _safe_eval("a + b - c * d / e",
                          {"a": 10, "b": 5, "c": 3, "d": 4, "e": 2}) == 9.0
        # 10 + 5 - (3 * 4 / 2) = 15 - 6 = 9

    def test_variavel_zero(self):
        assert _safe_eval("a + b", {"a": 0, "b": 0}) == 0.0

    def test_valor_negativo(self):
        assert _safe_eval("a", {"a": -100.50}) == -100.50

    def test_sintaxe_invalida(self):
        with pytest.raises(ValueError):
            _safe_eval("a + +", {"a": 1})

    def test_variavel_inexistente(self):
        with pytest.raises(ValueError):
            _safe_eval("a + x", {"a": 1})

    def test_seguranca(self):
        """Nao deve permitir acesso a funcoes perigosas."""
        with pytest.raises(Exception):
            _safe_eval("__import__('os').system('dir')", {})


# =============================================================================
# resolver_campos
# =============================================================================

RULE_SICREDI_AUTO = {
    "campos_calculo": {
        "rend_pagos_mes": {"label": "Rendimentos Pagos", "source": "rendimentos_pagos_mes", "manual": False},
        "rend_prov_anterior": {"label": "Rend. Prov. Anterior", "source": "rendimentos_provisionados_anterior", "manual": True},
        "rend_prov_atual": {"label": "Rend. Prov. Atual", "source": "rendimentos_provisionados_atual", "manual": False},
        "prov_irrf_atual": {"label": "Prov IRRF Atual", "source": "provisao_irrf_atual", "manual": False},
        "prov_irrf_anterior": {"label": "Prov IRRF Anterior", "source": "provisao_irrf_anterior", "manual": True},
        "prov_iof_atual": {"label": "Prov IOF Atual", "source": "provisao_iof_atual", "manual": False},
        "prov_iof_anterior": {"label": "Prov IOF Anterior", "source": "provisao_iof_anterior", "manual": True},
    }
}


class TestResolverCampos:
    def test_extrai_do_dados(self):
        dados = {"rendimentos_pagos_mes": 150.0, "rendimentos_provisionados_atual": 50.0}
        r = resolver_campos(RULE_SICREDI_AUTO, dados, {})
        assert r["rend_pagos_mes"]["valor"] == 150.0
        assert r["rend_pagos_mes"]["origem"] == "extrato"
        assert r["rend_prov_atual"]["valor"] == 50.0
        assert r["rend_prov_atual"]["origem"] == "extrato"

    def test_override_manual(self):
        dados = {"rendimentos_provisionados_anterior": 0.0}
        overrides = {"rend_prov_anterior": 30.0}
        r = resolver_campos(RULE_SICREDI_AUTO, dados, overrides)
        assert r["rend_prov_anterior"]["valor"] == 30.0
        assert r["rend_prov_anterior"]["origem"] == "manual"

    def test_campo_manual_sem_override_retorna_zero(self):
        dados = {}
        r = resolver_campos(RULE_SICREDI_AUTO, dados, {})
        assert r["rend_prov_anterior"]["valor"] == 0.0
        assert r["rend_prov_anterior"]["origem"] == "ausente"

    def test_campos_extra(self):
        dados = {"campos_extra": {"ganho_financeiro": 820.64}}
        rule = {"campos_calculo": {
            "ganho": {"label": "Ganho", "source": "ganho_financeiro", "manual": False}
        }}
        r = resolver_campos(rule, dados, {})
        assert r["ganho"]["valor"] == 820.64
        assert r["ganho"]["origem"] == "extrato"

    def test_label_e_manual(self):
        r = resolver_campos(RULE_SICREDI_AUTO, {}, {})
        assert r["rend_pagos_mes"]["label"] == "Rendimentos Pagos"
        assert r["rend_pagos_mes"]["manual"] is False
        assert r["rend_prov_anterior"]["manual"] is True


# =============================================================================
# calcular
# =============================================================================

RULE_SICREDI_AUTO_COMPLETA = {
    "tem_irrf": True,
    "tem_iof": True,
    "formulas": {
        "rendimento": "rend_pagos_mes - rend_prov_anterior + rend_prov_atual",
        "irrf": "prov_irrf_atual - prov_irrf_anterior",
        "iof": "prov_iof_atual - prov_iof_anterior",
    },
    "formulas_desc": {
        "rendimento": "Rendimento = Pagos - Prov. Anterior + Prov. Atual",
        "irrf": "IRRF = Atual - Anterior",
        "iof": "IOF = Atual - Anterior",
    },
    "campos_calculo": RULE_SICREDI_AUTO["campos_calculo"],
}

DADOS_SICREDI_AUTO = {
    "rendimentos_pagos_mes": 150.0,
    "rendimentos_provisionados_anterior": 30.0,
    "rendimentos_provisionados_atual": 50.0,
    "provisao_irrf_atual": 40.0,
    "provisao_irrf_anterior": 20.0,
    "provisao_iof_atual": 10.0,
    "provisao_iof_anterior": 5.0,
}


class TestCalcular:
    def test_calculo_completo(self):
        r = calcular(RULE_SICREDI_AUTO_COMPLETA, DADOS_SICREDI_AUTO, {})
        # rend = 150 - 30 + 50 = 170
        assert r["valores"]["rendimento"] == 170.0
        # irrf = 40 - 20 = 20
        assert r["valores"]["irrf"] == 20.0
        # iof = 10 - 5 = 5
        assert r["valores"]["iof"] == 5.0

    def test_memoria_de_calculo(self):
        r = calcular(RULE_SICREDI_AUTO_COMPLETA, DADOS_SICREDI_AUTO, {})
        assert len(r["memoria"]) == 3
        rend_mem = r["memoria"][0]
        assert rend_mem["tipo"] == "rendimento"
        assert rend_mem["resultado"] == 170.0
        assert len(rend_mem["passos"]) == 3

    def test_sem_irrf(self):
        rule = {**RULE_SICREDI_AUTO_COMPLETA, "tem_irrf": False}
        r = calcular(rule, DADOS_SICREDI_AUTO, {})
        assert "irrf" not in r["valores"]

    def test_sem_iof(self):
        rule = {**RULE_SICREDI_AUTO_COMPLETA, "tem_iof": False}
        r = calcular(rule, DADOS_SICREDI_AUTO, {})
        assert "iof" not in r["valores"]

    def test_override_muda_resultado(self):
        overrides = {"rend_prov_anterior": 50.0}
        r = calcular(RULE_SICREDI_AUTO_COMPLETA, DADOS_SICREDI_AUTO, overrides)
        # rend = 150 - 50 + 50 = 150
        assert r["valores"]["rendimento"] == 150.0

    def test_campos_retornados(self):
        r = calcular(RULE_SICREDI_AUTO_COMPLETA, DADOS_SICREDI_AUTO, {})
        assert "campos" in r
        assert r["campos"]["rend_pagos_mes"]["origem"] == "extrato"

    def test_valores_zerados(self):
        r = calcular(RULE_SICREDI_AUTO_COMPLETA, {}, {})
        assert r["valores"]["rendimento"] == 0.0
        assert r["valores"]["irrf"] == 0.0
        assert r["valores"]["iof"] == 0.0

    # --- XP Investimentos ---
    RULE_XP = {
        "tem_irrf": False,
        "tem_iof": False,
        "formulas": {
            "rendimento": "ganho_financeiro",
        },
        "campos_calculo": {
            "ganho_financeiro": {
                "label": "Ganho Financeiro",
                "source": "ganho_financeiro",
                "manual": False,
            }
        },
    }

    def test_xp_rendimento(self):
        dados = {"campos_extra": {"ganho_financeiro": 820.64}}
        r = calcular(self.RULE_XP, dados, {})
        assert r["valores"]["rendimento"] == 820.64
        # sem IRRF/IOF
        assert "irrf" not in r["valores"]
        assert "iof" not in r["valores"]

    # --- BB RF Simples ---
    RULE_BB_RF = {
        "tem_irrf": True,
        "tem_iof": True,
        "formulas": {
            "rendimento": "saldo_atual + resgates_mes + irrf_pago + iof_pago - saldo_anterior",
        },
        "campos_calculo": {
            "saldo_atual": {"source": "saldo_atual", "label": "Saldo Atual"},
            "saldo_anterior": {"source": "saldo_anterior", "label": "Saldo Anterior"},
            "resgates_mes": {"source": "resgates", "label": "Resgates"},
            "irrf_pago": {"source": "irrf_retido_mes", "label": "IRRF"},
            "iof_pago": {"source": "iof_retido_mes", "label": "IOF"},
        },
    }

    def test_bb_rf_rendimento(self):
        dados = {"saldo_atual": 11150.0, "saldo_anterior": 10000.0,
                 "resgates": 1000.0, "irrf_retido_mes": 30.0, "iof_retido_mes": 5.0}
        r = calcular(self.RULE_BB_RF, dados, {})
        # 11150 + 1000 + 30 + 5 - 10000 = 2185
        assert r["valores"]["rendimento"] == 2185.0
