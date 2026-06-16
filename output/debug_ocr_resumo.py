import sys, re, io
sys.path.insert(0, 'C:\\Apps\\Leitor_de_Aplica\u00e7\u00f5es_Financeiras')

import fitz
import pytesseract
from PIL import Image

def extrair_valores_resumo(caminho):
    """Extrai valores do Resumo do mes usando coordenadas OCR."""
    doc = fitz.open(caminho)
    page = doc[0]
    pix = page.get_pixmap(dpi=220)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    data = pytesseract.image_to_data(img, lang='por', output_type=pytesseract.Output.DICT)

    # Collect words with coordinates
    words = []
    for i in range(len(data['text'])):
        t = data['text'][i].strip()
        if not t:
            continue
        words.append({
            'text': t,
            'x': data['left'][i],
            'y': data['top'][i],
            'w': data['width'][i],
            'h': data['height'][i],
            'conf': int(data['conf'][i]),
        })

    # Group into rows by y-coordinate (tolerance 15px)
    tolerance = 15
    rows = []
    sorted_words = sorted(words, key=lambda w: (w['y'], w['x']))
    for w in sorted_words:
        placed = False
        for row in rows:
            if abs(row['y'] - w['y']) <= tolerance:
                row['words'].append(w)
                row['y'] = (row['y'] + w['y']) // 2
                placed = True
                break
        if not placed:
            rows.append({'y': w['y'], 'words': [w]})

    # Sort rows by y
    rows.sort(key=lambda r: r['y'])

    # Find resumo section and extract
    resumo_start = None
    resumo_end = None
    for i, row in enumerate(rows):
        texto = ' '.join([w['text'] for w in row['words']])
        if 'Resumo' in texto and 'mes' in texto.lower():
            resumo_start = i
        if 'Historico' in texto or 'movimentacao' in texto.lower():
            resumo_end = i
            break

    if resumo_start is None:
        return {}

    if resumo_end is None:
        resumo_end = len(rows)

    # Within resumo section, find labels and their values
    # Values are to the right of labels (higher x)
    # Labels: Saldo bruto em, Aplicacoes, Resgates, IR, IOF, Rendimentos
    labels_alvo = {
        'rendimento': [r'Rendimentos?'],
        'aplicacoes': [r'Aplica'],
        'resgates': [r'Resgates'],
        'irrf': [r'IR\b'],
        'iof': [r'IOF\b'],
        'saldo_anterior': [r'Saldo bruto.*\d{2}/\d{2}/\d{4}'],
        'saldo_bruto': [r'Saldo bruto.*\d{2}/\d{2}/\d{4}'],
    }

    # Find the row with the "totals" values (the column of numbers on the right)
    # These are at high x coordinates
    valores_encontrados = {}
    for i in range(resumo_start, len(rows)):
        row = rows[i]
        # Get words with high x (right side of page)
        right_words = [w for w in row['words'] if w['x'] > 500]
        for w in right_words:
            # Check if it's a Brazilian number
            if re.match(r'^[\d.]+,\d{2}$', w['text']):
                # Find which label this value corresponds to
                # Look for labels at similar y
                label = None
                for j in range(resumo_start, len(rows)):
                    if j == i:
                        continue
                    other_row = rows[j]
                    if abs(other_row['y'] - row['y']) > tolerance * 3:
                        continue
                    other_text = ' '.join([ow['text'] for ow in other_row['words']])
                    if re.search(r'Rendimentos?', other_text, re.IGNORECASE):
                        label = 'rendimento'
                    elif re.search(r'Aplica', other_text, re.IGNORECASE):
                        label = 'aplicacoes'
                    elif re.search(r'Resgates', other_text, re.IGNORECASE):
                        label = 'resgates'
                    elif re.search(r'\bIR\b', other_text):
                        label = 'irrf'
                    elif re.search(r'\bIOF\b', other_text):
                        label = 'iof'

    # Alternative: just look for patterns in the rows text
    for i in range(resumo_start, min(resumo_start + 15, len(rows))):
        row = rows[i]
        texto = ' '.join([w['text'] for w in row['words']])
        m = re.search(r'Rendimentos?[^0-9]*([\d.]+,\d{2})', texto, re.IGNORECASE)
        if m:
            valores_encontrados['rendimento'] = m.group(1)
            break

    return valores_encontrados

caminho = r'extratos\RENDE FACIL - OK.pdf'
res = extrair_valores_resumo(caminho)
print('Valores encontrados:', res)
