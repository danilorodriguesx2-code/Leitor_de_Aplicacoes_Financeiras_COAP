"""
Contabil Financeiro - Processador de Extratos de Aplicacoes Financeiras
========================================================================
App Streamlit que le extratos de investimento (Sicredi, Sicoob, BB, Itau, XP),
identifica banco/produto automaticamente, extrai os campos financeiros,
calcula rendimento/IRRF/IOF a partir das regras (JSON), monta os lancamentos
contabeis e exporta para Excel/CSV/TXT.

Sem banco de dados e sem microsservicos: tudo roda em memoria/arquivos locais.
"""
from __future__ import annotations

import os
import sys
import io
import datetime as dt

# Garante que /contabil_financeiro esteja no sys.path para importar
# os pacotes 'parsers' e 'modules' quando o app roda via 'streamlit run'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import pandas as pd
import streamlit as st

from modules import processor, calculator, accounting, export

EXTRATOS_DIR = os.path.join(BASE_DIR, "extratos")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(EXTRATOS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _limpar_extratos():
    """Remove arquivos temporários da pasta extratos ao iniciar."""
    for fname in os.listdir(EXTRATOS_DIR):
        fpath = os.path.join(EXTRATOS_DIR, fname)
        try:
            if os.path.isfile(fpath):
                os.remove(fpath)
        except Exception:
            pass


_limpar_extratos()

st.set_page_config(
    page_title="Contabil Financeiro - Extratos de Aplicacoes",
    page_icon="💰",
    layout="wide",
)

# ----------------------------------------------------------------------------
# Helpers de formatacao
# ----------------------------------------------------------------------------
def fmt_brl(v) -> str:
    try:
        return "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v)


def fmt_num(v) -> str:
    try:
        return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v)


@st.cache_data(show_spinner=False)
def _regras_cache():
    return processor.listar_regras()


def opcoes_regras():
    regras = _regras_cache()
    opcoes = {"(identificar automaticamente)": None}
    for r in regras:
        rotulo = f"{r['banco']} - {r['produto']}  [{r['rule_key']}]"
        opcoes[rotulo] = r["rule_key"]
    return opcoes


# ----------------------------------------------------------------------------
# Cabecalho
# ----------------------------------------------------------------------------
st.title("💰 Contabil Financeiro")
st.caption(
    "Processamento de extratos de aplicacoes financeiras: identificacao automatica do "
    "banco/produto, calculo de rendimento, IRRF e IOF, geracao dos lancamentos contabeis "
    "e exportacao para Excel, CSV e TXT."
)

with st.sidebar:
    st.header("⚙️ Configuracoes")
    data_lcto = st.date_input(
        "Data dos lancamentos (padrao)",
        value=dt.date.today(),
        format="DD/MM/YYYY",
        help="Usada quando o extrato nao informa data de referencia.",
    )
    st.divider()
    st.subheader("Bancos / produtos suportados")
    for r in _regras_cache():
        irrf = "IRRF" if r.get("tem_irrf") else ""
        iof = "IOF" if r.get("tem_iof") else ""
        tags = " ".join([t for t in (irrf, iof) if t]) or "sem impostos"
        st.markdown(f"- **{r['banco']}** · {r['produto']}  \n  <small>{tags}</small>", unsafe_allow_html=True)
    st.divider()
    st.caption(
        "OCR automatico para PDFs digitalizados (requer tesseract-ocr + idioma por). "
        "Nenhum dado e enviado para servidores externos."
    )

st.markdown("### 1. Envie os extratos")
arquivos = st.file_uploader(
    "Arraste e solte os arquivos (PDF, XLS, XLSX, CSV, HTML). Varios arquivos sao aceitos.",
    type=["pdf", "xls", "xlsx", "csv", "html", "htm"],
    accept_multiple_files=True,
)

if not arquivos:
    st.info("Aguardando o envio de extratos. Voce pode enviar varios de uma vez.")
    st.stop()

opc_regras = opcoes_regras()

# Acumula lancamentos de todos os arquivos para exportacao consolidada.
todos_lancamentos = []
todas_conferencias = []

st.markdown("### 2. Resultados por arquivo")

for idx, arq in enumerate(arquivos):
    # Salva o upload; remove primeiro para evitar lock residual
    caminho = os.path.join(EXTRATOS_DIR, arq.name)
    try:
        if os.path.exists(caminho):
            os.remove(caminho)
        with open(caminho, "wb") as f:
            f.write(arq.getbuffer())
    except PermissionError:
        caminho = os.path.join(OUTPUT_DIR, arq.name)
        if os.path.exists(caminho):
            os.remove(caminho)
        with open(caminho, "wb") as f:
            f.write(arq.getbuffer())

    with st.container(border=True):
        st.markdown(f"#### 📄 {arq.name}")

        # Permite forcar o produto manualmente
        col_sel, col_info = st.columns([2, 3])
        with col_sel:
            escolha = st.selectbox(
                "Banco/Produto",
                options=list(opc_regras.keys()),
                index=0,
                key=f"regra_{idx}",
                help="Deixe em automatico para deteccao por conteudo, ou selecione manualmente.",
            )
        forcar = opc_regras[escolha]

        # Processa o arquivo
        with st.spinner("Processando..."):
            data_ref_str = data_lcto.strftime("%d/%m/%Y")
            resultados = processor.processar_arquivo(caminho, arq.name, forcar_rule_key=forcar,
                                                      data_referencia=data_ref_str)

        with col_info:
            if any(r["sucesso"] for r in resultados):
                nomes = " + ".join(
                    f"{r['banco']} · {r['produto']}" for r in resultados if r["sucesso"]
                )
                st.success(f"**{nomes}**  \nMetodo: {resultados[0]['metodo']}")
            else:
                st.error("Nao foi possivel processar automaticamente.")

        # Avisos de OCR / parser
        if resultados[0].get("ocr_aplicado"):
            st.warning(f"🔎 OCR aplicado (PDF digitalizado). {resultados[0].get('aviso_ocr') or ''}")
        elif resultados[0].get("aviso_ocr"):
            st.info(resultados[0]["aviso_ocr"])

        if not any(r["sucesso"] for r in resultados):
            st.error(resultados[0].get("erro") or "Erro desconhecido.")
            st.caption("Dica: tente selecionar o banco/produto manualmente acima.")
            continue

        for sub_idx, res in enumerate(resultados):
            if not res["sucesso"]:
                st.error(f"  {res.get('produto') or '?'}: {res.get('erro')}")
                continue

            sufixo = f"_{sub_idx}" if len(resultados) > 1 else ""
            dados = res["dados"]
            rule = res["rule"]

            if len(resultados) > 1:
                st.markdown(f"**▶ {rule['banco']} · {rule['produto']}**")

            if dados.get("aviso"):
                st.warning(f"⚠️ {dados['aviso']}")

            # ------------------------------------------------------------------
            # Campos do mês anterior — prioriza extração automática do extrato anterior
            # ------------------------------------------------------------------
            overrides = {}
            campos_manuais = {
                n: cfg for n, cfg in rule.get("campos_calculo", {}).items()
                if cfg.get("manual")
            }
            anterior_fields = {
                n: cfg for n, cfg in campos_manuais.items()
                if n.endswith("_anterior")
            }
            if campos_manuais:
                st.markdown("**Campos do mês anterior**")

                auto_filled = set()
                if anterior_fields:
                    prev_file = st.file_uploader(
                        "📂 Envie o extrato do mês anterior (preenchimento automático)",
                        type=["pdf", "xls", "xlsx", "csv", "html", "htm"],
                        key=f"prev_extract_{idx}{sufixo}",
                    )
                    if prev_file is not None:
                        with st.spinner("Processando extrato anterior..."):
                            prev_path = os.path.join(EXTRATOS_DIR, f"_prev_{prev_file.name}")
                            try:
                                if os.path.exists(prev_path):
                                    os.remove(prev_path)
                                with open(prev_path, "wb") as f:
                                    f.write(prev_file.getbuffer())
                            except PermissionError:
                                prev_path = os.path.join(OUTPUT_DIR, f"_prev_{prev_file.name}")
                                if os.path.exists(prev_path):
                                    os.remove(prev_path)
                                with open(prev_path, "wb") as f:
                                    f.write(prev_file.getbuffer())

                            prev_results = processor.processar_arquivo(prev_path, prev_file.name)
                            try:
                                os.remove(prev_path)
                            except Exception:
                                pass

                            prev_dados = None
                            for pr in prev_results:
                                if pr["sucesso"] and pr.get("dados"):
                                    prev_dados = pr["dados"]
                                    break

                            if prev_dados:
                                field_map = {
                                    "rend_prov_anterior": "rendimentos_provisionados_atual",
                                    "prov_irrf_anterior": "provisao_irrf_atual",
                                    "prov_iof_anterior": "provisao_iof_atual",
                                }
                                extra = prev_dados.get("campos_extra", {}) or {}
                                vals = {}
                                for ant_nome, source in field_map.items():
                                    if ant_nome in anterior_fields:
                                        v = prev_dados.get(source) or extra.get(source) or 0.0
                                        try:
                                            vals[ant_nome] = float(v)
                                        except (ValueError, TypeError):
                                            vals[ant_nome] = 0.0

                                if vals:
                                    overrides.update(vals)
                                    auto_filled.update(vals.keys())
                                    cols_m = st.columns(len(vals))
                                    for i, (k, v) in enumerate(vals.items()):
                                        cols_m[i].metric(
                                            anterior_fields[k]["label"],
                                            fmt_brl(v),
                                        )
                                    st.success("✅ Valores extraídos do extrato anterior e aplicados no cálculo.")

                # Inputs manuais — apenas para campos NÃO preenchidos automaticamente
                restantes = {n: c for n, c in campos_manuais.items() if n not in auto_filled}
                if restantes:
                    cols = st.columns(min(3, len(restantes)))
                    sugeridos = calculator.resolver_campos(rule, dados, overrides)
                    for i, (nome, cfg) in enumerate(restantes.items()):
                        valor_default = float(sugeridos.get(nome, {}).get("valor", 0.0) or 0.0)
                        with cols[i % len(cols)]:
                            v = st.number_input(
                                cfg.get("label", nome),
                                value=valor_default,
                                step=0.01,
                                format="%.2f",
                                key=f"manual_{idx}{sufixo}_{nome}",
                            )
                        overrides[nome] = v

            # ------------------------------------------------------------------
            # Calculo
            # ------------------------------------------------------------------
            calc = calculator.calcular(rule, dados, overrides)
            valores = calc["valores"]

            data_ref = dados.get("data_referencia") or data_lcto.strftime("%d/%m/%Y")

            # Resumo dos valores calculados
            mcols = st.columns(4)
            mcols[0].metric("Rendimento", fmt_brl(valores.get("rendimento", 0.0)))
            if rule.get("tem_irrf"):
                mcols[1].metric("IRRF", fmt_brl(valores.get("irrf", 0.0)))
            if rule.get("tem_iof"):
                mcols[2].metric("IOF", fmt_brl(valores.get("iof", 0.0)))
            mcols[3].metric("Data de referencia", data_ref)

            # ------------------------------------------------------------------
            # Memoria de calculo
            # ------------------------------------------------------------------
            with st.expander("🧮 Memoria de calculo", expanded=False):
                for passo in calc["memoria"]:
                    tipo = passo.get("tipo", "")
                    if passo.get("erro"):
                        st.error(f"{tipo}: {passo['erro']}")
                        continue
                    st.markdown(f"**{tipo.upper()}** — {passo.get('descricao', '')}")
                    st.code(passo.get("formula", ""), language="text")
                    if passo.get("passos"):
                        df_passos = pd.DataFrame([
                            {
                                "Campo": p["campo"],
                                "Valor": fmt_num(p["valor"]),
                                "Origem": p["origem"] + (" (manual)" if p["manual"] else ""),
                            }
                            for p in passo["passos"]
                        ])
                        st.dataframe(df_passos, hide_index=True, use_container_width=True)
                    st.markdown(f"➡️ **Resultado: {fmt_brl(passo.get('resultado', 0.0))}**")
                    st.divider()

            # ------------------------------------------------------------------
            # Lancamentos contabeis
            # ------------------------------------------------------------------
            lancs = accounting.gerar_lancamentos(rule, valores, data_ref)
            for l in lancs:
                l["banco"] = rule["banco"]
                l["produto"] = rule["produto"]
                l["cnpj"] = rule.get("cnpj", "")
                l["data_ref"] = data_ref

            st.markdown("**Lancamentos contabeis gerados:**")
            if lancs:
                df_l = pd.DataFrame([
                    {
                        "Data": l["data"],
                        "Tipo": l["tipo"],
                        "Debito": f"{l['debito']} ({l['debito_cod_red']})" if l['debito_cod_red'] else l['debito'],
                        "Credito": f"{l['credito']} ({l['credito_cod_red']})" if l['credito_cod_red'] else l['credito'],
                        "Valor": fmt_num(l["valor"]),
                        "Historico": l["historico"],
                        "Complemento": l["complemento"],
                    }
                    for l in lancs
                ])
                st.dataframe(df_l, hide_index=True, use_container_width=True)
                todos_lancamentos.extend(lancs)
            else:
                st.caption("Nenhum lancamento gerado (valores zerados).")

            # ------------------------------------------------------------------
            # Conferencia / balancete
            # ------------------------------------------------------------------
            conf = accounting.gerar_conferencia(rule, dados, valores)
            if conf:
                with st.expander("📊 Conferencia de saldos (balancete)", expanded=False):
                    df_c = pd.DataFrame([
                        {"Conta": c["conta"], "Descricao": c["descricao"], "Saldo": fmt_brl(c["valor"])}
                        for c in conf
                    ])
                    st.dataframe(df_c, hide_index=True, use_container_width=True)
                for c in conf:
                    c2 = dict(c)
                    c2["banco"] = rule["banco"]
                    c2["produto"] = rule["produto"]
                    todas_conferencias.append(c2)

            # ------------------------------------------------------------------
            # Downloads individuais (apenas se unico resultado)
            # ------------------------------------------------------------------
            if lancs and len(resultados) == 1:
                base_nome = os.path.splitext(arq.name)[0]
                dcols = st.columns(3)
                dcols[0].download_button(
                    "⬇️ Excel",
                    data=export.exportar_excel(lancs, conf),
                    file_name=f"{base_nome}_lancamentos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"xlsx_{idx}",
                    use_container_width=True,
                )
                dcols[1].download_button(
                    "⬇️ CSV",
                    data=export.exportar_csv(lancs),
                    file_name=f"{base_nome}_lancamentos.csv",
                    mime="text/csv",
                    key=f"csv_{idx}",
                    use_container_width=True,
                )
                dcols[2].download_button(
                    "⬇️ TXT",
                    data=export.exportar_txt(lancs),
                    file_name=f"{base_nome}_lancamentos.txt",
                    mime="text/plain",
                    key=f"txt_{idx}",
                    use_container_width=True,
                )

# ----------------------------------------------------------------------------
# Exportacao consolidada
# ----------------------------------------------------------------------------
if todos_lancamentos:
    st.markdown("### 3. Exportacao consolidada (todos os arquivos)")
    st.caption(f"Total de {len(todos_lancamentos)} lancamento(s) de {len(arquivos)} arquivo(s).")

    df_all = export.lancamentos_para_df(todos_lancamentos)
    st.dataframe(df_all, hide_index=True, use_container_width=True)

    ccols = st.columns(4)
    ccols[0].download_button(
        "⬇️ Excel consolidado",
        data=export.exportar_excel(todos_lancamentos, todas_conferencias),
        file_name="lancamentos_consolidados.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    ccols[1].download_button(
        "⬇️ CSV consolidado",
        data=export.exportar_csv(todos_lancamentos),
        file_name="lancamentos_consolidados.csv",
        mime="text/csv",
        use_container_width=True,
    )
    ccols[2].download_button(
        "⬇️ TXT consolidado",
        data=export.exportar_txt(todos_lancamentos),
        file_name="lancamentos_consolidados.txt",
        mime="text/plain",
        use_container_width=True,
    )

    # Agrupa lancamentos por CNPJ para gerar LOT separados por cnpj
    grupos = {}
    for l in todos_lancamentos:
        cnpj = l.get("cnpj", "")
        grupos.setdefault(cnpj, []).append(l)
    partes_erp = []
    for cnpj, lote_lancs in grupos.items():
        data_ref = lote_lancs[0].get("data_ref", "")
        partes_erp.append(export.exportar_csv_erp(lote_lancs, data_ref, cnpj))
    csv_erp_bytes = b"".join(partes_erp) if partes_erp else b""

    ccols[3].download_button(
        "⬇️ CSV ERP",
        data=csv_erp_bytes,
        file_name="lancamentos_erp.csv",
        mime="text/csv",
        use_container_width=True,
    )

    # Salva uma copia consolidada em /output
    try:
        with open(os.path.join(OUTPUT_DIR, "lancamentos_consolidados.xlsx"), "wb") as f:
            f.write(export.exportar_excel(todos_lancamentos, todas_conferencias))
    except Exception:
        pass
