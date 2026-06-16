import sys
sys.path.insert(0, 'C:\\Apps\\Leitor_de_Aplica\u00e7\u00f5es_Financeiras')
from modules import processor, calculator, accounting

resultados = processor.processar_arquivo(r'extratos\EXTRATO RF LP CORP BANCOS.pdf')
print('Numero de resultados:', len(resultados))
print()
for i, res in enumerate(resultados):
    if not res['sucesso']:
        print('ERRO:', res.get('erro'))
        continue
    dados = res['dados']
    rule = res['rule']
    data_ref = dados.get('data_referencia', '')
    print('=== {} ==='.format(rule['produto']))
    print('  Saldo Anterior:', dados.get('saldo_anterior'))
    print('  Saldo Atual:', dados.get('saldo_atual'))
    print('  Resgates:', dados.get('resgates'))
    print('  IRRF:', dados.get('irrf_retido_mes'))
    print('  IOF:', dados.get('iof_retido_mes'))
    calc = calculator.calcular(rule, dados)
    print('  Rendimento calculado:', calc['valores'].get('rendimento'))
    for passo in calc['memoria']:
        print('  Formula:', passo.get('formula', '?'))
        for p in passo.get('passos', []):
            print('    ' + p['campo'] + ' = ' + str(p['valor']) + ' (' + p['origem'] + ')')
        print('  Resultado:', passo['resultado'])
    lancs = accounting.gerar_lancamentos(rule, calc['valores'], data_ref)
    for l in lancs:
        print('  Lanc: ' + l['debito'] + ' D | ' + l['credito'] + ' C | ' + str(l['valor']))
    print()
