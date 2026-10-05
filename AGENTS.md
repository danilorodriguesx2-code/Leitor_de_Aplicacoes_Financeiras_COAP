# AGENTS.md

## Propósito

Este arquivo fornece o contexto mínimo para agentes que alterem o projeto. O README e os documentos em `docs/` são a fonte operacional completa.

## Início rápido

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
streamlit run app/main.py
```

Na VPS, use o ambiente virtual persistente e o script `scripts/start_vps.sh`. Consulte [docs/DEPLOY_VPS.md](docs/DEPLOY_VPS.md).

## Arquitetura

- Entrada da interface: `app/main.py`.
- Pipeline: `modules/processor.py` coordena extração, identificação, parser, cálculo, contabilidade e exportação.
- OCR: `modules/ocr.py`, com extração nativa antes do Tesseract.
- Parsers: `parsers/bb.py`, `parsers/itau.py`, `parsers/sicoob.py`, `parsers/sicredi.py` e `parsers/xp.py`.
- Identificação: `modules/identifier.py`.
- Regras contábeis: JSONs em `rules/`, uma regra por produto.
- Testes: `tests/`.
- Execução VPS: `scripts/start_vps.sh` e `scripts/healthcheck.sh`.

## Regras de alteração

- Preserve os `rule_key` e os contratos dos parsers.
- Não altere regra contábil sem teste de regressão e revisão do impacto em débito, crédito, histórico e impostos.
- Trate os arquivos enviados como dados não confiáveis.
- Não execute macros ou conteúdo ativo.
- Não registre conteúdo integral de extratos, dados pessoais, tokens ou credenciais.
- Não versionar uploads reais, PDFs, planilhas, exportações, caches ou `__pycache__`.
- O processamento é local. Não adicionar integração externa sem autorização explícita.
- Em mudanças de interface, altere o rótulo visual sem mudar o identificador técnico quando a solicitação for apenas de comunicação.
- O texto `Sicoob · RDC Automatico (Encerrada)` é um lembrete visual. O `rule_key` `sicoob_rdc_automatico` permanece inalterado.

## Formatos e casos especiais

- PDF deve ser identificado pelo conteúdo quando a extensão for suspeita.
- Itaú Aplic Aut Mais pode chegar como PDF, `.aspx` ou HTML com extensão `.xls`.
- Sicoob RDC Flexível pode ser PDF digitalizado, com valores em coluna separada e erros OCR em letras de crédito.
- OCR exige Tesseract e idioma português para documentos digitalizados.
- A extensão não é prova suficiente do formato real.

## Exportação ERP

- A competência é preservada no último dia do mês.
- Em outras datas, usa-se a data padrão do painel.
- O agrupamento do ERP é por CNPJ e competência.
- O CSV ERP consolidado deve ter um único cabeçalho e um único BOM no início.
- Cada `LOT` contém duas linhas `CON` por lançamento.

## Validação obrigatória

Antes de concluir qualquer alteração:

```bash
python -m pytest -q
python -m compileall -q app modules parsers tests
git diff --check
```

Para mudanças na interface ou implantação, também execute:

```bash
./scripts/healthcheck.sh http://127.0.0.1:8520/
```

E valide visualmente o fluxo afetado quando o aceite envolver a tela.

## Publicação

Antes do commit:

```bash
git status --short
git diff --stat
git diff --check
```

Confirme que somente arquivos de código, testes e documentação necessários serão publicados. Não incluir credenciais, extratos reais ou artefatos de execução.
