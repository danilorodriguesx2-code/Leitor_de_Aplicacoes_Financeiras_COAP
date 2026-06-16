import sys
sys.path.insert(0, 'C:\\Apps\\Leitor_de_Aplica\u00e7\u00f5es_Financeiras')

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

caminho = r'extratos\RENDE FACIL - OK.pdf'
doc = fitz.open(caminho)
page = doc[0]

# Render page to image
pix = page.get_pixmap(dpi=220)
img = Image.open(io.BytesIO(pix.tobytes("png")))

# Get detailed OCR data with coordinates
data = pytesseract.image_to_data(img, lang='por', output_type=pytesseract.Output.DICT)

print('Total elementos OCR:', len(data['text']))

# Group by block_num to see text blocks
blocos = {}
for i in range(len(data['text'])):
    blk = data['block_num'][i]
    if blk not in blocos:
        blocos[blk] = []
    t = data['text'][i].strip()
    if t:
        blocos[blk].append({
            'text': t,
            'x': data['left'][i],
            'y': data['top'][i],
            'w': data['width'][i],
            'h': data['height'][i],
        })

print()
print('Blocos de texto encontrados:')
for blk_num, items in sorted(blocos.items()):
    # Get average y position for this block
    ys = [it['y'] for it in items]
    xs = [it['x'] for it in items]
    texto = ' '.join([it['text'] for it in items])
    print('Bloco ' + str(blk_num) + ': y~' + str(int(sum(ys)/len(ys))) + ' x~' + str(int(sum(xs)/len(xs))) + ' -> ' + texto[:120])
