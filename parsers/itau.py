"""Parser Itau: Itauvest (PDF/OCR) e Aplic Aut Mais (planilha XLS/HTML)."""
from __future__ import annotations
import re
from . import br_to_float, norm, campo_padrao


def parse(texto: str, paginas=None, caminho: str = "", nome_arquivo: str = "", rule_key: str = "",
          **kwargs) -> dict:
    base = norm(texto) + " " + norm(nome_arquivo)
    if "ITAUVEST" in base:
        return _parse_itauvest(texto)
    # Aplic Aut Mais vem de planilha
    return _parse_aplic_aut_mais(caminho, texto)


# ---------------- Itauvest (PDF escaneado -> OCR) ----------------
def _parse_itauvest(texto):
    data_ref = ""
    m = re.search(r"SALDO\s*FINAL\s*\n?\s*(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
    datas = re.findall(r"(\d{2}/\d{2}/\d{4})", texto)
    # data de referencia = ultima data do periodo
    mper = re.search(r"Per\w+odo:\s*\d{2}/\d{2}/\d{4}\s*[aà]\s*(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
    data_ref = mper.group(1) if mper else (datas[-1] if datas else "")
    d = campo_padrao("Itau", "Itauvest", "itau_itauvest", data_ref)

    # Linha Resumo do periodo:
    # Total <saldo_ant> <aplic> <recompras> <vencimentos> <rendim_acum> <saldo_bruto_final> <impostos> <saldo_final>
    m_tot = re.search(r"Total\s+" + r"([\d.]+,\d{2})\s+" * 7 + r"([\d.]+,\d{2})", texto)
    if m_tot:
        vals = [br_to_float(g) for g in m_tot.groups()]
        d["saldo_anterior"] = vals[0]
        d["aplicacoes"] = vals[1]
        d["resgates"] = vals[2]  # recompras
        d["rendimentos_provisionados_atual"] = vals[4]  # rendim acumulado
        d["saldo_bruto"] = vals[5]
        d["provisao_irrf_atual"] = vals[6]  # impostos estimados
        d["campos_extra"]["impostos_estimados_atual"] = vals[6]
        d["campos_extra"]["saldo_final_liquido"] = vals[7]

    # Valor(*) SALDO ANTERIOR e SALDO FINAL (coluna Valor(*) da movimentacao)
    m_sa = re.search(r"SALDO\s*ANTERIOR\s+([\d.]+,\d{2})", texto, re.IGNORECASE)
    saldo_anterior_valor = br_to_float(m_sa.group(1)) if m_sa else d["saldo_anterior"]
    m_sf = re.search(r"SALDO\s*FINAL\s+([\d.]+,\d{2})", texto, re.IGNORECASE)
    if not m_sf:
        m_sf = re.search(r"(\d{2}/\d{2}/\d{4})\s+SALDO\s+FINAL\s+([\d.]+,\d{2})", texto, re.IGNORECASE)
    saldo_final_valor = br_to_float(m_sf.groups()[-1]) if m_sf else d["saldo_bruto"]

    # Valor aplicacao (principal) - linha TOTAL da 'Posicao em': 1o valor monetario
    valor_aplicacao = 0.0
    m_tot2 = re.search(r"\bTOTAL\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})", texto)
    if m_tot2:
        valor_aplicacao = br_to_float(m_tot2.group(1))
    if not valor_aplicacao:
        # fallback: primeira linha de operacao (n. operacao + datas + valor aplicacao)
        m_ap = re.search(r"(\d{10,})\D+\d{2}/\d{2}/\d{4}\D+\d{2}/\d{2}/\d{4}\D+([\d.]+,\d{2})", texto)
        if m_ap:
            valor_aplicacao = br_to_float(m_ap.group(2))

    d["saldo_atual"] = valor_aplicacao or d["saldo_atual"]
    d["campos_extra"]["valor_aplicacao"] = valor_aplicacao
    d["campos_extra"]["saldo_anterior_valor"] = saldo_anterior_valor
    d["campos_extra"]["saldo_final_valor"] = saldo_final_valor
    d["campos_extra"]["valor_creditado"] = d.get("resgates", 0.0)
    # rendimento do periodo = Valor(*) final - Valor(*) anterior
    d["rendimentos_pagos_mes"] = round(saldo_final_valor - saldo_anterior_valor, 2)
    return d


# ---------------- Aplic Aut Mais (planilha) ----------------
def _parse_aplic_aut_mais(caminho, texto=""):
    import pandas as pd
    d = campo_padrao("Itau", "Aplic Aut Mais", "itau_aplic_aut_mais", "")
    try:
        tabelas = pd.read_html(caminho, thousands=".", decimal=",")
        df = tabelas[0]
    except Exception as e:
        d["avisos"].append(f"Falha ao ler planilha Itau: {e}")
        return d

    # Localiza linhas com data dd/mm/aaaa na coluna 1
    def is_data(x):
        return isinstance(x, str) and re.match(r"\d{2}/\d{2}/\d{4}", x.strip())

    col_data = 1
    linhas_data = [i for i in range(len(df)) if is_data(str(df.iloc[i, col_data]))]
    if not linhas_data:
        d["avisos"].append("Nao encontrei linhas de movimentacao na planilha Itau.")
        return d

    primeira = linhas_data[0]
    ultima = linhas_data[-1]

    def num(i, c):
        try:
            return br_to_float(df.iloc[i, c])
        except Exception:
            return 0.0

    # Colunas (layout Itau Aplic Aut Mais):
    # 10=Saldo Principal, 11=Saldo Bruto, 12=Prov IOF, 13=Prov IRRF, 14=Saldo Liquido
    saldo_princ_ant = num(primeira, 10)
    saldo_bruto_ant = num(primeira, 11)
    iof_ant = num(primeira, 12)
    irrf_ant = num(primeira, 13)

    saldo_princ_atu = num(ultima, 10)
    saldo_bruto_atu = num(ultima, 11)
    iof_atu = num(ultima, 12)
    irrf_atu = num(ultima, 13)

    d["data_referencia"] = str(df.iloc[ultima, col_data]).strip()
    d["saldo_anterior"] = saldo_princ_ant
    d["saldo_atual"] = saldo_princ_atu
    d["saldo_bruto"] = saldo_bruto_atu
    d["provisao_irrf_atual"] = irrf_atu
    d["provisao_irrf_anterior"] = irrf_ant
    d["provisao_iof_atual"] = iof_atu
    d["provisao_iof_anterior"] = iof_ant
    d["rendimentos_provisionados_atual"] = round(saldo_bruto_atu - saldo_princ_atu, 2)
    d["rendimentos_provisionados_anterior"] = round(saldo_bruto_ant - saldo_princ_ant, 2)
    d["campos_extra"]["render_atual"] = round(saldo_bruto_atu - saldo_princ_atu, 2)
    d["campos_extra"]["render_anterior"] = round(saldo_bruto_ant - saldo_princ_ant, 2)

    # Linha "Acum. Mês": totais de aplicacoes/resgates/rendimentos
    linha_acum = None
    for i in range(len(df)):
        if "ACUM" in norm(str(df.iloc[i, col_data])):
            linha_acum = i
            break
    if linha_acum is not None:
        # 2=Aplic, 3=Princ Resg, 4=Bruto Resg, 5=IOF, 6=IRRF, 7=Liq Resg, 8=Rend Bruto, 9=Rend Liq
        d["aplicacoes"] = num(linha_acum, 2)
        d["resgates"] = num(linha_acum, 4)
        d["iof_retido_mes"] = num(linha_acum, 5)
        d["irrf_retido_mes"] = num(linha_acum, 6)
        d["rendimentos_pagos_mes"] = num(linha_acum, 8)
        d["campos_extra"]["rendimento_pago_liquido"] = num(linha_acum, 9)
        d["campos_extra"]["valor_liquido_resgatado"] = num(linha_acum, 7)
    return d
