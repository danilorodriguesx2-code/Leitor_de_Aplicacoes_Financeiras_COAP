"""Parser Sicoob: RDC Flexivel e RDC Automatico (Extrato de Apropriacao Diaria)."""
from __future__ import annotations
import re
from . import br_to_float, norm, campo_padrao

_RE_LINHA = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d.]+,\d{2})\s*([CD])?\s*$", re.MULTILINE)


def parse(texto: str, paginas=None, caminho: str = "", nome_arquivo: str = "", rule_key: str = "",
          **kwargs) -> dict:
    n = norm(texto)
    if "RDC AUTOMATICO" in n:
        produto, rk = "RDC Automatico", "sicoob_rdc_automatico"
    else:
        produto, rk = "RDC Flexivel", "sicoob_rdc_flexivel"
    rk = rule_key or rk

    # data de referencia = data do "Saldo bruto em"
    m = re.search(r"Saldo bruto em\s+(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
    data_ref = m.group(1) if m else ""
    d = campo_padrao("Sicoob", produto, rk, data_ref)

    soma_cm = soma_resg = soma_aplic = soma_estorno = 0.0
    saldo_anterior = 0.0
    for mt in _RE_LINHA.finditer(texto):
        data, hist_raw, val_s, suf = mt.group(1), mt.group(2), mt.group(3), mt.group(4) or ""
        hist = norm(hist_raw)
        val = br_to_float(val_s)
        sinal = -1 if suf == "D" else 1
        d["movimentacoes"].append({"data": data, "historico": hist_raw.strip(),
                                    "valor": val, "tipo": suf or "C"})
        if "SALDO ANTERIOR" in hist:
            saldo_anterior = val
        elif "APROPRIACAO DE CM" in hist:
            soma_cm += val
        elif "ESTORNO DE RENDIMENTOS" in hist:
            soma_estorno += val
        elif "RESGATE" in hist:
            soma_resg += val
        elif "APLICACAO FINANCEIRA" in hist:
            soma_aplic += val

    # Rendimento = soma das apropriacoes de CM liquido de estornos na carencia
    d["saldo_anterior"] = saldo_anterior
    d["campos_extra"]["apropriacao_cm_bruta"] = round(soma_cm, 2)
    d["campos_extra"]["estorno_rendimentos"] = round(soma_estorno, 2)
    d["campos_extra"]["apropriacao_cm_mes"] = round(soma_cm - soma_estorno, 2)
    d["rendimentos_pagos_mes"] = round(soma_cm - soma_estorno, 2)
    d["resgates"] = round(soma_resg, 2)
    d["aplicacoes"] = round(soma_aplic, 2)

    # Saldos do Resumo
    m_sb = re.search(r"Saldo bruto em[^:]*:\s*([\d.]+,\d{2})", texto, re.IGNORECASE)
    m_sd = re.search(r"Saldo dispon\w+ em[^:]*:\s*([\d.]+,\d{2})", texto, re.IGNORECASE)
    d["saldo_bruto"] = br_to_float(m_sb.group(1)) if m_sb else 0.0
    saldo_disp = br_to_float(m_sd.group(1)) if m_sd else 0.0
    # Saldo atual (principal aproximado) = saldo bruto - rendimentos do mes
    d["saldo_atual"] = round(d["saldo_bruto"] - d["rendimentos_pagos_mes"], 2)
    d["campos_extra"]["saldo_disponivel"] = saldo_disp

    m_conta = re.search(r"Conta:\s*([\d.\-]+)", texto)
    m_ap = re.search(r"N\w+mero da aplica\w+:\s*(\d+)", texto, re.IGNORECASE)
    d["campos_extra"]["conta"] = m_conta.group(1) if m_conta else ""
    d["campos_extra"]["numero_aplicacao"] = m_ap.group(1) if m_ap else ""
    return d
