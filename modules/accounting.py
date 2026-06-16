"""
Geracao de lancamentos contabeis a partir dos valores calculados e das regras.

Cada lancamento contem: data, debito, credito, valor, historico, complemento.
Trata estorno de IRRF/IOF quando o valor calculado e negativo (inversao
de debito/credito) conforme os manuais.
"""
from __future__ import annotations


def _complemento(rule: dict) -> str:
    comp = rule.get("complemento", rule.get("produto", ""))
    pessoa = rule.get("pessoa", "")
    return f"{comp} - Pessoa {pessoa}".strip()


def gerar_lancamentos(rule: dict, valores: dict, data_ref: str) -> list:
    """
    Gera a lista de lancamentos contabeis.

    valores: {'rendimento': x, 'irrf': y, 'iof': z}
    Retorna lista de dicts padronizados.
    """
    lancs = []
    lanc_cfg = rule.get("lancamentos", {})
    comp = _complemento(rule)

    # ----- Rendimento -----
    rend = valores.get("rendimento")
    if rend is not None and abs(rend) > 0.0049 and "rendimento" in lanc_cfg:
        cfg = lanc_cfg["rendimento"]
        if rend >= 0:
            deb, cred = cfg["debito"], cfg["credito"]
            deb_cr, cred_cr = cfg.get("debito_cod_red", ""), cfg.get("credito_cod_red", "")
        else:
            # rendimento negativo -> inverte (estorno de rendimento)
            deb, cred = cfg["credito"], cfg["debito"]
            deb_cr, cred_cr = cfg.get("credito_cod_red", ""), cfg.get("debito_cod_red", "")
        lancs.append(_mk(data_ref, deb, deb_cr, cred, cred_cr, abs(rend),
                         cfg["historico"], cfg.get("historico_desc", ""), comp,
                         "Rendimento" + (" (estorno)" if rend < 0 else "")))

    # ----- IRRF -----
    irrf = valores.get("irrf")
    if irrf is not None and abs(irrf) > 0.0049 and "irrf" in lanc_cfg:
        cfg = lanc_cfg["irrf"]
        bloco = cfg["positivo"] if irrf >= 0 else cfg["estorno"]
        lancs.append(_mk(data_ref, bloco["debito"], bloco.get("debito_cod_red", ""),
                         bloco["credito"], bloco.get("credito_cod_red", ""), abs(irrf),
                         cfg["historico"], cfg.get("historico_desc", ""), comp,
                         "Provisao IRRF" + (" (estorno)" if irrf < 0 else "")))

    # ----- IOF -----
    iof = valores.get("iof")
    if iof is not None and abs(iof) > 0.0049 and "iof" in lanc_cfg:
        cfg = lanc_cfg["iof"]
        bloco = cfg["positivo"] if iof >= 0 else cfg["estorno"]
        lancs.append(_mk(data_ref, bloco["debito"], bloco.get("debito_cod_red", ""),
                         bloco["credito"], bloco.get("credito_cod_red", ""), abs(iof),
                         cfg["historico"], cfg.get("historico_desc", ""), comp,
                         "Provisao IOF" + (" (estorno)" if iof < 0 else "")))

    return lancs


def _mk(data, deb, deb_cr, cred, cred_cr, valor, hist, hist_desc, comp, tipo):
    return {
        "data": data,
        "tipo": tipo,
        "debito": deb,
        "debito_cod_red": deb_cr,
        "credito": cred,
        "credito_cod_red": cred_cr,
        "valor": round(valor, 2),
        "historico": hist,
        "historico_desc": hist_desc,
        "complemento": comp,
    }


def gerar_conferencia(rule: dict, dados: dict, valores: dict) -> list:
    """Gera linhas de conferencia de balancete (saldo principal/rendimentos/impostos)."""
    conf = []
    conta = rule.get("conta_aplicacao", "")
    conf.append({"conta": conta, "descricao": rule.get("conta_aplicacao_desc", "Aplicacao (principal)"),
                 "valor": round(dados.get("saldo_atual", 0.0), 2)})
    rp = dados.get("rendimentos_provisionados_atual", 0.0)
    if rp:
        conf.append({"conta": "1.1.01.03.097", "descricao": "Rendimentos a Apropriar",
                     "valor": round(rp, 2)})
    if rule.get("tem_irrf") and dados.get("provisao_irrf_atual"):
        conf.append({"conta": "1.1.01.03.098 / 1.1.03.04.025", "descricao": "IRRF a Apropriar / a Recuperar",
                     "valor": round(dados.get("provisao_irrf_atual", 0.0), 2)})
    if rule.get("tem_iof") and dados.get("provisao_iof_atual"):
        conf.append({"conta": "1.1.01.03.099 / 1.1.05.01.003", "descricao": "IOF a Apropriar",
                     "valor": round(dados.get("provisao_iof_atual", 0.0), 2)})
    return conf
