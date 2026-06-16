"""
Identificacao automatica de banco e produto a partir do conteudo do extrato.

Usa palavras-chave (do texto extraido e/ou do nome do arquivo) para
determinar qual parser/produto utilizar.
"""
from __future__ import annotations
import re
import unicodedata


def _normalize(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper()


# Ordem importa: padroes mais especificos primeiro.
# Cada regra: (rule_key, banco, produto, [padroes_obrigatorios_any], peso)
_REGRAS = [
    # ---- SICREDI ----
    ("sicredi_evolutivo", "Sicredi", "Sicredinvest Evolutivo",
     ["SICREDINVEST EVOLUTIVO"], 100),
    ("sicredi_automatico", "Sicredi", "Sicredinvest Automatico",
     ["SICREDINVEST AUTOMATICO"], 100),
    ("sicredi_poupanca", "Sicredi", "Poupanca Tradicional",
     ["POUPANCA TRADICIONAL", "MOVIMENTO POUPANCA"], 90),
    ("sicredi_sicredinvest", "Sicredi", "Sicredinvest",
     ["SICREDINVEST"], 70),  # generico, apos os especificos
    # ---- SICOOB ----
    ("sicoob_rdc_flexivel", "Sicoob", "RDC Flexivel",
     ["RDC FLEXIVEL"], 100),
    ("sicoob_rdc_automatico", "Sicoob", "RDC Automatico",
     ["RDC AUTOMATICO"], 100),
    # ---- BB ----
    ("bb_rf_simples_agil", "BB", "RF Simples Agil",
     ["RF SIMPLES AGIL"], 100),
    ("bb_rf_lp_corp_bancos", "BB", "RF LP Corp Bancos",
     ["RF LP CORP BANCOS"], 100),
    ("bb_rende_facil", "BB", "Rende Facil",
     ["RENDE FACIL"], 100),
    ("bb_cdb_di", "BB", "CDB DI",
     ["BB CDB DI", "CDB/BB REAPLIC", "EXTRATO DE CDB"], 90),
    # ---- ITAU ----
    ("itau_itauvest", "Itau", "Itauvest",
     ["ITAUVEST"], 100),
    ("itau_aplic_aut_mais", "Itau", "Aplic Aut Mais",
     ["APLIC AUT MAIS"], 100),
    # ---- XP ----
    ("xp_investimentos", "XP", "XP Investimentos",
     ["XPERFORMANCE", "RELATORIO DE INVESTIMENTOS", "EVOLUCAO PATRIMONIAL",
      "CONTA INVESTIMENTO", "XP INVESTIMENTOS"], 80),
]

# Palavras-chave de banco (para diagnostico/segunda chance)
_BANCO_KEYS = {
    "Sicredi": ["SICREDI", "COOPERATIVA:", "SICREDI FONE", "DEPOSITO A PRAZO"],
    "Sicoob": ["SICOOB", "SISBR", "APROPRIACAO DE CM"],
    "BB": ["BANCO DO BRASIL", "BBASSET", "CDB/BB REAPLIC", "FUNDOS DE INVESTIMENTO"],
    "Itau": ["ITAUEMPRESAS", "ITAU.COM.BR", "ITAUVEST", "APLIC AUT MAIS",
             "EXTRATO CONSOLIDADO MENSAL APLIC AUT MAIS"],
    "XP": ["XP INVESTIMENTOS", "XPERFORMANCE", "RELATORIO DE INVESTIMENTOS"],
}


def identificar(texto: str, nome_arquivo: str = "") -> dict:
    """
    Identifica banco e produto.

    Retorna dict:
      - rule_key, banco, produto, confianca (0-100), origem ('conteudo'|'arquivo'|'desconhecido')
      - candidatos: lista ordenada de (rule_key, score)
    """
    conteudo = _normalize(texto)
    nome = _normalize(nome_arquivo)
    base = conteudo + "\n" + nome

    candidatos = []
    for rule_key, banco, produto, padroes, peso in _REGRAS:
        for pad in padroes:
            if pad in base:
                # bonus se aparece no conteudo (mais confiavel que nome)
                score = peso + (10 if pad in conteudo else 0)
                candidatos.append((rule_key, banco, produto, score))
                break

    if candidatos:
        candidatos.sort(key=lambda x: x[3], reverse=True)
        rule_key, banco, produto, score = candidatos[0]
        return {
            "rule_key": rule_key,
            "banco": banco,
            "produto": produto,
            "confianca": min(score, 100),
            "origem": "conteudo" if score >= 80 else "arquivo",
            "candidatos": [(c[0], c[3]) for c in candidatos],
        }

    # Segunda chance: identificar ao menos o banco
    for banco, keys in _BANCO_KEYS.items():
        if any(k in base for k in keys):
            return {
                "rule_key": None,
                "banco": banco,
                "produto": None,
                "confianca": 30,
                "origem": "banco_apenas",
                "candidatos": [],
            }

    return {
        "rule_key": None,
        "banco": None,
        "produto": None,
        "confianca": 0,
        "origem": "desconhecido",
        "candidatos": [],
    }
