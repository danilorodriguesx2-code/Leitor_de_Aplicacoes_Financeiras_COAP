# Contábil Financeiro

Aplicação Streamlit para processar extratos de aplicações financeiras, identificar banco e produto, extrair valores, calcular rendimentos e impostos, gerar lançamentos contábeis e exportar os resultados para Excel, CSV, TXT e CSV ERP.

O processamento é local. Os arquivos enviados não são transmitidos para serviços externos.

## Escopo atual

Bancos e produtos suportados:

- Banco do Brasil: CDB DI, Rende Fácil, RF LP Corp Bancos e RF Simples Ágil.
- Itaú: Aplic Aut Mais e Itauvest.
- Sicoob: RDC Flexível e RDC Automático.
- Sicredi: Sicredinvest, Sicredinvest Evolutivo, Sicredinvest Automático, Poupança Tradicional e Sicredinvest.
- XP: XP Investimentos, incluindo seleção mensal pela data de lançamentos.

Formatos aceitos:

- PDF com texto nativo.
- PDF digitalizado, mediante Tesseract OCR com idioma português.
- PDF baixado com extensão `.aspx`, quando o conteúdo real começa com `%PDF-`.
- XLS, XLSX, CSV, HTML e HTM.
- O Itaú pode fornecer o Aplic Aut Mais como HTML exportado com extensão `.xls`; o conteúdo é detectado e lido como tabela.

## Arquitetura

```text
upload
  -> modules/processor.py
  -> extração nativa ou OCR
  -> modules/identifier.py
  -> parser do banco em parsers/
  -> regra JSON em rules/
  -> modules/calculator.py
  -> modules/accounting.py
  -> exportação em modules/export.py
```

Diretórios principais:

- `app/main.py`: interface Streamlit.
- `modules/`: OCR, pipeline, cálculos, contabilidade e exportação.
- `parsers/`: parsers específicos de cada instituição.
- `rules/`: regras contábeis por produto, sem credenciais.
- `tests/`: testes automatizados e regressões de formatos reais.
- `scripts/`: execução e verificação da aplicação na VPS.
- `docs/`: operação, homologação e critérios de implantação.
- `extratos/`: uploads temporários, limpos ao iniciar.
- `output/`: arquivos gerados localmente, não versionados.

## Instalação local

### Requisitos

- Python 3.13 recomendado.
- Git.
- Dependências Python de `requirements.txt`.
- Tesseract e idioma português para PDFs digitalizados.
- Poppler é recomendado quando ferramentas externas de conversão de PDF forem necessárias.

### Linux ou macOS

```bash
git clone https://github.com/danilorodriguesx2-code/Leitor_de_Aplicacoes_Financeiras_COAP.git
cd Leitor_de_Aplicacoes_Financeiras_COAP
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Dependências OCR em Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-por poppler-utils
```

Execução local:

```bash
streamlit run app/main.py
```

A aplicação abre, por padrão, em `http://localhost:8501`.

### Windows

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app/main.py
```

Instale o Tesseract para Windows e configure `TESSERACT_CMD` caso o executável não esteja no `PATH`.

## Execução na VPS

A aplicação deve permanecer restrita à rede privada. Não publique diretamente a porta do Streamlit no IP público.

Critérios mínimos de implantação:

1. Debian 12/13 ou Ubuntu 22.04/24.04.
2. Python 3.13 disponível.
3. Repositório clonado em um diretório persistente.
4. Ambiente virtual separado do Python do sistema.
5. Dependências instaladas dentro do ambiente virtual.
6. Tesseract com `por.traineddata` disponível para extratos digitalizados.
7. Tailscale conectado quando o acesso for privado.
8. Processo vinculado a `127.0.0.1` ou ao endereço Tailscale, nunca ao IP público sem autenticação e HTTPS.
9. Porta definida explicitamente, atualmente `8520` no ambiente COAP.
10. Testes, compilação, health check e validação da interface concluídos antes do uso operacional.

Procedimento detalhado para a VPS: [docs/DEPLOY_VPS.md](docs/DEPLOY_VPS.md).

Execução pelo script do projeto:

```bash
cd /opt/data/Leitor_de_Aplicacoes_Financeiras_COAP
VENV_DIR=/opt/data/.venvs/leitor-financeiro \
BIND_ADDRESS=127.0.0.1 PORT=8520 ./scripts/start_vps.sh
```

Para acesso privado via Tailscale, substitua `BIND_ADDRESS` pelo endereço Tailscale da VPS, sem usar o IP público.

Verificação de disponibilidade:

```bash
./scripts/healthcheck.sh http://127.0.0.1:8520/
```

## Fluxo operacional

1. Configure a data padrão dos lançamentos no painel.
2. Envie um ou mais extratos.
3. Confirme banco e produto identificados.
4. Se o produto exigir, envie também o extrato anterior.
5. Revise memória de cálculo, lançamentos e conferência de saldos.
6. Gere os arquivos individualmente ou de forma consolidada.
7. Para o ERP, valide o cabeçalho `LOT`, a competência, os totais e as linhas `CON` antes da importação.

Procedimentos operacionais e troubleshooting: [docs/OPERACAO.md](docs/OPERACAO.md).

## OCR

O pipeline tenta primeiro extrair texto nativo. Quando o PDF não tem texto suficiente, renderiza as páginas e usa Tesseract.

Variáveis opcionais:

```bash
export TESSERACT_CMD=/caminho/para/tesseract
export TESSDATA_PREFIX=/caminho/para/tessdata
export LD_LIBRARY_PATH=/caminho/para/libs:$LD_LIBRARY_PATH
export TESSERACT_CONFIG="--psm 3"
export OCR_DPI=160
```

O `OCR_DPI=160` é adequado para os extratos Sicoob RDC Flexível validados. Outros documentos podem exigir outro valor.

Sem Tesseract, PDFs com texto nativo continuam funcionando. PDFs digitalizados serão sinalizados como não processados automaticamente.

## Exportação ERP

O CSV ERP utiliza o layout:

- uma linha `LOT` por combinação de CNPJ e competência;
- duas linhas `CON` por lançamento, débito e crédito;
- um único cabeçalho no arquivo consolidado;
- um único BOM UTF-8 no início do arquivo.

Regra de competência:

- lançamento no último dia do mês: preserva a data original;
- lançamento em qualquer outro dia: utiliza a data padrão do cabeçalho do painel;
- competências diferentes geram lotes diferentes, mesmo para o mesmo CNPJ.

A aplicação Sicoob RDC Automático foi encerrada no mês 8. O painel exibe `Sicoob · RDC Automatico (Encerrada)` como lembrete visual. O `rule_key`, parser, regra contábil e cálculo permanecem inalterados.

## Testes e validação

Execute a suíte completa:

```bash
python -m pytest -q
python -m compileall -q app modules parsers tests
git diff --check
```

Critérios de aceite antes da operação:

- todos os testes passam;
- nenhum erro de compilação;
- JSONs em `rules/` carregam corretamente;
- aplicação inicia sem exceção;
- health check retorna HTTP 200;
- interface mostra upload e produtos suportados;
- pelo menos um extrato nativo e um digitalizado são processados;
- exportações são abertas e conferidas;
- CSV ERP tem um único cabeçalho e totais conciliados;
- acesso público à porta não é necessário nem permitido.

O CI do GitHub executa a suíte em Python 3.13: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Segurança e privacidade

- Não versionar extratos reais, PDFs, planilhas, exportações, tokens, senhas, chaves ou arquivos `.env`.
- Não executar macros ou conteúdo ativo de documentos.
- Tratar uploads como dados não confiáveis.
- Manter a aplicação na rede privada até existir autenticação pública, HTTPS e controle de acesso.
- Conferir `git status`, `.gitignore` e o diff antes de publicar.

## Contribuição

Antes de criar um commit:

```bash
git status --short
python -m pytest -q
python -m compileall -q app modules parsers tests
git diff --check
```

Descreva alterações de parser com um caso de regressão reproduzível. Alterações em `rules/` devem explicar o impacto contábil e ser revisadas antes da publicação.
