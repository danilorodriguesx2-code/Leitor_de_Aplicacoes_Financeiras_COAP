"""Testes para parsers/__init__.py (utilitários) e parsers individuais."""
from __future__ import annotations
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pytest
from parsers import br_to_float, norm, achar_data, achar_valor, campo_padrao
from parsers.sicredi import parse as parse_sicredi
from parsers.sicoob import parse as parse_sicoob
from parsers.bb import parse as parse_bb
from parsers.itau import parse as parse_itau
from parsers.xp import parse as parse_xp


# =============================================================================
# Utilitários
# =============================================================================

class TestBrToFloat:
    def test_simples(self):
        assert br_to_float("1.234,56") == 1234.56

    def test_com_razao_social(self):
        assert br_to_float("R$ 80.785,24") == 80785.24

    def test_sem_virgula(self):
        assert br_to_float("962.91") == 962.91

    def test_milhar_sem_decimal(self):
        # "1.234" é ambíguo — sem vírgula, um ponto é tratado como decimal
        assert br_to_float("1.234") == 1.234

    def test_negativo_parenteses(self):
        assert br_to_float("(500,00)") == -500.0

    def test_negativo_sinal(self):
        assert br_to_float("-500,00") == -500.0

    def test_sufixo_c(self):
        assert br_to_float("1.000,00 C") == 1000.0

    def test_sufixo_d(self):
        assert br_to_float("500,00 D") == 500.0

    def test_none(self):
        assert br_to_float(None) == 0.0

    def test_vazio(self):
        assert br_to_float("") == 0.0

    def test_float_direto(self):
        assert br_to_float(1234.56) == 1234.56

    def test_int_direto(self):
        assert br_to_float(1000) == 1000.0

    def test_valor_zero(self):
        assert br_to_float("0,00") == 0.0


class TestNorm:
    def test_remove_acentos(self):
        assert norm("Aplicação") == "APLICACAO"

    def test_upper(self):
        assert norm("abc") == "ABC"

    def test_vazio(self):
        assert norm("") == ""
        assert norm(None) == ""


class TestAcharData:
    def test_ultima_data(self):
        texto = "10/05/2026\n15/06/2026"
        assert achar_data(texto) == "15/06/2026"

    def test_default(self):
        assert achar_data("", "01/01/2026") == "01/01/2026"


class TestAcharValor:
    def test_depois(self):
        texto = "Saldo Atual R$ 1.500,00"
        assert achar_valor(texto, "Saldo Atual") == 1500.0

    def test_antes(self):
        texto = "R$ 1.500,00 Saldo Anterior"
        assert achar_valor(texto, "Saldo Anterior", depois=False) == 1500.0

    def test_nao_encontrado(self):
        assert achar_valor("qualquer texto", "Inexistente") == 0.0


class TestCampoPadrao:
    def test_estrutura(self):
        d = campo_padrao("Teste", "Produto", "teste_key", "01/01/2026")
        assert d["banco"] == "Teste"
        assert d["produto"] == "Produto"
        assert d["rule_key"] == "teste_key"
        assert d["data_referencia"] == "01/01/2026"
        assert d["saldo_atual"] == 0.0
        assert d["movimentacoes"] == []
        assert d["campos_extra"] == {}
        assert d["avisos"] == []


# =============================================================================
# Parser Sicredi
# =============================================================================

TEXTO_SICREDI = """Posicao em: 31/05/2026
SICREDINVEST AUTOMATICO

01/05/2026 Saldo Anterior            10.000,00
15/05/2026 Aplicacao                  2.000,00
20/05/2026 Resgate                    1.000,00
25/05/2026 Rendimento Bruto             150,00
30/05/2026 Encargos de IRRF             30,00
31/05/2026 Encargos de IOF               5,00
31/05/2026 Saldo Atual               11.115,00

Posicao para Saque
Saldo Atual             11.115,00
Rendimentos Provisionados      0,00
Saldo Bruto             11.115,00
Provisao IRRF              30,00
Provisao IOF                5,00
Liquido para Saque       11.080,00
Cooperativa: 1234
Conta Corrente: 56789
Periodo de Consulta: 01/05/2026 a 31/05/2026"""


class TestSicrediParser:
    def test_automatico(self):
        d = parse_sicredi(TEXTO_SICREDI)
        assert d["banco"] == "Sicredi"
        assert d["rule_key"] == "sicredi_automatico"
        assert d["data_referencia"] == "31/05/2026"
        assert d["saldo_anterior"] == 10000.0
        assert d["saldo_atual"] == 11115.0
        assert d["saldo_bruto"] == 11115.0
        assert d["rendimentos_pagos_mes"] == 150.0
        assert d["irrf_retido_mes"] == 30.0
        assert d["iof_retido_mes"] == 5.0
        assert d["aplicacoes"] == 2000.0
        assert d["resgates"] == 1000.0
        assert d["rendimentos_provisionados_atual"] == 0.0
        assert d["provisao_irrf_atual"] == 30.0
        assert d["provisao_iof_atual"] == 5.0
        assert len(d["movimentacoes"]) == 7

    def test_evolutivo(self):
        texto = TEXTO_SICREDI.replace("SICREDINVEST AUTOMATICO", "EVOLUTIVO")
        d = parse_sicredi(texto)
        assert d["rule_key"] == "sicredi_evolutivo"

    def test_poupanca(self):
        texto = TEXTO_SICREDI.replace("SICREDINVEST AUTOMATICO", "POUPANCA TRADICIONAL")
        d = parse_sicredi(texto)
        assert d["rule_key"] == "sicredi_poupanca"

    def test_fallback_generico(self):
        texto = TEXTO_SICREDI.replace("SICREDINVEST AUTOMATICO", "SICREDINVEST")
        d = parse_sicredi(texto)
        assert d["rule_key"] == "sicredi_sicredinvest"


# =============================================================================
# Parser Sicoob
# =============================================================================

TEXTO_SICOOB = """Extrato de Apropriacao Diaria
RDC AUTOMATICO
Conta: 12345-6
Numero da aplicacao: 789

01/05/2026 Saldo Anterior                  10.000,00 C
15/05/2026 Aplicacao Financeira             2.000,00 C
20/05/2026 Resgate                          1.000,00 D
25/05/2026 Apropriacao de CM                  200,00 C
30/05/2026 Estorno de Rendimentos              20,00 D
Saldo bruto em 31/05/2026:             11.150,00
Saldo disponivel em 31/05/2026:         11.130,00"""


class TestSicoobParser:
    def test_rdc_automatico(self):
        d = parse_sicoob(TEXTO_SICOOB)
        assert d["banco"] == "Sicoob"
        assert d["rule_key"] == "sicoob_rdc_automatico"
        assert d["data_referencia"] == "31/05/2026"
        assert d["saldo_anterior"] == 10000.0
        assert d["rendimentos_pagos_mes"] == 180.0  # 200 - 20
        assert d["resgates"] == 1000.0
        assert d["aplicacoes"] == 2000.0
        assert d["campos_extra"]["apropriacao_cm_bruta"] == 200.0
        assert d["campos_extra"]["estorno_rendimentos"] == 20.0
        assert d["campos_extra"]["apropriacao_cm_mes"] == 180.0
        assert d["saldo_bruto"] == 11150.0
        # saldo_atual = saldo_bruto - rendimentos_pagos_mes
        assert d["saldo_atual"] == 11150.0 - 180.0

    def test_rdc_flexivel(self):
        texto = TEXTO_SICOOB.replace("RDC AUTOMATICO", "RDC FLEXIVEL")
        d = parse_sicoob(texto)
        assert d["rule_key"] == "sicoob_rdc_flexivel"


# =============================================================================
# Parser BB
# =============================================================================

TEXTO_BB_FUNDO = """Fundo RF Simples Agil
Projecao para 31/05/2026
Saldo anterior 10.000,00
Saldo atual 11.150,00
Aplicacoes 2.000,00
Resgates/Amortizacoes 1.000,00
Imposto de Renda 30,00
IOF 5,00"""


class TestBbParser:
    def test_rf_simples_agil(self):
        d = parse_bb(TEXTO_BB_FUNDO)
        assert d["banco"] == "BB"
        assert d["rule_key"] == "bb_rf_simples_agil"
        assert d["data_referencia"] == "31/05/2026"
        assert d["saldo_anterior"] == 10000.0
        assert d["saldo_atual"] == 11150.0
        assert d["saldo_bruto"] == 11150.0
        assert d["aplicacoes"] == 2000.0
        assert d["resgates"] == 1000.0
        assert d["irrf_retido_mes"] == 30.0
        assert d["iof_retido_mes"] == 5.0

    def test_rf_lp_corp_bancos(self):
        texto = TEXTO_BB_FUNDO.replace("RF Simples Agil", "RF LP Corp Bancos")
        d = parse_bb(texto)
        assert d["rule_key"] == "bb_rf_lp_corp_bancos"

    def test_cdb(self):
        texto = """CDB DI
Periodo: 01/05/2026 a 31/05/2026
valor juros 150,00
valor capital 10.000,00
SALDO NOS ULTIMOS 6 MESES
01/01/2026 10000,00 100,00 15,00 10085,00
01/02/2026 10100,00 120,00 18,00 10202,00
31/05/2026 10000,00 150,00 30,00 10120,00"""
        d = parse_bb(texto)
        assert d["rule_key"] == "bb_cdb_di"
        assert d["saldo_atual"] == 10000.0
        assert d["rendimentos_pagos_mes"] == 150.0
        assert d["provisao_irrf_atual"] == 30.0
        # penultima linha do saldo 6 meses
        assert d["provisao_irrf_anterior"] == 18.0
        assert d["rendimentos_provisionados_atual"] == 150.0

    def test_rende_facil(self):
        texto = """RENDE FACIL
Saldo bruto em 30/04/2026 R$ 10.000,00
Aplicacoes no mes: R$ 2.000,00
Resgates liquidos no mes: R$ 1.000,00
Rendimento no mes: R$ 200,00
IR sobre resgates no mes: R$ 30,00
IOF sobre resgates no mes: R$ 5,00
Saldo bruto em 31/05/2026 R$ 11.165,00
Saldo Final R$ 10.000,00 R$ 200,00 R$ 30,00 R$ 5,00"""
        d = parse_bb(texto)
        assert d["rule_key"] == "bb_rende_facil"
        assert d["rendimentos_pagos_mes"] == 200.0
        assert d["aplicacoes"] == 2000.0
        assert d["resgates"] == 1000.0
        assert d["irrf_retido_mes"] == 30.0
        assert d["iof_retido_mes"] == 5.0
        assert d["saldo_anterior"] == 10000.0
        assert d["saldo_bruto"] == 11165.0
        assert d["saldo_atual"] == 10000.0  # Capital da linha Saldo Final
        assert d["rendimentos_provisionados_atual"] == 200.0
        assert d["provisao_irrf_atual"] == 30.0
        assert d["provisao_iof_atual"] == 5.0


# =============================================================================
# Parser Itaú
# =============================================================================

TEXTO_ITAU_ITAU_VEST = """ITAUVEST
Periodo: 01/05/2026 a 31/05/2026
Total 10000,00 2000,00 1000,00 0,00 200,00 11200,00 30,00 11170,00
SALDO ANTERIOR 10000,00
SALDO FINAL 11170,00
TOTAL 10000,00 200,00 1000,00"""


class TestItauParser:
    def test_itauvest(self):
        d = parse_itau(TEXTO_ITAU_ITAU_VEST)
        assert d["banco"] == "Itau"
        assert d["rule_key"] == "itau_itauvest"
        assert d["data_referencia"] == "31/05/2026"
        assert d["saldo_anterior"] == 10000.0
        assert d["saldo_atual"] == 10000.0  # valor_aplicacao do TOTAL
        assert d["saldo_bruto"] == 11200.0
        assert d["aplicacoes"] == 2000.0
        assert d["resgates"] == 1000.0
        assert d["rendimentos_provisionados_atual"] == 200.0
        assert d["provisao_irrf_atual"] == 30.0
        # rendimento = saldo_final_valor - saldo_anterior_valor
        assert d["rendimentos_pagos_mes"] == 11170.0 - 10000.0

    def test_aplic_aut_mais_sem_arquivo(self):
        """Aplic Aut Mais depende de arquivo XLS -- deve retornar dados minimos."""
        d = parse_itau("APLIC AUT MAIS")
        assert d["rule_key"] == "itau_aplic_aut_mais"
        assert d["avisos"]  # deve conter aviso de falha


# =============================================================================
# Parser XP
# =============================================================================

TEXTO_XP = """RELATORIO DE INVESTIMENTOS
XPerformance
Data de referencia: 31/05/2026
PATRIMONIO TOTAL BRUTO: R$ 500.000,00

Evolucao Patrimonial por Periodo
mai./26 R$ 437.269,94 R$ 0,00 R$ 0,00 R$ 0,00 R$ 438.090,57 R$ 820,64 0,19% 87,79%
abr./26 R$ 436.000,00 -R$ 1.000,00 R$ 0,00 R$ 0,00 R$ 437.269,94 R$ 810,00 0,18% 85,00%
mar./26 R$ 435.000,00 R$ 500,00 R$ 10,00 R$ 2,00 R$ 436.000,00 R$ 790,00 0,17% 80,00%"""


class TestXpParser:
    def test_parse_basico(self):
        d = parse_xp(TEXTO_XP)
        assert d["banco"] == "XP"
        assert d["rule_key"] == "xp_investimentos"
        assert d["data_referencia"] == "31/05/2026"
        # Deve pegar a linha que casa com data_ref (mai./26)
        assert d["rendimentos_pagos_mes"] == 820.64
        assert d["saldo_atual"] == 438090.57
        assert d["saldo_bruto"] == 438090.57
        assert d["saldo_anterior"] == 437269.94
        assert d["irrf_retido_mes"] == 0.0
        assert d["iof_retido_mes"] == 0.0
        assert d["campos_extra"]["patrimonio_total_bruto"] == 500000.0
        assert len(d["campos_extra"]["evolucao_patrimonial"]) == 3

    def test_competencia_alvo(self):
        """Deve respeitar kwargs competencia_alvo para selecionar a linha."""
        d = parse_xp(TEXTO_XP, competencia_alvo="03/2026")
        assert d["rendimentos_pagos_mes"] == 790.0
        assert d["saldo_atual"] == 436000.0

    def test_sem_tabela(self):
        """Texto sem tabela deve gerar aviso."""
        d = parse_xp("XP INVESTIMENTOS\nData de referencia: 31/05/2026")
        assert d.get("aviso") is not None

    def test_movimentacoes_negativas(self):
        """Resgates devem ser extraidos quando movimentacoes sao negativas."""
        d = parse_xp(TEXTO_XP, competencia_alvo="04/2026")
        assert d["resgates"] == 1000.0
        assert d["aplicacoes"] == 0.0
