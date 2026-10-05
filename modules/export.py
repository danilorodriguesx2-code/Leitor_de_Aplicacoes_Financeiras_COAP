"""Exportacao de lancamentos contabeis para Excel, CSV e TXT."""
from __future__ import annotations
import io
import csv
import datetime as dt
import pandas as pd


COLUNAS = [
    ("data", "Data"),
    ("banco", "Banco"),
    ("produto", "Produto"),
    ("tipo", "Tipo"),
    ("debito", "Conta Debito"),
    ("debito_cod_red", "Cod.Red Debito"),
    ("credito", "Conta Credito"),
    ("credito_cod_red", "Cod.Red Credito"),
    ("valor", "Valor"),
    ("historico", "Historico"),
    ("complemento", "Complemento"),
]


def lancamentos_para_df(lancamentos: list) -> pd.DataFrame:
    rows = []
    for l in lancamentos:
        rows.append({titulo: l.get(chave, "") for chave, titulo in COLUNAS})
    df = pd.DataFrame(rows, columns=[t for _, t in COLUNAS])
    return df


def _fmt_valor(v) -> str:
    try:
        return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v)


def exportar_excel(lancamentos: list, conferencias: list | None = None) -> bytes:
    df = lancamentos_para_df(lancamentos)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Lancamentos")
        if conferencias:
            dfc = pd.DataFrame(conferencias)
            dfc.to_excel(writer, index=False, sheet_name="Conferencia")
        # ajusta largura das colunas
        ws = writer.sheets["Lancamentos"]
        for i, col in enumerate(df.columns, start=1):
            largura = max(12, min(40, int(df[col].astype(str).map(len).max() if len(df) else 12) + 2))
            ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = largura
    return buf.getvalue()


def exportar_csv(lancamentos: list) -> bytes:
    df = lancamentos_para_df(lancamentos)
    # formata valor em pt-BR
    if "Valor" in df.columns:
        df = df.copy()
        df["Valor"] = df["Valor"].map(_fmt_valor)
    buf = io.StringIO()
    df.to_csv(buf, index=False, sep=";", quoting=csv.QUOTE_MINIMAL)
    return buf.getvalue().encode("utf-8-sig")


def _parse_data_br(value: str):
    try:
        return dt.datetime.strptime(str(value).strip(), "%d/%m/%Y").date()
    except (TypeError, ValueError):
        return None


def _eh_ultimo_dia_mes(value: str) -> bool:
    data = _parse_data_br(value)
    if data is None:
        return False
    proximo_mes = data.replace(day=28) + dt.timedelta(days=4)
    ultimo = proximo_mes - dt.timedelta(days=proximo_mes.day)
    return data == ultimo


def competencia_erp(lancamentos: list, data_padrao: str) -> str:
    """Escolhe a competencia do LOT do ERP.

    A data de origem so permanece quando todos os lancamentos do lote estao
    no ultimo dia do respectivo mes. Caso contrario, usa a data padrao do
    cabecalho do painel.
    """
    datas = [
        str(l.get("data_ref") or l.get("data") or "").strip()
        for l in lancamentos
    ]
    if datas and len(set(datas)) == 1 and _eh_ultimo_dia_mes(datas[0]):
        return datas[0]
    return str(data_padrao or "").strip()


def exportar_csv_erp(lancamentos: list, data_ref: str, cnpj: str, lote: str = "900", filial: str = "1") -> bytes:
    """
    Layout para importacao direta no ERP.
    Gera LOT (cabecalho do lote) + 2 linhas CON por lancamento (D e C).
    """
    header = (
        "TIPO;COD LOTE;VLR CONTABIL LOTE;COMPETENCIA;COD FILIAL;"
        "COD CONTA CONTABIL;VLR CONTABIL;PARTIDA;COD HISTORICO;COMPLEMENTO;"
        "COD CENTRO CUSTO;VLR CENTRO CUSTO;CPF/CNPJ;IMOBILIZADO;VLR IMOBILIZADO"
    )

    total_debitos = sum(l.get("valor", 0.0) for l in lancamentos)
    comp = data_ref.strip()

    def _fmt_valor_us(v):
        try:
            return f"{float(v):.2f}"
        except Exception:
            return str(v)

    cnpj_pad = cnpj.zfill(14)

    buf = io.StringIO()
    buf.write(header + "\n")

    # linha de cabecalho do lote
    buf.write(
        f"LOT;{lote};{_fmt_valor_us(total_debitos)};{comp};;;;;;;;;;;;;;\n"
    )

    for l in lancamentos:
        valor_s = _fmt_valor_us(l.get("valor", 0.0))
        hist = l.get("historico", "")
        deb = l.get("debito", "")
        cred = l.get("credito", "")
        compl = l.get("complemento", "")

        # linha de debito
        buf.write(f"CON;;;{''.rjust(11)};{filial};{deb};{valor_s};D;{hist};{compl};;;{cnpj_pad};;\n")
        # linha de credito
        buf.write(f"CON;;;{''.rjust(11)};{filial};{cred};{valor_s};C;{hist};{compl};;;{cnpj_pad};;\n")

    return buf.getvalue().encode("utf-8-sig")


def consolidar_csv_erp(partes: list[bytes]) -> bytes:
    """Une lotes ERP mantendo um unico cabecalho e um unico BOM."""
    header = ""
    linhas = []
    for parte in partes:
        texto = parte.decode("utf-8-sig")
        bloco = texto.splitlines()
        if not bloco:
            continue
        if not header:
            header = bloco[0]
        linhas.extend(linha for linha in bloco[1:] if linha.strip())
    if not header:
        return b""
    return ("\n".join([header, *linhas]) + "\n").encode("utf-8-sig")


def exportar_txt(lancamentos: list) -> bytes:
    """
    Layout TXT posicional/delimitado por '|' para importacao contabil generica:
    DATA|DEBITO|CREDITO|VALOR|HISTORICO|COMPLEMENTO
    """
    linhas = ["DATA|DEBITO|CREDITO|VALOR|HISTORICO|COMPLEMENTO"]
    for l in lancamentos:
        linhas.append("|".join([
            str(l.get("data", "")),
            str(l.get("debito", "")),
            str(l.get("credito", "")),
            _fmt_valor(l.get("valor", 0)),
            str(l.get("historico", "")),
            str(l.get("complemento", "")),
        ]))
    return ("\n".join(linhas) + "\n").encode("utf-8")
