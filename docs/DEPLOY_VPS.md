# Implantação na VPS

Este documento define os critérios para executar o Contábil Financeiro na VPS COAP sem expor a aplicação diretamente à internet.

## 1. Critérios de infraestrutura

Obrigatórios:

- Linux Debian 12/13 ou Ubuntu 22.04/24.04.
- Python 3.13.
- Git.
- Tailscale ativo quando o acesso for privado.
- Diretório persistente para o clone, o ambiente virtual e logs.
- Porta local definida, atualmente `8520` no ambiente COAP.
- Memória suficiente para Streamlit, pandas, PyMuPDF e OCR. O consumo depende do tamanho e da quantidade de PDFs.

O processo não deve ser vinculado ao IP público sem uma camada de autenticação e HTTPS.

## 2. Diretórios recomendados

Exemplo usado na VPS COAP:

```text
/opt/data/Leitor_de_Aplicacoes_Financeiras_COAP   clone do projeto
/opt/data/.venvs/leitor-financeiro                ambiente virtual
/opt/data/cache/scratch                           arquivos temporários
/opt/data/cache/scratch/leitor_financeiro_streamlit.log
/opt/data/cache/scratch/leitor_financeiro_streamlit.err.log
```

Não copie credenciais para o repositório. Use o ambiente protegido do host ou o gerenciador de processos.

## 3. Preparação do ambiente

```bash
git clone https://github.com/danilorodriguesx2-code/Leitor_de_Aplicacoes_Financeiras_COAP.git /opt/data/Leitor_de_Aplicacoes_Financeiras_COAP
cd /opt/data/Leitor_de_Aplicacoes_Financeiras_COAP
python3.13 -m venv /opt/data/.venvs/leitor-financeiro
/opt/data/.venvs/leitor-financeiro/bin/python -m pip install -r requirements.txt
```

Em ambientes sem `pip` no Python do sistema, use `uv` para instalar no ambiente virtual:

```bash
uv pip install --python /opt/data/.venvs/leitor-financeiro/bin/python -r requirements.txt
```

A aplicação foi validada com Python 3.13.5, Streamlit 1.65.0, pandas 3.0.6, PyMuPDF 1.28.2, Pillow 12.3.0 e openpyxl 3.1.5.

## 4. OCR no host

Para instalação privilegiada em Debian/Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-por poppler-utils
```

Validar:

```bash
tesseract --version
tesseract --list-langs
```

A saída deve conter `por`.

### Instalação sem root

Quando o host não permite instalar pacotes no sistema, mantenha o Tesseract em um diretório do usuário ou de ferramentas da VPS e configure:

```bash
export TESSERACT_CMD=/opt/data/tools/tesseract/usr/bin/tesseract
export TESSDATA_PREFIX=/opt/data/tools/tesseract/usr/share/tesseract-ocr/5/tessdata
export LD_LIBRARY_PATH=/opt/data/tools/tesseract/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}
export TESSERACT_CONFIG="--psm 3"
export OCR_DPI=160
```

O executável deve responder a:

```bash
"$TESSERACT_CMD" --version
"$TESSERACT_CMD" --list-langs
```

O idioma português deve estar instalado no diretório informado por `TESSDATA_PREFIX`.

## 5. Testes antes de iniciar

```bash
cd /opt/data/Leitor_de_Aplicacoes_Financeiras_COAP
/opt/data/.venvs/leitor-financeiro/bin/python -m pytest -q
/opt/data/.venvs/leitor-financeiro/bin/python -m compileall -q app modules parsers tests
git diff --check
```

Critério de aprovação: todos os testes passam, a compilação termina sem erro e não há erro de whitespace.

## 6. Início do Streamlit

O script `scripts/start_vps.sh` usa variáveis para não fixar o endereço da rede:

```bash
cd /opt/data/Leitor_de_Aplicacoes_Financeiras_COAP
VENV_DIR=/opt/data/.venvs/leitor-financeiro \
BIND_ADDRESS=127.0.0.1 PORT=8520 ./scripts/start_vps.sh
```

Para acesso privado pela Tailscale:

```bash
BIND_ADDRESS=<IP-TAILSCALE-DA-VPS> PORT=8520 ./scripts/start_vps.sh
```

Não substitua o endereço por um IP público sem configurar autenticação e HTTPS.

Parâmetros usados pelo script:

- `BIND_ADDRESS`, padrão `127.0.0.1`.
- `PORT`, padrão `8520`.
- `TESSERACT_CMD`, opcional.
- `TESSDATA_PREFIX`, opcional.
- `LD_LIBRARY_PATH`, opcional.
- `TESSERACT_CONFIG`, padrão `--psm 3`.
- `OCR_DPI`, padrão `160` no script VPS.

## 7. Health check

```bash
./scripts/healthcheck.sh http://127.0.0.1:8520/
```

Critério de aprovação: retorno HTTP `200` e página Streamlit disponível.

Para acesso privado, execute o teste a partir de um dispositivo conectado à mesma tailnet, usando o endereço Tailscale da VPS.

## 8. Operação persistente

O processo deve ser gerenciado por systemd, supervisor, Docker ou outro gerenciador de processos da VPS. Quando for usado systemd, o serviço deve:

- executar com usuário sem privilégios;
- usar o ambiente virtual correto;
- carregar as variáveis de OCR;
- gravar logs fora do repositório;
- reiniciar somente após validação da nova versão;
- não expor secrets no arquivo de unidade.

Exemplo conceitual de comando, não de unidade completa:

```bash
Environment=BIND_ADDRESS=127.0.0.1
Environment=PORT=8520
ExecStart=/opt/data/Leitor_de_Aplicacoes_Financeiras_COAP/scripts/start_vps.sh
```

## 9. Atualização do projeto

Antes de atualizar:

```bash
cd /opt/data/Leitor_de_Aplicacoes_Financeiras_COAP
git status --short
git fetch origin
git log -1 --oneline
```

Depois de atualizar:

```bash
git pull --ff-only origin main
/opt/data/.venvs/leitor-financeiro/bin/python -m pip install -r requirements.txt
/opt/data/.venvs/leitor-financeiro/bin/python -m pytest -q
/opt/data/.venvs/leitor-financeiro/bin/python -m compileall -q app modules parsers tests
./scripts/healthcheck.sh http://127.0.0.1:8520/
```

Reinicie o processo somente após esses passos.

## 10. Critérios de rollback

Faça rollback se ocorrer qualquer um destes casos:

- testes falhando;
- aplicação não inicia;
- health check diferente de `200`;
- parser retorna erro em extrato conhecido;
- exportação ERP tem cabeçalho duplicado, BOM intermediário ou totais incorretos;
- porta privada deixa de responder;
- processo escuta no IP público sem autorização explícita.

Rollback básico:

```bash
git log --oneline -5
git checkout <commit-validado>
/opt/data/.venvs/leitor-financeiro/bin/python -m pytest -q
./scripts/healthcheck.sh http://127.0.0.1:8520/
```
