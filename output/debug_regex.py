import sys, re
sys.path.insert(0, 'C:\\Apps\\Leitor_de_Aplica\u00e7\u00f5es_Financeiras')
from modules import ocr

res = ocr.extrair_texto_pdf(r'extratos\RENDE FACIL - OK.pdf')
texto = res['texto']

# Find lines containing "rendimento" (case insensitive)
for i, linha in enumerate(texto.splitlines()):
    if 'rendimento' in linha.lower():
        print('Linha ' + str(i) + ': ' + repr(linha))

print()
print('--- Testando regex ---')
# Original regex
pat_old = r"Rendimento no m\w+s:\s*R?\$?\s*([\d.]+,\d{2})"
# Fixed regex
pat_new = r"Rendimentos? no m\w+s:\s*R?\$?\s*([\d.]+,\d{2})"

m_old = re.search(pat_old, texto, re.IGNORECASE)
m_new = re.search(pat_new, texto, re.IGNORECASE)

print('Match old:', m_old.group(1) if m_old else 'NENHUM')
print('Match new:', m_new.group(1) if m_new else 'NENHUM')

# Let me also check direct substring
print()
if 'Rendimentos no m\u00eas' in texto:
    print('ENCONTROU: Rendimentos no m\u00eas')
if 'Rendimento no m\u00eas' in texto:
    print('ENCONTROU: Rendimento no m\u00eas')

# Search with various patterns
for pat_name, pat in [
    ('Rendimento no m', r'Rendimento no m'),
    ('Rendimentos no m', r'Rendimentos no m'),
    ('Rendimento', r'Rendimento'),
    ('Rendimentos', r'Rendimentos'),
]:
    m = re.search(pat, texto, re.IGNORECASE)
    print(pat_name + ':', m.group(0) if m else 'NENHUM')
