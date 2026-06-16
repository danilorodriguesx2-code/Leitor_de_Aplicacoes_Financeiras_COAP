"""
Pipeline de processamento de um extrato:
  arquivo -> texto (com OCR se preciso) -> identificacao -> parser -> dados.

Tambem carrega as regras JSON e roteia para o parser correto.
"""
from __future__ import annotations
import os
import json
import unicodedata

from . import ocr as ocr_mod
from . import identifier as ident_mod

from parsers import sicredi, sicoob, bb, itau, xp

_THIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_RULES_DIR = os.path.join(_THIS_DIR, "rules")

_PARSER_POR_BANCO = {
    "Sicredi": sicredi.parse,
    "Sicoob": sicoob.parse,
    "BB": bb.parse,
    "Itau": itau.parse,
    "XP": xp.parse,
}


def carregar_regra(rule_key: str) -> dict | None:
    if not rule_key:
        return None
    caminho = os.path.join(_RULES_DIR, rule_key + ".json")
    if not os.path.exists(caminho):
        return None
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def listar_regras() -> list:
    regras = []
    for nome in sorted(os.listdir(_RULES_DIR)):
        if nome.endswith(".json"):
            with open(os.path.join(_RULES_DIR, nome), "r", encoding="utf-8") as f:
                r = json.load(f)
            regras.append(r)
    return regras


def _texto_de_planilha_ou_csv(caminho: str, ext: str) -> str:
    """Extrai um texto representativo de XLS/HTML/CSV/XLSX para identificacao."""
    import pandas as pd
    try:
        if ext in ("xls", "html", "htm"):
            tabelas = pd.read_html(caminho)
            return "\n".join(t.to_string() for t in tabelas)
        if ext == "xlsx":
            dfs = pd.read_excel(caminho, sheet_name=None, header=None)
            return "\n".join(df.to_string() for df in dfs.values())
        if ext == "csv":
            with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
    except Exception:
        # tenta ler como texto bruto
        try:
            with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""
    return ""


def processar_arquivo(caminho: str, nome_arquivo: str = "", forcar_rule_key: str | None = None,
                      data_referencia: str | None = None) -> list[dict]:
    """
    Processa um arquivo e pode retornar UM ou MAIS resultados (ex.: PDF
    com extrato de dois fundos diferentes). Cada resultado contem:
      - sucesso: bool
      - banco, produto, rule_key, confianca
      - ocr_aplicado, metodo, aviso_ocr
      - dados: campos extraidos pelo parser
      - rule: regra carregada
      - erro: mensagem (se falhou)
    """
    nome_arquivo = nome_arquivo or os.path.basename(caminho)
    ext = os.path.splitext(nome_arquivo)[1].lower().lstrip(".")

    def _resultado_vazio():
        return {
            "arquivo": nome_arquivo, "sucesso": False, "erro": None,
            "ocr_aplicado": False, "metodo": None, "aviso_ocr": None,
            "banco": None, "produto": None, "rule_key": None, "confianca": 0,
            "dados": None, "rule": None,
        }

    resultado = _resultado_vazio()

    # 1. Extrair texto
    try:
        if ext == "pdf":
            res_ocr = ocr_mod.extrair_texto_pdf(caminho)
            texto = res_ocr["texto"]
            paginas = res_ocr["paginas"]
            resultado["ocr_aplicado"] = res_ocr["ocr_aplicado"]
            resultado["metodo"] = res_ocr["metodo"]
            resultado["aviso_ocr"] = res_ocr["aviso"]
        else:
            texto = _texto_de_planilha_ou_csv(caminho, ext)
            paginas = [texto]
            resultado["metodo"] = "planilha/csv"
    except Exception as e:
        resultado["erro"] = f"Falha ao extrair conteudo: {e}"
        return [resultado]

    if not (texto or "").strip() and ext != "pdf":
        resultado["erro"] = "Arquivo vazio ou ilegivel."
        return [resultado]

    # 2. Identificar
    if forcar_rule_key:
        rule = carregar_regra(forcar_rule_key)
        if rule:
            ident = {"rule_key": forcar_rule_key, "banco": rule["banco"],
                     "produto": rule["produto"], "confianca": 100, "origem": "manual"}
        else:
            ident = ident_mod.identificar(texto, nome_arquivo)
    else:
        ident = ident_mod.identificar(texto, nome_arquivo)

    if not ident["banco"]:
        resultado["erro"] = (
            "Nao foi possivel identificar o banco/produto deste extrato. "
            "Verifique se o arquivo e um extrato suportado ou selecione o produto manualmente."
        )
        if resultado["aviso_ocr"]:
            resultado["erro"] += f" ({resultado['aviso_ocr']})"
        return [resultado]

    parser_fn = _PARSER_POR_BANCO.get(ident["banco"])
    if not parser_fn:
        resultado["erro"] = f"Banco identificado ({ident['banco']}) sem parser disponivel."
        return [resultado]

    # 3. Parsear — passa competencia_alvo se data_referencia for informada
    extra_kwargs = {}
    if data_referencia:
        try:
            # data_referencia esperado como dd/mm/yyyy -> mm/yyyy
            partes = data_referencia.split("/")
            if len(partes) == 3:
                extra_kwargs["competencia_alvo"] = f"{partes[1]}/{partes[2]}"
        except Exception:
            pass

    try:
        dados_bruto = parser_fn(texto, paginas=paginas, caminho=caminho,
                                nome_arquivo=nome_arquivo, rule_key=ident["rule_key"],
                                **extra_kwargs)
    except Exception as e:
        resultado["erro"] = f"Falha ao processar o extrato ({ident['banco']}): {e}"
        return [resultado]

    # Normaliza para lista: parser pode retornar dict (1 produto) ou list[dict] (multi-produto)
    dados_lista = dados_bruto if isinstance(dados_bruto, list) else [dados_bruto]

    resultados = []
    for dados in dados_lista:
        r = _resultado_vazio()
        r["ocr_aplicado"] = resultado["ocr_aplicado"]
        r["metodo"] = resultado["metodo"]
        r["aviso_ocr"] = resultado["aviso_ocr"]
        r["confianca"] = ident["confianca"]

        rule_key_final = dados.get("rule_key") or ident["rule_key"]
        rule = carregar_regra(rule_key_final)
        if not rule:
            r["erro"] = f"Regra '{rule_key_final}' nao encontrada."
            resultados.append(r)
            continue

        r["rule_key"] = rule_key_final
        r["banco"] = rule["banco"]
        r["produto"] = rule["produto"]
        r["dados"] = dados
        r["rule"] = rule
        r["sucesso"] = True
        resultados.append(r)

    return resultados if resultados else [resultado]
