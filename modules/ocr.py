"""
Modulo de OCR e extracao de texto de PDFs.

Estrategia:
  1. Tenta extrair texto nativo (pdfplumber / PyMuPDF) - rapido.
  2. Se o PDF for escaneado (texto vazio/insuficiente), aplica OCR via
     PyMuPDF (render) + pytesseract. Faz fallback gracioso caso o
     Tesseract nao esteja instalado.
"""
from __future__ import annotations
import io
import logging
import os

logger = logging.getLogger(__name__)

# Limiar de caracteres para considerar que ha texto nativo suficiente
_MIN_TEXT_CHARS = 30


def _configurar_tesseract(pytesseract):
    """Aponta o pytesseract para uma instalacao configurada pelo ambiente."""
    comando = os.environ.get("TESSERACT_CMD")
    if comando:
        pytesseract.pytesseract.tesseract_cmd = comando
    return pytesseract


def _tesseract_disponivel() -> bool:
    try:
        import pytesseract
        _configurar_tesseract(pytesseract)
        pytesseract.get_tesseract_version()
        return True
    except Exception as e:  # pragma: no cover
        logger.warning("Tesseract indisponivel: %s", e)
        return False


def extrair_texto_pdf(caminho: str) -> dict:
    """
    Extrai texto de um PDF.

    Retorna dict com:
      - texto: texto completo concatenado
      - paginas: lista de textos por pagina
      - ocr_aplicado: bool
      - metodo: 'nativo' | 'ocr' | 'nativo+ocr'
      - aviso: mensagem opcional
    """
    texto_nativo, paginas_nativas = _extrair_nativo(caminho)
    total_chars = len(texto_nativo.strip())

    if total_chars >= _MIN_TEXT_CHARS:
        return {
            "texto": texto_nativo,
            "paginas": paginas_nativas,
            "ocr_aplicado": False,
            "metodo": "nativo",
            "aviso": None,
        }

    # PDF provavelmente escaneado -> tenta OCR
    if not _tesseract_disponivel():
        return {
            "texto": texto_nativo,
            "paginas": paginas_nativas,
            "ocr_aplicado": False,
            "metodo": "nativo",
            "aviso": (
                "PDF aparenta ser escaneado (sem texto nativo) e o Tesseract OCR "
                "nao esta instalado. Instale 'tesseract-ocr' e 'tesseract-ocr-por' "
                "para processar este arquivo."
            ),
        }

    texto_ocr, paginas_ocr = _aplicar_ocr(
        caminho,
        dpi=int(os.environ.get("OCR_DPI", "220")),
    )
    return {
        "texto": texto_ocr,
        "paginas": paginas_ocr,
        "ocr_aplicado": True,
        "metodo": "ocr",
        "aviso": None,
    }


def _extrair_nativo(caminho: str):
    """Extrai texto nativo usando pdfplumber (fallback PyMuPDF)."""
    paginas = []
    try:
        import pdfplumber
        with pdfplumber.open(caminho) as pdf:
            for page in pdf.pages:
                paginas.append(page.extract_text() or "")
        if any(p.strip() for p in paginas):
            return "\n".join(paginas), paginas
    except Exception as e:
        logger.warning("pdfplumber falhou: %s", e)

    # Fallback PyMuPDF
    try:
        import fitz
        paginas = []
        doc = fitz.open(caminho)
        for page in doc:
            paginas.append(page.get_text() or "")
        doc.close()
        return "\n".join(paginas), paginas
    except Exception as e:
        logger.warning("PyMuPDF falhou: %s", e)

    return "", []


def _aplicar_ocr(caminho: str, dpi: int = 220, lang: str = "por"):
    """Renderiza paginas e aplica OCR. Fallback de idioma para 'eng'."""
    import fitz
    import pytesseract
    from PIL import Image

    _configurar_tesseract(pytesseract)
    config = os.environ.get("TESSERACT_CONFIG", "--psm 3")
    paginas = []
    doc = fitz.open(caminho)
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        try:
            txt = pytesseract.image_to_string(img, lang=lang, config=config)
        except Exception:
            # idioma 'por' pode nao estar instalado -> usa default
            txt = pytesseract.image_to_string(img, config=config)
        paginas.append(txt or "")
    doc.close()
    return "\n".join(paginas), paginas


def extrair_texto(caminho: str, extensao: str) -> dict:
    """Interface generica: roteia por tipo de arquivo."""
    extensao = (extensao or "").lower().lstrip(".")
    if extensao == "pdf":
        return extrair_texto_pdf(caminho)
    # Para outros formatos, o parser le diretamente; retorna vazio aqui.
    return {"texto": "", "paginas": [], "ocr_aplicado": False, "metodo": "nao_aplicavel", "aviso": None}
