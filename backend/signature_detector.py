"""
Signature position detection utilities.
Intelligently detect where signatures should be placed in PDF documents.
"""

import re
from typing import Optional
from PyPDF2 import PdfReader

# Try to import pdfplumber for text coordinate extraction
try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


# Keywords to search for signature placement (case-insensitive)
# Ordered by priority - medical-specific first
SIGNATURE_KEYWORDS = [
    # Medical-specific (highest priority)
    r"signature\s+of\s+physician",
    r"signature\s+of\s+doctor",
    r"physician'?s?\s*signature",
    r"doctor'?s?\s*signature",
    r"consulting\s+physician",
    r"attending\s+physician",
    r"treating\s+doctor",
    r"medical\s+officer\s*signature",
    r"surgeon'?s?\s*signature",
    r"specialist'?s?\s*signature",
    r"consultant\s*signature",
    r"clinician'?s?\s*signature",
    # General signature keywords
    r"authorized\s*signature",
    r"signature\s*:?",
    r"sign\s*here",
    r"signed\s*by\s*:?",
    r"authorized\s*by",
    r"approved\s*by",
    r"verified\s*by",
    r"_+\s*signature",  # Underlines before signature
    r"signature\s*_+",  # Signature followed by underlines
    # Hindi
    r"चिकित्सक\s*(?:के\s*)?हस्ताक्षर",  # Doctor's signature in Hindi
    r"डॉक्टर\s*(?:के\s*)?हस्ताक्षर",
    r"हस्ताक्षर",
    r"साइन",
    # Common patterns
    r"sign\s*:?\s*$",
    r"sig\s*:?\s*$",
]

# Compile patterns for efficiency
SIGNATURE_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in SIGNATURE_KEYWORDS]


def detect_signature_position(pdf_path: str) -> dict:
    """
    Detect the best position for signature placement in a PDF.

    Uses a hybrid approach:
    1. First, search for signature-related keywords in text
    2. If found, return coordinates near that text
    3. If not found, use heuristics (bottom of last page)

    Args:
        pdf_path: Path to the PDF file

    Returns:
        dict with:
            - found: bool - whether a signature location was detected
            - page: int - 0-indexed page number
            - x: float - x coordinate
            - y: float - y coordinate from top
            - width: float - suggested signature width
            - height: float - suggested signature height
            - confidence: str - 'high', 'medium', 'low'
            - method: str - detection method used
            - keyword: str - matched keyword (if any)
    """
    result = {
        'found': False,
        'page': 0,
        'x': 100,
        'y': 100,
        'width': 120,
        'height': 40,
        'confidence': 'low',
        'method': 'fallback',
        'keyword': None
    }

    try:
        # Get basic PDF info
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)

        if num_pages == 0:
            return result

        # Get last page dimensions for fallback
        last_page = reader.pages[-1]
        page_width = float(last_page.mediabox.width)
        page_height = float(last_page.mediabox.height)

        # Method 1: Try pdfplumber for precise text coordinates
        if HAS_PDFPLUMBER:
            detection = _detect_with_pdfplumber(pdf_path, num_pages)
            if detection['found']:
                return detection

        # Method 2: Search text content with PyPDF2 (less precise)
        detection = _detect_with_pypdf2(reader, num_pages, page_width, page_height)
        if detection['found']:
            return detection

        # Method 3: Fallback - place at bottom of last page (above typical footer)
        result['found'] = True
        result['page'] = num_pages - 1
        result['x'] = page_width * 0.1  # 10% from left
        result['y'] = page_height * 0.75  # 75% down the page
        result['width'] = 120
        result['height'] = 40
        result['confidence'] = 'low'
        result['method'] = 'fallback_bottom'

        return result

    except Exception as e:
        print(f"Error detecting signature position: {e}")
        return result


def _detect_with_pdfplumber(pdf_path: str, num_pages: int) -> dict:
    """Use pdfplumber to find text with coordinates."""
    result = {
        'found': False,
        'page': 0,
        'x': 100,
        'y': 100,
        'width': 120,
        'height': 40,
        'confidence': 'low',
        'method': 'pdfplumber',
        'keyword': None
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            # Search from last page backwards (signature usually at end)
            for page_idx in range(num_pages - 1, -1, -1):
                page = pdf.pages[page_idx]
                page_height = float(page.height)
                page_width = float(page.width)

                # Extract words with positions
                words = page.extract_words()
                if not words:
                    continue

                # Build text blocks for pattern matching
                text_content = page.extract_text() or ""

                # Check each pattern
                for pattern in SIGNATURE_PATTERNS:
                    match = pattern.search(text_content)
                    if match:
                        matched_text = match.group().lower().strip()

                        # Find the word position - look for signature-related words
                        for word in words:
                            word_text = word['text'].lower()
                            if any(kw in word_text for kw in ['signature', 'sign', 'हस्ताक्षर', 'authorized', 'physician', 'doctor']):
                                # Position signature ABOVE the label text (so it appears on the signature line)
                                sig_height = 40  # Smaller default height
                                sig_width = 120  # Smaller default width

                                result['found'] = True
                                result['page'] = page_idx
                                result['x'] = float(word['x0'])
                                result['y'] = float(word['top']) - sig_height - 5  # ABOVE the text
                                result['width'] = sig_width
                                result['height'] = sig_height
                                result['confidence'] = 'high'
                                result['method'] = 'keyword_match'
                                result['keyword'] = matched_text

                                # Ensure within page bounds
                                if result['x'] + result['width'] > page_width:
                                    result['x'] = page_width - result['width'] - 20
                                if result['y'] < 10:  # Don't go above page
                                    result['y'] = 10
                                if result['y'] + result['height'] > page_height:
                                    result['y'] = page_height - result['height'] - 20

                                return result

                # Look for horizontal lines (potential signature lines)
                lines = page.lines if hasattr(page, 'lines') else []
                for line in lines:
                    # Check if it's a horizontal line in bottom half
                    if line.get('top', 0) > page_height / 2:
                        line_width = abs(line.get('x1', 0) - line.get('x0', 0))
                        if line_width > 100:  # Significant horizontal line
                            result['found'] = True
                            result['page'] = page_idx
                            result['x'] = float(line.get('x0', 100))
                            result['y'] = float(line.get('top', page_height - 100)) - 45  # Above the line
                            result['width'] = 120
                            result['height'] = 40
                            result['confidence'] = 'medium'
                            result['method'] = 'line_detection'
                            return result

    except Exception as e:
        print(f"pdfplumber detection error: {e}")

    return result


def _detect_with_pypdf2(reader: PdfReader, num_pages: int, page_width: float, page_height: float) -> dict:
    """Fallback detection using PyPDF2 text extraction."""
    result = {
        'found': False,
        'page': 0,
        'x': 100,
        'y': 100,
        'width': 120,
        'height': 40,
        'confidence': 'low',
        'method': 'pypdf2',
        'keyword': None
    }

    try:
        # Search from last page backwards
        for page_idx in range(num_pages - 1, -1, -1):
            page = reader.pages[page_idx]
            text = page.extract_text() or ""

            # Check each pattern
            for pattern in SIGNATURE_PATTERNS:
                match = pattern.search(text)
                if match:
                    matched_text = match.group().lower().strip()

                    # We found a keyword but don't have exact coordinates
                    # Place signature at reasonable position on this page
                    result['found'] = True
                    result['page'] = page_idx

                    # Estimate position based on where keywords usually appear
                    # Place signature in bottom third, above where label would be
                    result['x'] = page_width * 0.1  # 10% from left
                    result['y'] = page_height * 0.70  # 70% down the page (above typical label)
                    result['width'] = 120
                    result['height'] = 40
                    result['confidence'] = 'medium'
                    result['method'] = 'text_search'
                    result['keyword'] = matched_text

                    return result

    except Exception as e:
        print(f"PyPDF2 detection error: {e}")

    return result


def detect_signature_positions_batch(pdf_paths: list[str]) -> list[dict]:
    """
    Detect signature positions for multiple PDFs.

    Args:
        pdf_paths: List of PDF file paths

    Returns:
        List of detection results
    """
    results = []
    for pdf_path in pdf_paths:
        result = detect_signature_position(pdf_path)
        result['pdf_path'] = pdf_path
        results.append(result)
    return results
