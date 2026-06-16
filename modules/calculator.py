"""
Calculadora de rendimento, IRRF e IOF baseada nas regras JSON.

Funciona de forma generica: para cada formula definida na regra, resolve os
campos de entrada (a partir dos dados extraidos pelo parser ou de overrides
manuais informados pelo usuario) e avalia a expressao com seguranca.

Gera tambem a "memoria de calculo": passos detalhados (campos, valores e
formula aplicada) para exibicao visual.
"""
from __future__ import annotations
import math


def _safe_eval(expr: str, variaveis: dict) -> float:
    """Avalia uma expressao aritmetica simples com namespace restrito."""
    permitido = {"__builtins__": {}}
    permitido.update({k: float(v) for k, v in variaveis.items()})
    permitido.update({"abs": abs, "min": min, "max": max, "round": round})
    try:
        return float(eval(expr, permitido, {}))  # noqa: S307 (namespace restrito)
    except Exception as e:
        raise ValueError(f"Erro ao avaliar formula '{expr}': {e}")


def resolver_campos(rule: dict, dados: dict, overrides: dict | None = None) -> dict:
    """
    Para cada campo de calculo, busca o valor:
      1. override manual (se informado),
      2. dados['campos_extra'][source],
      3. dados[source],
      4. 0.0
    Retorna {nome_campo: {'valor', 'label', 'manual', 'origem'}}
    """
    overrides = overrides or {}
    resolvidos = {}
    extra = dados.get("campos_extra", {}) or {}
    for nome, cfg in rule.get("campos_calculo", {}).items():
        source = cfg.get("source", nome)
        origem = "padrao"
        if nome in overrides and overrides[nome] not in (None, ""):
            valor = overrides[nome]
            origem = "manual"
        elif source in extra and extra[source] not in (None, ""):
            valor = extra[source]
            origem = "extrato"
        elif source in dados and dados[source] not in (None, ""):
            valor = dados[source]
            origem = "extrato"
        else:
            valor = 0.0
            origem = "ausente" if cfg.get("manual") else "padrao"
        try:
            valor = float(valor)
        except Exception:
            valor = 0.0
        resolvidos[nome] = {
            "valor": valor,
            "label": cfg.get("label", nome),
            "manual": bool(cfg.get("manual", False)),
            "origem": origem,
        }
    return resolvidos


def calcular(rule: dict, dados: dict, overrides: dict | None = None) -> dict:
    """
    Executa os calculos definidos na regra.

    Retorna dict:
      - valores: {'rendimento': x, 'irrf': y, 'iof': z}
      - memoria: lista de passos para exibicao
      - campos: campos resolvidos
    """
    campos = resolver_campos(rule, dados, overrides)
    var = {k: v["valor"] for k, v in campos.items()}

    valores = {}
    memoria = []
    formulas = rule.get("formulas", {})
    formulas_desc = rule.get("formulas_desc", {})

    for tipo, expr in formulas.items():
        # pula irrf/iof se produto nao possui
        if tipo == "irrf" and not rule.get("tem_irrf", False):
            continue
        if tipo == "iof" and not rule.get("tem_iof", False):
            continue
        try:
            resultado = round(_safe_eval(expr, var), 2)
        except ValueError as e:
            resultado = 0.0
            memoria.append({"tipo": tipo, "erro": str(e)})
            valores[tipo] = resultado
            continue
        valores[tipo] = resultado

        # monta passos
        usados = [nome for nome in campos if nome in expr]
        passos = [{
            "campo": campos[n]["label"],
            "valor": campos[n]["valor"],
            "origem": campos[n]["origem"],
            "manual": campos[n]["manual"],
        } for n in usados]
        memoria.append({
            "tipo": tipo,
            "descricao": formulas_desc.get(tipo, expr),
            "formula": expr,
            "passos": passos,
            "resultado": resultado,
        })

    return {"valores": valores, "memoria": memoria, "campos": campos}
