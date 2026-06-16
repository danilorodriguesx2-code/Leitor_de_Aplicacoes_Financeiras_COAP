import sys, re, io
sys.path.insert(0, 'C:\\Apps\\Leitor_de_Aplica\u00e7\u00f5es_Financeiras')

import fitz
import pytesseract
from PIL import Image

caminho = r'extratos\RENDE FACIL - OK.pdf'
doc = fitz.open(caminho)
page = doc[0]
pix = page.get_pixmap(dpi=220)
img = Image.open(io.BytesIO(pix.tobytes("png")))
data = pytesseract.image_to_data(img, lang='por', output_type=pytesseract.Output.DICT)

# Collect all words with coordinates, grouped into precise rows (5px tolerance)
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
    })

# Group by precise y
tolerance = 8
rows = []
sorted_w = sorted(words, key=lambda w: (w['y'], w['x']))
for w in sorted_w:
    placed = False
    for row in rows:
        if abs(row['y'] - w['y']) <= tolerance:
            row['words'].append(w)
            row['y'] = (row['y'] + w['y']) // 2
            placed = True
            break
    if not placed:
        rows.append({'y': w['y'], 'words': [w]})

rows.sort(key=lambda r: r['y'])

# Print all rows with their y-position and text
for row in rows:
    # Sort words by x
    row['words'].sort(key=lambda w: w['x'])
    texto = ' | '.join([w['text'] + '@' + str(w['x']) for w in row['words']])
    print('y=' + str(row['y']) + ': ' + texto)
