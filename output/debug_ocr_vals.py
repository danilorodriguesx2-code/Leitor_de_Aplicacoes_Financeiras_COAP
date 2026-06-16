import sys
sys.path.insert(0, 'C:\\Apps\\Leitor_de_Aplica\u00e7\u00f5es_Financeiras')
from parsers.bb import _extrair_resumo_por_coordenadas

vals = _extrair_resumo_por_coordenadas(r'extratos\RENDE FACIL - OK.pdf')
for k, v in sorted(vals.items()):
    print(k + ' = ' + str(v))
