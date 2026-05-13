"""
OCRService (Simplified)
-----------------------
Extracts text from CNI images using pytesseract (Tesseract OCR).
Parses only 3 fields from Cameroonian CNI:
  - nom (surname)
  - prenom (given name)
  - numero_cni (CNI number)

Install requirements:
  pip install pytesseract pillow
  apt-get install tesseract-ocr tesseract-ocr-fra
"""
import re
import logging
from PIL import Image

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

logger = logging.getLogger(__name__)

# Tesseract config — use French + English, PSM 6
TESS_CONFIG = '--oem 3 --psm 6 -l fra+eng'


class OCRService:

    def extract_text(self, image_path: str) -> str:
        """Run OCR on an image file and return the raw text."""
        if not TESSERACT_AVAILABLE:
            logger.warning("pytesseract not installed — returning empty OCR text")
            return ""
        try:
            img  = Image.open(image_path)
            text = pytesseract.image_to_string(img, config=TESS_CONFIG)
            logger.info("OCR extracted %d chars from %s", len(text), image_path)
            return text
        except Exception as exc:
            logger.error("OCR failed for %s: %s", image_path, exc)
            return ""

    def parse_cni_fields(self, recto_text: str, verso_text: str = "") -> dict:
        """
        Parse OCR text from a Cameroonian CNI.
        Returns a dict with only: nom, prenom, numero_cni.
        """
        combined = recto_text + "\n" + verso_text
        return {
            "nom":        self._extract_nom(recto_text),
            "prenom":     self._extract_prenom(recto_text),
            "numero_cni": self._extract_numero_cni(combined),
        }

    # ── Private parsers ────────────────────────────────────────────

    def _extract_nom(self, text: str) -> str:
        patterns = [
            r'(?:NOM|SURNAME|NOM DE FAMILLE)[:\s]+([A-ZÉÈÊËÀÂÙÎÏ\-\s]+)',
        ]
        return self._first_match(text.upper(), patterns)

    def _extract_prenom(self, text: str) -> str:
        patterns = [
            r'(?:PR[ÉE]NOM[S]?|GIVEN NAME[S]?|FIRST NAME[S]?)[:\s]+([A-ZÉÈÊËÀÂÙÎÏ\-\s]+)',
        ]
        return self._first_match(text.upper(), patterns)

    def _extract_numero_cni(self, text: str) -> str:
        # Cameroonian CNI numbers: 9 digits or alphanumeric
        patterns = [
            r'\b([0-9]{9})\b',              # 9-digit format
            r'\b([A-Z]{1,3}[0-9]{6,9})\b', # alpha-numeric format
        ]
        for p in patterns:
            m = re.search(p, text.upper())
            if m:
                return m.group(1)
        return ""

    def _first_match(self, text: str, patterns: list) -> str:
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""
