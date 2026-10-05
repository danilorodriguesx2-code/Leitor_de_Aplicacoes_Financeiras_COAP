# Changelog

## 2026-10-05

### Corrigido

- Leitura do Itaú Aplic Aut Mais em PDF, `.aspx` e HTML com extensão `.xls`.
- Leitura do Sicoob RDC Flexível em PDFs digitalizados.
- OCR configurável por ambiente, incluindo idioma português, resolução e modo de página.
- Parser Sicoob para valores em coluna separada, saldos separados e erros comuns de OCR.
- Exportação CSV ERP consolidada com um único cabeçalho e um único BOM.
- Competência ERP aplicada antes do agrupamento por CNPJ e competência.

### Adicionado

- Testes de regressão para Itaú, Sicoob, OCR e CSV ERP.
- Identificação visual `Sicoob · RDC Automatico (Encerrada)` para a aplicação encerrada no mês 8.
- Script de inicialização para VPS em `scripts/start_vps.sh`.
- Script de health check em `scripts/healthcheck.sh`.
- Documentação de implantação e operação em `docs/`.
- `.gitignore` para impedir publicação de uploads, exportações, caches e bytecode.
- CI do GitHub Actions para compilação e testes em Python 3.13.
