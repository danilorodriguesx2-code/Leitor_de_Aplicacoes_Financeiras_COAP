# Operação e critérios de validação

## Fluxo diário

1. Confirme a data padrão no cabeçalho do painel.
2. Envie os extratos do período.
3. Confirme banco, produto, método de leitura e data de referência.
4. Revise os valores principais: saldo anterior, saldo atual, saldo bruto, rendimento, IRRF, IOF, aplicações e resgates.
5. Revise a memória de cálculo.
6. Revise os lançamentos contábeis e a conferência de saldos.
7. Gere os arquivos necessários.
8. Abra o arquivo exportado antes de importar no ERP.
9. Registre divergências e preserve o arquivo original fora do repositório.

## Produtos encerrados

O Sicoob RDC Automático foi encerrado no mês 8. O painel exibe:

```text
Sicoob · RDC Automatico (Encerrada)
```

Esse texto é somente um alerta visual para evitar a cobrança de novos extratos ao financeiro. O identificador técnico continua `sicoob_rdc_automatico`; nenhuma regra contábil ou parser foi alterado por essa marcação.

## Extratos Sicoob RDC Flexível

Os extratos podem ser PDFs digitalizados. A leitura exige Tesseract com português. O parser trata:

- valores na mesma linha da data e do histórico;
- valores em coluna separada;
- leitura OCR de `C` como `€`;
- saldos do resumo em bloco separado;
- apropriações de CM, aplicações, resgates e retenções de IRRF/IOF.

Após o processamento, confirme se o método exibido é `ocr` quando o PDF for imagem.

## Extratos Itaú Aplic Aut Mais

O produto pode chegar em mais de um formato:

- PDF;
- PDF com extensão `.aspx`;
- HTML exportado com extensão `.xls`.

O sistema identifica PDF pelo conteúdo `%PDF-` e identifica a tabela HTML pelo conteúdo real, não apenas pela extensão. Não renomeie o arquivo para alterar o conteúdo.

## Regra de competência ERP

A competência é definida antes do agrupamento dos lotes:

- último dia do mês: mantém a data original;
- qualquer outro dia: usa a data padrão do painel.

O agrupamento é por CNPJ e competência. Assim, o mesmo CNPJ pode gerar mais de um `LOT` quando houver competências diferentes.

O CSV ERP consolidado deve conter:

- um único cabeçalho;
- um único BOM UTF-8 no início;
- uma linha `LOT` por grupo;
- duas linhas `CON` por lançamento;
- total do `LOT` igual à soma dos débitos e créditos do grupo.

## Critérios de conferência do CSV ERP

Antes da importação, confira:

- cabeçalho aparece somente uma vez;
- nenhuma linha começa com BOM no meio do arquivo;
- quantidade de `LOT` corresponde às combinações de CNPJ e competência;
- soma do valor dos lotes corresponde aos lançamentos;
- cada lançamento tem uma linha débito e uma linha crédito;
- débito e crédito têm o mesmo valor;
- CNPJ, conta, histórico e filial estão preenchidos;
- competência está no campo correto da linha `LOT`;
- valores usam ponto decimal no formato exigido pelo importador ERP.

## Tratamento de erro

### PDF digitalizado não processa

Verifique:

```bash
$TESSERACT_CMD --version
$TESSERACT_CMD --list-langs
```

A lista deve conter `por`. Também confirme `TESSDATA_PREFIX` e `LD_LIBRARY_PATH` quando o Tesseract estiver instalado fora do sistema.

### Produto não identificado

1. Confirme se o conteúdo é um extrato suportado.
2. Verifique a extensão real e o cabeçalho do arquivo.
3. Tente selecionar o produto manualmente no painel.
4. Preserve uma cópia do arquivo para criar teste de regressão.

### Valores zerados ou incompatíveis

1. Não importe o arquivo no ERP.
2. Compare o extrato original com a memória de cálculo.
3. Confirme o método `nativo`, `ocr` ou `planilha/csv`.
4. Reproduza com teste automatizado antes de alterar a regra.
5. Nunca corrija o valor apenas na apresentação sem localizar a origem no parser ou na regra.

### Aplicação não responde

```bash
./scripts/healthcheck.sh http://127.0.0.1:8520/
pgrep -af 'streamlit run app/main.py'
```

Confirme também o endereço de bind, a porta e se o cliente está conectado à Tailscale.

## Validação mínima antes de liberar

```bash
python -m pytest -q
python -m compileall -q app modules parsers tests
git diff --check
./scripts/healthcheck.sh http://127.0.0.1:8520/
```

Para mudanças de interface, confirme visualmente:

- nome dos produtos;
- upload dos formatos afetados;
- resultado por arquivo;
- memória de cálculo;
- exportações individuais;
- exportação consolidada;
- CSV ERP.
