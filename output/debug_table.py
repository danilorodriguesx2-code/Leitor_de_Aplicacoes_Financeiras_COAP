import sys
sys.path.insert(0, 'C:\\Apps\\Leitor_de_Aplica\u00e7\u00f5es_Financeiras')

import pdfplumber

caminho = r'extratos\RENDE FACIL - OK.pdf'

with pdfplumber.open(caminho) as pdf:
    for i, page in enumerate(pdf.pages):
        print('=== Pagina ' + str(i+1) + ' ===')
        
        # Try table extraction
        tables = page.extract_tables()
        if tables:
            print('Tabelas encontradas:', len(tables))
            for j, table in enumerate(tables):
                print('--- Tabela ' + str(j+1) + ' ---')
                for linha in table:
                    print(linha)
        else:
            print('Nenhuma tabela encontrada')
        
        # Also try words
        words = page.extract_words()
        print()
        print('Words (primeiros 50):')
        for w in words[:50]:
            print('  x0=' + str(round(w['x0'],0)) + ' top=' + str(round(w['top'],0)) + ' text=' + w['text'])
