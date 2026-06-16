import sys, re
sys.path.insert(0, 'C:\\Apps\\Leitor_de_Aplica\u00e7\u00f5es_Financeiras')
from modules import ocr

res = ocr.extrair_texto_pdf(r'extratos\RENDE FACIL - OK.pdf')
texto = res['texto']

# Find all numbers in Brazilian format
nums = re.findall(r'[\d.]+,\d{2}', texto)
print('Todos os numeros encontrados:')
for n in nums:
    for i, linha in enumerate(texto.splitlines()):
        if n in linha:
            print('  ' + n + ' (linha ' + str(i) + ': ' + linha.strip()[:80] + ')')
            break

print()
# Find lines with values that could be rendimento (666.28)
for i, linha in enumerate(texto.splitlines()):
    if '666' in linha or '692' in linha or '1.202' in linha:
        print('Linha ' + str(i) + ': ' + repr(linha[:100]))
