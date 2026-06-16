# 💰 Contábil Financeiro

Aplicação **Streamlit** para processar extratos de aplicações financeiras de bancos
brasileiros, identificar automaticamente o **banco/produto**, extrair os campos
financeiros, calcular **rendimento, IRRF e IOF**, gerar os **lançamentos contábeis**
e exportar para **Excel, CSV e TXT**.

Sem banco de dados e sem microsserviços — tudo roda localmente, em memória/arquivos.

---

## ✅ Bancos e produtos suportados

| Banco   | Produtos |
|---------|----------|
| Sicredi | Sicredinvest, Sicredinvest Evolutivo, Sicredinvest Automático, Poupança |
| Sicoob  | RDC Flexível, RDC Automático |
| Banco do Brasil | RF Simples Ágil, RF LP Corp Bancos, Rende Fácil, CDB DI |
| Itaú    | Aplicação Automática Mais, Itauvest |
| XP      | XP Investimentos (relatório XPerformance) — seleção do mês baseada na data de lançamentos informada |

Formatos aceitos: **PDF** (incluindo digitalizados via OCR), **XLS/XLSX**, **CSV**, **HTML**.

---

## 🧱 Estrutura do projeto

```
contabil_financeiro/
├── app/
│   └── main.py            # Interface Streamlit
├── parsers/               # Extração de campos por banco
│   ├── sicredi.py
│   ├── sicoob.py
│   ├── bb.py
│   ├── itau.py
│   ├── xp.py
│   └── __init__.py        # utilidades (br_to_float, norm, etc.)
├── rules/                 # Regras contábeis em JSON (1 por produto)
├── modules/
│   ├── ocr.py             # extração de texto + OCR (tesseract)
│   ├── identifier.py      # identificação automática do banco/produto
│   ├── calculator.py      # cálculo de rendimento/IRRF/IOF + memória de cálculo
│   ├── accounting.py      # geração dos lançamentos contábeis e conferência
│   ├── export.py          # exportação Excel/CSV/TXT
│   └── processor.py       # pipeline completo (arquivo → texto → regra → dados)
├── extratos/              # uploads temporários (limpos automaticamente ao iniciar)
├── output/                # exportações geradas
├── requirements.txt
└── README.md
```

---

## ⚙️ Instalação

### 1. Dependências do sistema (OCR)

O OCR de PDFs digitalizados usa o **Tesseract** com o idioma português e o `pdftoppm` (Poppler):

```bash
# Debian / Ubuntu
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-por poppler-utils

# macOS (Homebrew)
brew install tesseract tesseract-lang poppler
```

> O app funciona sem o Tesseract para PDFs com texto nativo; o OCR só é necessário
> para extratos digitalizados (imagem).

### 2. Dependências Python

```bash
cd contabil_financeiro
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## ▶️ Como executar

```bash
cd contabil_financeiro
streamlit run app/main.py
```

O Streamlit abrirá no navegador (por padrão em `http://localhost:8501`).

### Uso

1. **Defina a data de lançamentos** na barra lateral — usada como referência para
   selecionar o mês correto na tabela "Evolução Patrimonial" dos extratos XP.
2. **Envie os extratos** (arraste e solte um ou vários arquivos).
3. O app identifica o banco/produto. Se necessário, **selecione manualmente** o produto.
4. **Extrato do mês anterior** (Sicredi): se o produto exigir saldos do mês anterior,
   o app exibe um uploader — envie o PDF do período anterior para preenchimento
   automático dos campos de provisão/rendimento, sem necessidade de digitação manual.
5. Confira a **memória de cálculo**, os **lançamentos contábeis** e a **conferência de saldos**.
6. **Baixe** o resultado em Excel, CSV ou TXT — individual ou consolidado.

---

## 🧮 Regras contábeis

Cada produto tem um arquivo JSON em `rules/` descrevendo:

- contas de débito/crédito por tipo (rendimento, IRRF, IOF);
- históricos contábeis (591 = rendimento, 592 = IRRF, 593 = IOF);
- fórmulas de cálculo (avaliadas com segurança a partir dos campos extraídos);
- tratamento de **estorno** (inverte débito/crédito quando o valor é negativo).

Para adicionar/ajustar um produto, edite o JSON correspondente — não é preciso mexer no código.

---

## 🔒 Privacidade

Todo o processamento é local. Nenhum dado do extrato é enviado para serviços externos.
