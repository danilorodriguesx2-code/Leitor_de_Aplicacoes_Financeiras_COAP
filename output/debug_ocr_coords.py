import sys
sys.path.insert(0, 'C:\\Apps\\Leitor_de_Aplica\u00e7\u00f5es_Financeiras')

import fitz
import pytesseract
from PIL import Image
import io

caminho = r'extratos\RENDE FACIL - OK.pdf'
doc = fitz.open(caminho)
page = doc[0]
pix = page.get_pixmap(dpi=220)
img = Image.open(io.BytesIO(pix.tobytes("png")))

data = pytesseract.image_to_data(img, lang='por', output_type=pytesseract.Output.DICT)

# Group by line_num (line within block) for row reconstruction
linhas = {}
for i in range(len(data['text'])):
    t = data['text'][i].strip()
    if not t:
        continue
    blk = data['block_num'][i]
    line = data['line_num'][i]
    key = (blk, line)
    if key not in linhas:
        linhas[key] = []
    linhas[key].append({
        'text': t,
        'x': data['left'][i],
        'y': data['top'][i],
        'conf': data['conf'][i],
    })

# Sort by y position and group into "rows" (within ~15px tolerance)
items = []
for key, words in sorted(linhas.items(), key=lambda kv: (kv[0][0], kv[0][1])):
    ys = [w['y'] for w in words]
    xy_text = ' | '.join([w['text'] + '@' + str(w['x']) for w in words])
    avg_y = int(sum(ys)/len(ys))
    items.append((avg_y, xy_text))

# Group by y-position (within tolerance of 20px)
tolerance = 20
rows = []
current_y = None
current_texts = []
for y, txt in items:
    if current_y is None:
        current_y = y
        current_texts = [txt]
    elif abs(y - current_y) <= tolerance:
        current_texts.append(txt)
    else:
        rows.append((current_y, '  ||  '.join(current_texts)))
        current_y = y
        current_texts = [txt]
if current_texts:
    rows.append((current_y, '  ||  '.join(current_texts)))

print('Linhas reconstruidas por coordenada Y:')
for y, txt in rows:
    print('y=' + str(y) + ': ' + txt[:200])
