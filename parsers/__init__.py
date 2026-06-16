"""
Pacote de parsers especificos por banco.

Cada parser expõe a funcao `parse(texto, paginas, caminho, nome_arquivo) -> dict`
retornando um dicionario padronizado de campos extraidos.
"""
from __future__ import annotations
import re
import unicodedata

__all__ = [
    "br_to_float", "norm", "achar_valor", "achar_data",
    "campo_padrao",
]


def norm(s: str) -> str:
    """Remove acentos e coloca em maiusculas (para busca robusta)."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.upper()


def br_to_float(valor) -> float:
    """
    Converte string de numero no formato brasileiro para float.
    Ex: '1.234.567,89' -> 1234567.89 ; 'R$ 80.785,24' -> 80785.24
    Aceita sufixo C (credito, +) / D (debito, sinal mantido positivo aqui).
    Retorna 0.0 se nao for possivel converter.
    """
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        try:
            v = float(valor)
            if v != v:  # NaN
                return 0.0
            return v
        except Exception:
            return 0.0
    s = str(valor).strip()
    if not s:
        return 0.0
    # remove rotulos
    s = s.replace("R$", "").replace("r$", "").strip()
    # remove sufixo C/D
    suffix = ""
    m = re.search(r"([CD])\s*$", s)
    if m:
        suffix = m.group(1)
        s = s[: m.start()].strip()
    # negativo entre parenteses
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    if s.startswith("-"):
        neg = True
        s = s[1:]
    # mantem apenas digitos, ponto e virgula
    s = re.sub(r"[^0-9.,]", "", s)
    if not s:
        return 0.0
    # formato BR: ponto = milhar, virgula = decimal
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # sem virgula: pode ter ponto como decimal (ex 962.91) -> mantem
        # mas se houver multiplos pontos, sao milhares
        if s.count(".") > 1:
            s = s.replace(".", "")
    try:
        v = float(s)
    except ValueError:
        return 0.0
    if neg:
        v = -v
    return v


_RE_DATA = re.compile(r"(\d{2}/\d{2}/\d{4})")


def achar_data(texto: str, default: str = "") -> str:
    """Retorna a ultima data dd/mm/aaaa encontrada (geralmente a de referencia)."""
    datas = _RE_DATA.findall(texto or "")
    return datas[-1] if datas else default


def achar_valor(texto: str, rotulo: str, depois=True) -> float:
    """
    Procura um rotulo e retorna o primeiro numero apos (ou antes) dele na mesma linha.
    Busca tolerante a acentos.
    """
    alvo = norm(rotulo)
    for linha in (texto or "").splitlines():
        if alvo in norm(linha):
            nums = re.findall(r"[-(]?\s*[\d.]+,\d{2}\)?[CD]?", linha)
            if not nums:
                nums = re.findall(r"\d[\d.,]*", linha)
            if nums:
                return br_to_float(nums[-1] if depois else nums[0])
    return 0.0


def campo_padrao(banco, produto, rule_key, data_ref) -> dict:
    """Estrutura base de retorno de um parser."""
    return {
        "banco": banco,
        "produto": produto,
        "rule_key": rule_key,
        "data_referencia": data_ref,
        # campos financeiros (default 0)
        "saldo_atual": 0.0,
        "saldo_anterior": 0.0,
        "saldo_bruto": 0.0,
        "rendimentos_provisionados_atual": 0.0,
        "rendimentos_provisionados_anterior": 0.0,
        "provisao_irrf_atual": 0.0,
        "provisao_irrf_anterior": 0.0,
        "provisao_iof_atual": 0.0,
        "provisao_iof_anterior": 0.0,
        "rendimentos_pagos_mes": 0.0,
        "irrf_retido_mes": 0.0,
        "iof_retido_mes": 0.0,
        "resgates": 0.0,
        "aplicacoes": 0.0,
        "movimentacoes": [],
        "campos_extra": {},
        "avisos": [],
    }
