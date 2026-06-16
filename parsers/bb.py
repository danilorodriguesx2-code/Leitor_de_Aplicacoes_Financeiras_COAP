"""Parser Banco do Brasil: RF Simples Agil, RF LP Corp Bancos, Rende Facil, CDB DI."""
from __future__ import annotations
import re
import io
from . import br_to_float, norm, campo_padrao

try:
    import fitz
    import pytesseract
    from PIL import Image
    _OCR_DISPONIVEL = True
except Exception:
    _OCR_DISPONIVEL = False


def parse(texto: str, paginas=None, caminho: str = "", nome_arquivo: str = "", rule_key: str = "",
          **kwargs) -> dict | list[dict]:
    n = norm(texto)
    nome_n = norm(nome_arquivo)
    base = n + " " + nome_n

    # Multi-produto: mesmo PDF com dois fundos diferentes
    if "RF LP CORP BANCOS" in base and "RF SIMPLES AGIL" in base:
        secoes = _split_fund_sections(texto)
        resultados = []
        for secao in secoes:
            sn = norm(secao)
            if "RF LP CORP BANCOS" in sn:
                resultados.append(_parse_fundo(secao, "RF LP Corp Bancos", "bb_rf_lp_corp_bancos"))
            elif "RF SIMPLES AGIL" in sn:
                resultados.append(_parse_fundo(secao, "RF Simples Agil", "bb_rf_simples_agil"))
        return resultados if resultados else _parse_fundo(texto, "RF LP Corp Bancos", "bb_rf_lp_corp_bancos")

    if "RF LP CORP BANCOS" in base:
        return _parse_fundo(texto, "RF LP Corp Bancos", "bb_rf_lp_corp_bancos")
    if "RF SIMPLES AGIL" in base:
        return _parse_fundo(texto, "RF Simples Agil", "bb_rf_simples_agil")
    if "RENDE FACIL" in base:
        return _parse_rende_facil(texto, caminho)
    if "CDB" in base:
        return _parse_cdb(texto)
    # fallback generico fundo
    return _parse_fundo(texto, "RF Simples Agil", "bb_rf_simples_agil")


def _split_fund_sections(texto):
    """Divide texto com multiplos extratos de fundos BB em secoes individuais."""
    import re
    # Cada secao comeca com "RF <Nome> - CNPJ: XX.XXX.XXX/XXXX-XX"
    pattern = r"(RF (?:LP Corp Bancos|Simples Ágil) - CNPJ: [\d./-]+)"
    partes = re.split(pattern, texto)
    secoes = []
    for i in range(1, len(partes), 2):
        cabecalho = partes[i]
        conteudo = partes[i + 1] if i + 1 < len(partes) else ""
        secoes.append(cabecalho + "\n" + conteudo)
    return secoes


# ---------------- Fundos (RF Simples Agil / RF LP Corp Bancos) ----------------
def _parse_fundo(texto, produto, rk):
    data_ref = _data_ref_fundo(texto)
    d = campo_padrao("BB", produto, rk, data_ref)

    m_ant = re.search(r"Saldo anterior\s+([\d.]+,\d{2})", texto, re.IGNORECASE)
    m_atu = re.search(r"Saldo atual\s+([\d.]+,\d{2})", texto, re.IGNORECASE)
    d["saldo_anterior"] = br_to_float(m_ant.group(1)) if m_ant else 0.0
    d["saldo_atual"] = br_to_float(m_atu.group(1)) if m_atu else 0.0

    m_aplic = re.search(r"Aplica\w+es\s+([\d.]+,\d{2})", texto, re.IGNORECASE)
    m_resg = re.search(r"Resgates/Amortiza\w+es\s+([\d.]+,\d{2})", texto, re.IGNORECASE)
    d["aplicacoes"] = br_to_float(m_aplic.group(1)) if m_aplic else 0.0
    d["resgates"] = br_to_float(m_resg.group(1)) if m_resg else 0.0

    m_ir = re.search(r"Imposto de Renda[^\d]*([\d.]+,\d{2})", texto, re.IGNORECASE)
    m_iof = re.search(r"(?:IOF|10F)[^\d]*([\d.]+,\d{2})", texto, re.IGNORECASE)
    d["irrf_retido_mes"] = br_to_float(m_ir.group(1)) if m_ir else 0.0
    d["iof_retido_mes"] = br_to_float(m_iof.group(1)) if m_iof else 0.0

    d["saldo_bruto"] = d["saldo_atual"]
    return d


def _data_ref_fundo(texto):
    m = re.search(r"Proje\w+ para\s+(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
    if m:
        return m.group(1)
    # Trunca no inicio do rodape da pagina para ignorar datas de metadados
    for marcador in ("Transa", "Servi\u00e7o de Atendimento", "Ouvidoria"):
        pos = texto.find(marcador)
        if pos >= 0:
            texto = texto[:pos]
    datas = re.findall(r"(\d{2}/\d{2}/\d{4})", texto)
    return datas[-1] if datas else ""


# ---------------- Rende Facil ----------------
def _parse_rende_facil(texto, caminho=""):
    data_ref = ""
    m = re.search(r"Saldo bruto em\s+\d{2}/\d{2}/\d{4}.*?Saldo bruto em\s+(\d{2}/\d{2}/\d{4})",
                  texto, re.IGNORECASE | re.DOTALL)
    if m:
        data_ref = m.group(1)
    d = campo_padrao("BB", "Rende Facil", "bb_rende_facil", data_ref)

    def g(pat):
        mm = re.search(pat, texto, re.IGNORECASE)
        return br_to_float(mm.group(1)) if mm else 0.0

    d["aplicacoes"] = g(r"Aplica\w+es no m\w+s:\s*R?\$?\s*([\d.]+,\d{2})")
    d["resgates"] = g(r"Resgates l\w+quidos no m\w+s:\s*R?\$?\s*([\d.]+,\d{2})")
    d["irrf_retido_mes"] = g(r"IR sobre resgates no m\w+s:\s*R?\$?\s*([\d.]+,\d{2})")
    d["iof_retido_mes"] = g(r"IOF sobre resgates no m\w+s:\s*R?\$?\s*([\d.]+,\d{2})")
    rendimento_mes = g(r"Rendimentos? no m\w+s:\s*R?\$?\s*([\d.]+,\d{2})")
    d["campos_extra"]["rendimento_no_mes"] = rendimento_mes
    d["rendimentos_pagos_mes"] = rendimento_mes

    # Saldo bruto final (segundo 'Saldo bruto em')
    saldos = re.findall(r"Saldo bruto em\s+\d{2}/\d{2}/\d{4}\s*R?\$?\s*([\d.]+,\d{2})", texto, re.IGNORECASE)
    if len(saldos) >= 2:
        d["saldo_anterior"] = br_to_float(saldos[0])
        d["saldo_bruto"] = br_to_float(saldos[-1])
    elif saldos:
        d["saldo_bruto"] = br_to_float(saldos[-1])

    # Linha 'Saldo Final' do historico: Capital, Rendimento, IR, IOF
    m_sf = re.search(r"Saldo Final\s+R?\$?\s*([\d.]+,\d{2})\s+R?\$?\s*([\d.]+,\d{2})\s+R?\$?\s*([\d.]+,\d{2})\s+R?\$?\s*([\d.]+,\d{2})",
                     texto, re.IGNORECASE)
    if m_sf:
        d["saldo_atual"] = br_to_float(m_sf.group(1))  # Capital
        d["rendimentos_provisionados_atual"] = br_to_float(m_sf.group(2))
        d["campos_extra"]["irrf_saldo_final_atual"] = br_to_float(m_sf.group(3))
        d["campos_extra"]["iof_saldo_final_atual"] = br_to_float(m_sf.group(4))
        d["provisao_irrf_atual"] = br_to_float(m_sf.group(3))
        d["provisao_iof_atual"] = br_to_float(m_sf.group(4))
    else:
        d["saldo_atual"] = d["saldo_bruto"]

    # Fallback OCR por coordenadas quando regex falha (PDF escaneado)
    if not rendimento_mes and caminho and _OCR_DISPONIVEL:
        vals = _extrair_resumo_por_coordenadas(caminho)
        if vals.get("rendimento"):
            d["campos_extra"]["rendimento_no_mes"] = br_to_float(vals["rendimento"])
            d["rendimentos_pagos_mes"] = br_to_float(vals["rendimento"])
        if vals.get("irrf"):
            d["irrf_retido_mes"] = br_to_float(vals["irrf"])
        if vals.get("iof"):
            d["iof_retido_mes"] = br_to_float(vals["iof"])
        if vals.get("saldo_anterior"):
            d["saldo_anterior"] = br_to_float(vals["saldo_anterior"])
        if vals.get("saldo_bruto"):
            d["saldo_bruto"] = br_to_float(vals["saldo_bruto"])
        if vals.get("aplicacoes"):
            d["aplicacoes"] = br_to_float(vals["aplicacoes"])
        if vals.get("resgates"):
            d["resgates"] = br_to_float(vals["resgates"])
        if vals.get("saldo_atual"):
            d["saldo_atual"] = br_to_float(vals["saldo_atual"])
        if vals.get("rendimentos_provisionados_atual"):
            d["rendimentos_provisionados_atual"] = br_to_float(vals["rendimentos_provisionados_atual"])
        if vals.get("irrf_saldo_final_atual"):
            d["campos_extra"]["irrf_saldo_final_atual"] = br_to_float(vals["irrf_saldo_final_atual"])
            d["provisao_irrf_atual"] = br_to_float(vals["irrf_saldo_final_atual"])
        if vals.get("iof_saldo_final_atual"):
            d["campos_extra"]["iof_saldo_final_atual"] = br_to_float(vals["iof_saldo_final_atual"])
            d["provisao_iof_atual"] = br_to_float(vals["iof_saldo_final_atual"])

    return d


def _extrair_resumo_por_coordenadas(caminho):
    """Extrai valores do Resumo do mes usando pytesseract com coordenadas."""
    import fitz
    import pytesseract
    from PIL import Image

    doc = fitz.open(caminho)
    page = doc[0]
    pix = page.get_pixmap(dpi=220)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    data = pytesseract.image_to_data(img, lang="por", output_type=pytesseract.Output.DICT)

    words = []
    for i in range(len(data["text"])):
        t = data["text"][i].strip()
        if not t:
            continue
        words.append({
            "text": t, "x": data["left"][i], "y": data["top"][i],
        })

    # Agrupa em linhas por coordenada Y (tolerancia 10px)
    rows = []
    for w in sorted(words, key=lambda w: (w["y"], w["x"])):
        for row in rows:
            if abs(row["y"] - w["y"]) <= 10:
                row["words"].append(w)
                row["y"] = (row["y"] + w["y"]) // 2
                break
        else:
            rows.append({"y": w["y"], "words": [w]})
    rows.sort(key=lambda r: r["y"])

    # Localiza secao Resumo
    ini = fim = None
    for i, row in enumerate(rows):
        texto_linha = " ".join([p["text"] for p in row["words"]])
        if "Resumo" in texto_linha and "m" in texto_linha.lower():
            ini = i
        if "Historico" in texto_linha or "moviment" in texto_linha.lower():
            fim = i
            break
    if ini is None:
        return {}
    if fim is None:
        fim = len(rows)

    # Mapeia rotulos do Resumo para valores a direita (x > 900)
    valores = {}
    rotulos = [
        (r"\bIR\b", "irrf", False),
        (r"\bIOF\b", "iof", False),
        (r"Rendimentos?", "rendimento", False),
    ]

    for i in range(ini + 1, fim):
        row = rows[i]
        texto_linha = " ".join([p["text"] for p in row["words"]])
        # Pega numero mais a direita na linha (x alto)
        nums_direita = [p for p in row["words"] if p["x"] > 900 and re.match(r"^[\d.]+,\d{2}$", p["text"])]
        if not nums_direita:
            continue
        for padrao, chave, primeiro in rotulos:
            if chave in valores:
                continue
            if re.search(padrao, texto_linha, re.IGNORECASE):
                # Se primeiro=True, pega o primeiro numero da esquerda (Capital)
                # Senao, pega o ultimo numero (valores a direita)
                if primeiro:
                    nums_esq = [p for p in row["words"] if p["x"] < 900 and re.match(r"^[\d.]+,\d{2}$", p["text"])]
                    if nums_esq:
                        valores[chave] = nums_esq[0]["text"]
                else:
                    valores[chave] = nums_direita[-1]["text"]

    retry_labels = [
        (r"\bIR\b", "irrf"),
        (r"\bIOF\b", "iof"),
        (r"Rendimentos?", "rendimento"),
    ]
    if not valores.get("rendimento"):
        for i in range(ini + 1, fim):
            row = rows[i]
            texto_linha = " ".join([p["text"] for p in row["words"]])
            nums_direita = [p for p in row["words"] if p["x"] > 900 and re.match(r"^[\d.]+,\d{2}$", p["text"])]
            if not nums_direita:
                continue
            for padrao, chave in retry_labels:
                if chave in valores:
                    continue
                if re.search(padrao, texto_linha, re.IGNORECASE):
                    valores[chave] = nums_direita[-1]["text"]

    # Capital column: extrai valores da tabela historica (y > fim+1)
    capital_vals = []
    hist_textos = []
    for i in range(fim + 1, min(fim + 10, len(rows))):
        row = rows[i]
        texto_linha = " ".join([p["text"] for p in row["words"]])
        hist_textos.append(texto_linha)
        for p in row["words"]:
            if 500 < p["x"] < 700 and re.match(r"^[\d.]+,\d{2}$", p["text"]):
                capital_vals.append(p["text"])
                break

    if len(capital_vals) >= 1 and not valores.get("saldo_anterior"):
        valores["saldo_anterior"] = capital_vals[0]
    if len(capital_vals) >= 5:
        if not valores.get("saldo_bruto"):
            valores["saldo_bruto"] = capital_vals[-1]

    # Saldo Final row: extrai Capital, Rendimento, IR, IOF, VL
    for i in range(fim + 1, min(fim + 10, len(rows))):
        row = rows[i]
        texto_linha = " ".join([p["text"] for p in row["words"]])
        if "Saldo" not in texto_linha or "Final" not in texto_linha:
            continue
        # Extrai valores por faixa de x
        nums_col = {"capital": [], "rendimento": [], "ir": [], "iof": [], "vl": []}
        for p in row["words"]:
            if not re.match(r"^[\d.]+,\d{2}$", p["text"]):
                continue
            if 500 < p["x"] < 700:
                nums_col["capital"].append(p["text"])
            elif 800 < p["x"] < 1000:
                nums_col["rendimento"].append(p["text"])
            elif 1050 < p["x"] < 1250:
                nums_col["ir"].append(p["text"])
            elif 1250 < p["x"] < 1450:
                nums_col["iof"].append(p["text"])
            elif 1450 < p["x"] < 1650:
                nums_col["vl"].append(p["text"])
        if nums_col["capital"]:
            valores["saldo_atual"] = nums_col["capital"][0]
        if nums_col["rendimento"]:
            valores["rendimentos_provisionados_atual"] = nums_col["rendimento"][0]
        if nums_col["ir"]:
            valores["irrf_saldo_final_atual"] = nums_col["ir"][0]
        if nums_col["iof"]:
            valores["iof_saldo_final_atual"] = nums_col["iof"][0]
        break

    return valores


# ---------------- CDB DI ----------------
def _parse_cdb(texto):
    data_ref = ""
    m = re.search(r"Per\w+odo\s*:\s*\d{2}/\d{2}/\d{4}\s*a\s*(\d{2}/\d{2}/\d{4})", texto, re.IGNORECASE)
    if m:
        data_ref = m.group(1)
    d = campo_padrao("BB", "CDB DI", "bb_cdb_di", data_ref)

    # Rendimento mensal -> valor juros
    m_j = re.search(r"valor juros\s+([\d.]+,\d{2})", texto, re.IGNORECASE)
    rendimento = br_to_float(m_j.group(1)) if m_j else 0.0
    d["campos_extra"]["rendimento_mensal"] = rendimento
    d["rendimentos_pagos_mes"] = rendimento

    # valor capital (principal)
    m_c = re.search(r"valor capital\s+([\d.]+,\d{2})", texto, re.IGNORECASE)
    d["saldo_atual"] = br_to_float(m_c.group(1)) if m_c else 0.0

    # SALDO NOS ULTIMOS 6 MESES: Data Capital Juros IR proj Liquid
    # Isola o bloco entre "SALDO NOS ULTIMOS 6 MESES" e "RESUMO DOS DEPOSITOS"
    # para nao capturar linhas de outras tabelas (ex.: RESUMO DOS DEPOSITOS).
    bloco = texto
    m_ini = re.search(r"SALDO\s+NOS\s+\w+\s+6\s+MESES", texto, re.IGNORECASE)
    if m_ini:
        bloco = texto[m_ini.end():]
        m_fim = re.search(r"RESUMO\s+DOS\s+DEP\w+SITOS", bloco, re.IGNORECASE)
        if m_fim:
            bloco = bloco[:m_fim.start()]
    # Remove espacos inseridos pelo OCR dentro de numeros (ex.: "1600000 ,00" -> "1600000,00")
    bloco = re.sub(r"(\d)\s+,\s*(\d)", r"\1,\2", bloco)
    linhas_saldo = re.findall(
        r"(\d{2}/\d{2}/\d{4})\s+([\d.]+,?\d*)\s+([\d.]+,?\d*)\s+([\d.]+,?\d*)\s+([\d.]+,?\d*)", bloco)
    if len(linhas_saldo) >= 2:
        atual = linhas_saldo[-1]
        anterior = linhas_saldo[-2]
        d["campos_extra"]["ir_proj_atual"] = br_to_float(atual[3])
        d["campos_extra"]["ir_proj_anterior"] = br_to_float(anterior[3])
        d["provisao_irrf_atual"] = br_to_float(atual[3])
        d["provisao_irrf_anterior"] = br_to_float(anterior[3])
        d["rendimentos_provisionados_atual"] = br_to_float(atual[2])  # juros
        d["saldo_bruto"] = br_to_float(atual[1]) + br_to_float(atual[2])
    elif len(linhas_saldo) == 1:
        atual = linhas_saldo[-1]
        d["campos_extra"]["ir_proj_atual"] = br_to_float(atual[3])
        d["campos_extra"]["ir_proj_anterior"] = 0.0
        d["provisao_irrf_atual"] = br_to_float(atual[3])
    return d
