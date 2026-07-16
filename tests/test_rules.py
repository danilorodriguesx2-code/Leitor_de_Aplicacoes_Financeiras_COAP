"""Validacao dos arquivos JSON de regras em rules/."""
from __future__ import annotations
import sys
import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_DIR = os.path.join(BASE_DIR, "rules")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pytest


def _carregar_todas_regras():
    """Retorna lista de (nome_arquivo, dict_regra)."""
    regras = []
    for fname in sorted(os.listdir(RULES_DIR)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(RULES_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                data = None
        regras.append((fname, data))
    return regras


REGRAS = _carregar_todas_regras()


class TestRegrasJsonValidas:
    def test_todos_arquivos_sao_json_validos(self):
        invalidos = [fname for fname, data in REGRAS if data is None]
        assert not invalidos, f"Arquivos JSON invalidos: {invalidos}"

    @pytest.mark.parametrize("fname,regra", REGRAS, ids=lambda r: r[0] if isinstance(r, tuple) else str(r))
    def test_campos_obrigatorios(self, fname, regra):
        obrigatorios = ["rule_key", "banco", "produto", "formulas", "campos_calculo", "lancamentos"]
        for campo in obrigatorios:
            assert campo in regra, f"{fname}: campo '{campo}' ausente"

    @pytest.mark.parametrize("fname,regra", REGRAS)
    def test_rule_key_consistente(self, fname, regra):
        esperado = fname.replace(".json", "")
        assert regra["rule_key"] == esperado, f"{fname}: rule_key '{regra['rule_key']}' != '{esperado}'"

    @pytest.mark.parametrize("fname,regra", REGRAS)
    def test_formulas_referenciam_campos_validos(self, fname, regra):
        campos = set(regra.get("campos_calculo", {}).keys())
        for tipo, expr in regra.get("formulas", {}).items():
            # Extrai nomes de variaveis da expressao (palavras alfanumericas + underscore)
            import re
            vars_usadas = set(re.findall(r"\b[a-zA-Z_]\w*\b", expr))
            # Filtra funcoes permitidas e palavras reservadas
            permitidas = {"abs", "min", "max", "round"}
            for var in vars_usadas:
                if var in permitidas:
                    continue
                assert var in campos, (
                    f"{fname}: formula '{tipo}' referencia campo '{var}' "
                    f"que nao existe em campos_calculo"
                )

    @pytest.mark.parametrize("fname,regra", REGRAS)
    def test_campos_calculo_source_existe(self, fname, regra):
        """Verifica se cada source referencia um campo valido do parser."""
        for nome, cfg in regra.get("campos_calculo", {}).items():
            assert "source" in cfg, f"{fname}: campo '{nome}' sem 'source'"
            assert "label" in cfg, f"{fname}: campo '{nome}' sem 'label'"

    @pytest.mark.parametrize("fname,regra", REGRAS)
    def test_lancamentos_rendimento_estrutura(self, fname, regra):
        lanc = regra.get("lancamentos", {}).get("rendimento")
        assert lanc is not None, f"{fname}: falta lancamentos.rendimento"
        for campo in ("historico", "debito", "credito"):
            assert campo in lanc, f"{fname}: lancamentos.rendimento faltando '{campo}'"

    @pytest.mark.parametrize("fname,regra", REGRAS)
    def test_lancamentos_irrf_estrutura(self, fname, regra):
        lanc = regra.get("lancamentos", {}).get("irrf")
        if lanc is not None:
            for bloco in ("positivo", "estorno"):
                assert bloco in lanc, f"{fname}: lancamentos.irrf faltando '{bloco}'"
                for campo in ("debito", "credito"):
                    assert campo in lanc[bloco], f"{fname}: lancamentos.irrf.{bloco} faltando '{campo}'"

    @pytest.mark.parametrize("fname,regra", REGRAS)
    def test_lancamentos_iof_estrutura(self, fname, regra):
        lanc = regra.get("lancamentos", {}).get("iof")
        if lanc is not None:
            for bloco in ("positivo", "estorno"):
                assert bloco in lanc, f"{fname}: lancamentos.iof faltando '{bloco}'"
                for campo in ("debito", "credito"):
                    assert campo in lanc[bloco], f"{fname}: lancamentos.iof.{bloco} faltando '{campo}'"

    @pytest.mark.parametrize("fname,regra", REGRAS)
    def test_campos_manuais_tem_label(self, fname, regra):
        for nome, cfg in regra.get("campos_calculo", {}).items():
            if cfg.get("manual"):
                assert "label" in cfg and cfg["label"], (
                    f"{fname}: campo manual '{nome}' precisa de label descritiva"
                )

    @pytest.mark.parametrize("fname,regra", REGRAS)
    def test_cnpj_tem_14_digitos(self, fname, regra):
        cnpj = str(regra.get("cnpj", ""))
        assert len(cnpj) == 14, f"{fname}: CNPJ '{cnpj}' deve ter 14 digitos"
        assert cnpj.isdigit(), f"{fname}: CNPJ deve conter apenas digitos"
