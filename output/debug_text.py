import sys
sys.path.insert(0, 'C:\\Apps\\Leitor_de_Aplica\u00e7\u00f5es_Financeiras')
from modules import ocr

res = ocr.extrair_texto_pdf(r'extratos\RENDE FACIL - OK.pdf')
texto = res['texto']
linhas = texto.splitlines()

print('Linhas 15-40:')
for i in range(max(0, 15), min(len(linhas), 40)):
    print(str(i) + ': ' + repr(linhas[i]))
