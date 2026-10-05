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
    soma_irrf = soma_iof = 0.0
    saldo_anterior = 0.0
    eventos = []
    pendentes = []
    linhas = [linha.strip() for linha in (texto or "").splitlines() if linha.strip()]
    texto_ocr_normalizado = (texto or "").replace("€", "C").replace("¢", "C")

    tem_cabecalho_mov = any(norm(linha).startswith("DATA HISTORICO") for linha in linhas)
    em_movimentacoes = not tem_cabecalho_mov
    for linha in texto_ocr_normalizado.splitlines():
        linha = linha.strip()
        linha_norm = norm(linha)
        if linha_norm.startswith("DATA HISTORICO"):
            em_movimentacoes = True
            continue
        if em_movimentacoes and linha_norm == "RESUMO":
            em_movimentacoes = False
            continue
        if not em_movimentacoes:
            continue
        mt = _RE_LINHA.fullmatch(linha)
        if mt:
            eventos.append((mt.group(1), mt.group(2).strip(), mt.group(3), mt.group(4) or ""))
            continue
        # Alguns PDFs escaneados posicionam todos os valores em uma coluna
        # separada. Guardamos as linhas de data/historico para parear depois.
        me = re.match(r"^(\d{2}/\d{2}/\d{4})\s+(.+?)$", linha)
        if me and norm(me.group(2)) not in {"DATA HISTORICO", "DATA HISTORICO VALOR"}:
            pendentes.append((me.group(1), me.group(2).strip()))

    if pendentes:
        valores_coluna = []
        for i, linha in enumerate(linhas):
            if norm(linha) != "VALOR":
                continue
            for seguinte in linhas[i + 1:]:
                mv = re.fullmatch(r"([\d.]+,\d{2})\s*([CD])?", seguinte.replace("€", "C"))
                if mv:
                    valores_coluna.append((mv.group(1), mv.group(2) or ""))
            if len(valores_coluna) >= len(pendentes) + 2:
                break
        for (data, hist), (valor, suf) in zip(pendentes, valores_coluna):
            eventos.append((data, hist, valor, suf))

    for data, hist_raw, val_s, suf in eventos:
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
        elif "RETENCAO DE IRRF" in hist:
            soma_irrf += val
        elif "RETENCAO DE IOF" in hist:
            soma_iof += val

    # Rendimento = soma das apropriacoes de CM liquido de estornos na carencia
    d["saldo_anterior"] = saldo_anterior
    d["campos_extra"]["apropriacao_cm_bruta"] = round(soma_cm, 2)
    d["campos_extra"]["estorno_rendimentos"] = round(soma_estorno, 2)
    d["campos_extra"]["apropriacao_cm_mes"] = round(soma_cm - soma_estorno, 2)
    d["rendimentos_pagos_mes"] = round(soma_cm - soma_estorno, 2)
    d["resgates"] = round(soma_resg, 2)
    d["aplicacoes"] = round(soma_aplic, 2)
    d["irrf_retido_mes"] = round(soma_irrf, 2)
    d["iof_retido_mes"] = round(soma_iof, 2)
    d["campos_extra"]["irrf_retido_mes"] = d["irrf_retido_mes"]
    d["campos_extra"]["iof_retido_mes"] = d["iof_retido_mes"]

    # Saldos do Resumo
    m_sb = re.search(r"Saldo bruto em[^:]*:\s*([\d.]+,\d{2})", texto, re.IGNORECASE)
    m_sd = re.search(r"Saldo dispon\w+ em[^:]*:\s*([\d.]+,\d{2})", texto, re.IGNORECASE)
    if m_sb:
        d["saldo_bruto"] = br_to_float(m_sb.group(1))
    if m_sd:
        saldo_disp = br_to_float(m_sd.group(1))
    else:
        # No OCR em colunas, os dois valores do resumo podem aparecer no
        # bloco Valor, depois dos valores das movimentacoes.
        valores_resumo = []
        for i, linha in enumerate(linhas):
            if norm(linha) != "VALOR":
                continue
            for seguinte in linhas[i + 1:]:
                mv = re.fullmatch(r"([\d.]+,\d{2})\s*([CD])?", seguinte.replace("€", "C"))
                if mv:
                    valores_resumo.append(mv.group(1))
        if len(valores_resumo) >= 2:
            d["saldo_bruto"] = br_to_float(valores_resumo[-2])
            saldo_disp = br_to_float(valores_resumo[-1])
        else:
            saldo_disp = 0.0
    # Saldo atual (principal aproximado) = saldo bruto - rendimentos do mes.
    # Em aplicacoes resgatadas, o resumo pode vir zerado; nunca retornar saldo
    # principal negativo por causa da apropriacao acumulada.
    d["saldo_atual"] = round(max(d["saldo_bruto"] - d["rendimentos_pagos_mes"], 0.0), 2)
    d["campos_extra"]["saldo_disponivel"] = saldo_disp

    m_conta = re.search(r"Conta:\s*([\d.\-]+)", texto)
    m_ap = re.search(r"N\w+mero da aplica\w+:\s*(\d+)", texto, re.IGNORECASE)
    d["campos_extra"]["conta"] = m_conta.group(1) if m_conta else ""
    d["campos_extra"]["numero_aplicacao"] = m_ap.group(1) if m_ap else ""
    return d
