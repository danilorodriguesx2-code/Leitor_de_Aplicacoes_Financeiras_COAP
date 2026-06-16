import sys
sys.path.insert(0, 'C:\\Apps\\Leitor_de_Aplica\u00e7\u00f5es_Financeiras')
from modules import processor, calculator, accounting

resultados = processor.processar_arquivo(r'extratos\RENDE FACIL - OK.pdf')
resultado = resultados[0] if resultados else {"sucesso": False, "erro": "Sem resultados"}
if not resultado['sucesso']:
    print('ERRO:', resultado.get('erro', 'Desconhecido'))
else:
    rule = resultado['rule']
    dados = resultado['dados']
    data_ref = dados.get('data_referencia', '')
    print('Banco:', rule['banco'])
    print('Produto:', rule['produto'])
    print('Data Ref:', data_ref)
    print('CNPJ:', rule.get('cnpj', ''))

    print()
    skip = ('movimentacoes', 'avisos', 'campos_extra')
    for k, v in sorted(dados.items()):
        if k not in skip:
            print('  ' + k + ': ' + str(v))

    if dados.get('campos_extra'):
        print()
        print('--- Campos Extra ---')
        for k, v in dados['campos_extra'].items():
            print('  ' + k + ': ' + str(v))

    calc = calculator.calcular(rule, dados)
    print()
    print('--- Calculo ---')
    for passo in calc['memoria']:
        print('Tipo:', passo['tipo'])
        print('Formula:', passo['formula'])
        print('Descricao:', passo['descricao'])
        for p in passo['passos']:
            print('  ' + p['campo'] + ': ' + str(p['valor']) + ' (' + p['origem'] + ')')
        print('Resultado:', passo['resultado'])
        print()

    lancs = accounting.gerar_lancamentos(rule, calc['valores'], data_ref)
    print('--- Lancamentos Gerados ---')
    for l in lancs:
        print('  ' + l['debito'] + ' D | ' + l['credito'] + ' C | ' + str(l['valor']) + ' | hist:' + str(l['historico']))
