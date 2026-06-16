# AGENTS.md — Instruções para agentes de assistência (copilot/AI)

Propósito
- Fornecer a visão mínima e acionável que um agente precisa para ser produtivo neste repositório.
- Não substituir a documentação existente; linkar para o README e arquivos relevantes.

Rápido (instalação e execução)
- Configurar ambiente Python:
  - python3 -m venv .venv
  - Windows: .venv\Scripts\activate
  - pip install -r requirements.txt
- Dependências do sistema (somente para OCR em PDFs digitalizados):
  - tesseract-ocr (com idioma português)
  - poppler-utils (`pdftoppm`)
- Executar a aplicação:
  - streamlit run app/main.py

O que o agente deve saber primeiro
- Entry point: [app/main.py](app/main.py)
- Pipeline: `modules/processor.py` orquestra extração → identificação → parser → calculadora → contabilidade → export
- Parsers: cada banco tem um módulo em `parsers/` (bb.py, itau.py, sicredi.py, sicoob.py, xp.py)
- Regras contábeis: arquivos JSON em `rules/`, 1 arquivo por produto (não altere automaticamente sem validação)

Convenções e padrões importantes
- Parsers expõem funções utilitárias em `parsers/__init__.py` (norm, br_to_float, achar_valor, achar_data)
- `modules/identifier.py` contém padrões hardcoded para mapear texto → rule_key (ex: `sicredi_evolutivo`). Verificar antes de refatorar.
- Alterações em parsers ou em `modules/calculator.py` devem ser tratadas com cautela (não há testes automatizados).

Pontos de atenção (para revisões/PRs)
- Não assumir disponibilidade do Tesseract em CI; marcar como opcionais ou mockar OCR para testes.
- Evitar mudanças massivas em regex dos parsers sem exemplos de extratos para regressão.
- Validar JSON em `rules/` antes de aplicar mudanças que o consumam; erros aparecem somente em runtime.

Links úteis
- Documentação principal: [README.md](README.md)
- Entry point UI: [app/main.py](app/main.py)
- Pipeline: [modules/processor.py](modules/processor.py)
- Parsers: [parsers/](parsers/)
- Regras: [rules/](rules/)

Sugestões futuras
- Adicionar um conjunto mínimo de testes (pytest) para `parsers/` e `modules/calculator.py`.
- Criar um script de validação para os JSONs em `rules/`.

Se quiser, gero também um `/.github/copilot-instructions.md` com um resumo reduzido para PRs e revisão de código.
