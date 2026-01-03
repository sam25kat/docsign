"""
Signature position detection utilities.
Uses pdfplumber to detect where signatures should be placed in PDF documents.
Only searches for the word "signature" (case-insensitive).
Finds blank space nearest to the signature label for placement.
Searches from last page to first (signatures usually at end of documents).
Avoids center area of pages (signatures typically at bottom or sides).
Falls back to blank space on last page if no keyword found.
"""

import re
import random
import pdfplumber

# Pattern to match only the word "signature" (case-insensitive)
SIGNATURE_PATTERN = re.compile(r'\bsignature\b', re.IGNORECASE)

# Signature dimensions
SIG_WIDTH = 120
SIG_HEIGHT = 40
PADDING = 10  # Minimum padding from other elements
TEXT_HEIGHT = 30  # Space for "Digitally signed by" text below signature


def is_in_center_area(x, y, page_width, page_height, sig_width, sig_height):
    """
    Check if a position is in the center area of the page.
    Center area is defined as the middle 40% horizontally and middle 50% vertically.
    Signatures should typically be at the bottom or sides, not center.
    """
    # Define center zone
    center_x_start = page_width * 0.3
    center_x_end = page_width * 0.7
    center_y_start = page_height * 0.25
    center_y_end = page_height * 0.75

    # Check if signature center would be in the center zone
    sig_center_x = x + sig_width / 2
    sig_center_y = y + sig_height / 2

    in_center_x = center_x_start < sig_center_x < center_x_end
    in_center_y = center_y_start < sig_center_y < center_y_end

    return in_center_x and in_center_y


def find_blank_space_on_page(page, sig_width=SIG_WIDTH, sig_height=SIG_HEIGHT, avoid_center=True):
    """
    Find blank space on a page suitable for signature placement.
    Prefers bottom areas of the page, avoids center.

    Args:
        page: pdfplumber page object
        sig_width: Width of signature
        sig_height: Height of signature
        avoid_center: Whether to avoid center area

    Returns:
        dict with x, y coordinates of best blank space, or None if not found
    """
    page_width = float(page.width)
    page_height = float(page.height)

    # Extract words
    words = page.extract_words() or []

    # Build list of occupied rectangles
    occupied_rects = []
    for word in words:
        occupied_rects.append({
            'x0': float(word['x0']) - PADDING,
            'y0': float(word['top']) - PADDING,
            'x1': float(word['x1']) + PADDING,
            'y1': float(word['bottom']) + PADDING
        })

    # Also check for lines/rectangles
    try:
        lines = page.lines or []
        for line in lines:
            occupied_rects.append({
                'x0': float(line['x0']) - PADDING,
                'y0': float(line['top']) - PADDING,
                'x1': float(line['x1']) + PADDING,
                'y1': float(line['bottom']) + PADDING
            })

        rects = page.rects or []
        for rect in rects:
            occupied_rects.append({
                'x0': float(rect['x0']) - PADDING,
                'y0': float(rect['top']) - PADDING,
                'x1': float(rect['x1']) + PADDING,
                'y1': float(rect['bottom']) + PADDING
            })
    except:
        pass

    total_height = sig_height + TEXT_HEIGHT  # Account for text below signature

    def is_area_clear(x, y, width, height):
        """Check if a rectangular area is free from obstacles."""
        if x < PADDING or y < PADDING:
            return False
        if x + width > page_width - PADDING or y + height > page_height - PADDING:
            return False

        for rect in occupied_rects:
            if not (x + width < rect['x0'] or x > rect['x1'] or
                    y + height < rect['y0'] or y > rect['y1']):
                return False
        return True

    # Search for blank space with STRONG priority on bottom areas
    # Priority 1: Bottom-left quadrant (most common for signatures)
    # Priority 2: Bottom-right quadrant
    # Priority 3: Other areas only as last resort
    step = 15  # Finer step for better positioning

    # Priority 1: Bottom-left quadrant - search very thoroughly
    # Bottom 40% of page, left 50%
    bottom_start_y = page_height * 0.6
    for y in range(int(page_height - total_height - PADDING), int(bottom_start_y), -step):
        for x in range(PADDING, int(page_width * 0.5), step):
            if is_area_clear(x, y, sig_width, total_height):
                if not (avoid_center and is_in_center_area(x, y, page_width, page_height, sig_width, sig_height)):
                    return {'x': float(x), 'y': float(y)}

    # Priority 2: Bottom-right quadrant
    # Bottom 40% of page, right 50%
    for y in range(int(page_height - total_height - PADDING), int(bottom_start_y), -step):
        for x in range(int(page_width * 0.5), int(page_width - sig_width - PADDING), step):
            if is_area_clear(x, y, sig_width, total_height):
                if not (avoid_center and is_in_center_area(x, y, page_width, page_height, sig_width, sig_height)):
                    return {'x': float(x), 'y': float(y)}

    # Priority 3: Middle-left area (above bottom quadrant but still left side)
    for y in range(int(bottom_start_y), int(page_height * 0.3), -step):
        for x in range(PADDING, int(page_width * 0.3), step):
            if is_area_clear(x, y, sig_width, total_height):
                if not (avoid_center and is_in_center_area(x, y, page_width, page_height, sig_width, sig_height)):
                    return {'x': float(x), 'y': float(y)}

    # Priority 4: Middle-right area
    for y in range(int(bottom_start_y), int(page_height * 0.3), -step):
        for x in range(int(page_width * 0.7), int(page_width - sig_width - PADDING), step):
            if is_area_clear(x, y, sig_width, total_height):
                if not (avoid_center and is_in_center_area(x, y, page_width, page_height, sig_width, sig_height)):
                    return {'x': float(x), 'y': float(y)}

    # Last resort: any clear space on the page (excluding center)
    for y in range(int(page_height - total_height - PADDING), PADDING, -step):
        for x in range(PADDING, int(page_width - sig_width - PADDING), step):
            if is_area_clear(x, y, sig_width, total_height):
                if not is_in_center_area(x, y, page_width, page_height, sig_width, sig_height):
                    return {'x': float(x), 'y': float(y)}

    # Absolute last resort: even center if nothing else available
    for y in range(int(page_height - total_height - PADDING), PADDING, -step):
        for x in range(PADDING, int(page_width - sig_width - PADDING), step):
            if is_area_clear(x, y, sig_width, total_height):
                return {'x': float(x), 'y': float(y)}

    return None


def find_blank_space_near_keyword(page, keyword_word, all_words, sig_width=SIG_WIDTH, sig_height=SIG_HEIGHT):
    """
    Find the nearest blank space to place a signature near a keyword.
    Avoids center area of the page.

    Args:
        page: pdfplumber page object
        keyword_word: The word dict containing the keyword position
        all_words: List of all words on the page
        sig_width: Width of signature
        sig_height: Height of signature

    Returns:
        dict with x, y coordinates of best blank space, or None if not found
    """
    page_width = float(page.width)
    page_height = float(page.height)

    keyword_x = float(keyword_word['x0'])
    keyword_y = float(keyword_word['top'])
    keyword_bottom = float(keyword_word['bottom'])
    keyword_right = float(keyword_word['x1'])

    # Build list of occupied rectangles (text bounding boxes)
    occupied_rects = []
    for word in all_words:
        occupied_rects.append({
            'x0': float(word['x0']) - PADDING,
            'y0': float(word['top']) - PADDING,
            'x1': float(word['x1']) + PADDING,
            'y1': float(word['bottom']) + PADDING
        })

    # Also check for lines/rectangles (form fields, boxes)
    try:
        lines = page.lines or []
        for line in lines:
            occupied_rects.append({
                'x0': float(line['x0']) - PADDING,
                'y0': float(line['top']) - PADDING,
                'x1': float(line['x1']) + PADDING,
                'y1': float(line['bottom']) + PADDING
            })

        rects = page.rects or []
        for rect in rects:
            occupied_rects.append({
                'x0': float(rect['x0']) - PADDING,
                'y0': float(rect['top']) - PADDING,
                'x1': float(rect['x1']) + PADDING,
                'y1': float(rect['bottom']) + PADDING
            })
    except:
        pass  # Some PDFs may not have lines/rects

    total_height = sig_height + TEXT_HEIGHT  # Account for text below signature

    def is_area_clear(x, y, width, height):
        """Check if a rectangular area is free from obstacles."""
        # Check page bounds
        if x < PADDING or y < PADDING:
            return False
        if x + width > page_width - PADDING or y + height > page_height - PADDING:
            return False

        # Check against all occupied rectangles
        for rect in occupied_rects:
            # Check for overlap
            if not (x + width < rect['x0'] or x > rect['x1'] or
                    y + height < rect['y0'] or y > rect['y1']):
                return False
        return True

    def distance_from_keyword(x, y):
        """Calculate distance from candidate position to keyword."""
        # Distance from center of signature area to keyword position
        center_x = x + sig_width / 2
        center_y = y + sig_height / 2
        return ((center_x - keyword_x) ** 2 + (center_y - keyword_y) ** 2) ** 0.5

    # Candidate positions to check (in priority order)
    # Priority: positions that keep signature in bottom-left or bottom-right quadrants
    candidates = []

    # Check if keyword is in bottom half of page
    is_keyword_in_bottom = keyword_y > page_height * 0.5

    # 1. Above the keyword (most common for signature lines)
    candidates.append((keyword_x, keyword_y - total_height - 5))

    # 2. Right of the keyword (for "Signature: _______" patterns)
    candidates.append((keyword_right + 10, keyword_y - sig_height / 2))

    # 3. Below the keyword (if there's space)
    candidates.append((keyword_x, keyword_bottom + 5))

    # 4. Left of keyword (less common)
    candidates.append((keyword_x - sig_width - 10, keyword_y - sig_height / 2))

    # 5. Grid search around the keyword - prioritize bottom and left positions
    search_range = 150  # pixels
    step = 15

    # First search below and to the left of keyword (bottom-left priority)
    for dy in range(0, search_range + 1, step):
        for dx in range(-search_range, 0, step):
            x = keyword_x + dx
            y = keyword_y + dy
            if x >= PADDING and y + total_height <= page_height - PADDING:
                candidates.append((x, y))

    # Then search below and to the right (bottom-right priority)
    for dy in range(0, search_range + 1, step):
        for dx in range(0, search_range + 1, step):
            x = keyword_x + dx
            y = keyword_y + dy
            if x + sig_width <= page_width - PADDING and y + total_height <= page_height - PADDING:
                candidates.append((x, y))

    # Finally search above keyword
    for dy in range(-search_range, 0, step):
        for dx in range(-search_range, search_range + 1, step):
            x = keyword_x + dx
            y = keyword_y + dy
            candidates.append((x, y))

    def position_score(x, y):
        """
        Score a position - lower is better.
        Heavily favors bottom-left, then bottom-right.
        """
        score = distance_from_keyword(x, y)

        # Strong bonus for bottom half of page (lower score = better)
        if y > page_height * 0.6:
            score -= 200  # Big bonus for bottom 40%
        elif y > page_height * 0.5:
            score -= 100  # Moderate bonus for bottom half

        # Bonus for left side (bottom-left is priority 1)
        if x < page_width * 0.5:
            score -= 50  # Prefer left side

        # Penalty for center area
        if is_in_center_area(x, y, page_width, page_height, sig_width, sig_height):
            score += 500  # Heavy penalty for center

        return score

    # Find the best position using scoring
    best_pos = None
    best_score = float('inf')

    for x, y in candidates:
        if is_area_clear(x, y, sig_width, total_height):
            # Skip center area in first pass
            if is_in_center_area(x, y, page_width, page_height, sig_width, sig_height):
                continue
            score = position_score(x, y)
            if score < best_score:
                best_score = score
                best_pos = (x, y)

    # If no non-center position found, accept center as last resort
    if best_pos is None:
        for x, y in candidates:
            if is_area_clear(x, y, sig_width, total_height):
                score = position_score(x, y)
                if score < best_score:
                    best_score = score
                    best_pos = (x, y)

    if best_pos:
        return {'x': best_pos[0], 'y': best_pos[1]}

    # Fallback: place above keyword even if overlapping slightly
    # (user can adjust manually)
    fallback_y = keyword_y - total_height - 5
    if fallback_y < PADDING:
        fallback_y = keyword_bottom + 5

    return {
        'x': max(PADDING, min(keyword_x, page_width - sig_width - PADDING)),
        'y': max(PADDING, min(fallback_y, page_height - total_height - PADDING))
    }


def detect_all_signature_positions(pdf_path: str) -> dict:
    """
    Detect signature positions across ALL pages of a PDF using pdfplumber.
    Returns at most ONE signature position per page (0 or 1 per page).
    Only searches for the word "signature" (case-insensitive).
    Places signature in blank space nearest to the keyword.
    Searches from last page to first (signatures usually at end).
    Falls back to blank space on last page if no keyword found.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        dict with:
            - found: bool - whether any signature locations were detected
            - positions: list of position dicts, each with page, x, y, width, height, confidence, method, keyword
            - total_pages: int - total number of pages in PDF
    """
    result = {
        'found': False,
        'positions': [],
        'total_pages': 0
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            result['total_pages'] = num_pages

            if num_pages == 0:
                return result

            positions = []

            # Search from last page to first
            for page_idx in range(num_pages - 1, -1, -1):
                page = pdf.pages[page_idx]
                page_height = float(page.height)
                page_width = float(page.width)

                # Extract text content
                text_content = page.extract_text() or ""

                # Only search for "signature"
                match = SIGNATURE_PATTERN.search(text_content)
                if not match:
                    continue  # No signature keyword on this page

                # Extract words with positions
                words = page.extract_words()
                if not words:
                    continue

                # Find the word "signature" position
                for word in words:
                    word_text = word['text'].lower()
                    if 'signature' in word_text:
                        # Find blank space near this keyword
                        blank_pos = find_blank_space_near_keyword(
                            page, word, words, SIG_WIDTH, SIG_HEIGHT
                        )

                        if blank_pos:
                            x = blank_pos['x']
                            y = blank_pos['y']
                        else:
                            # Fallback to above keyword
                            x = float(word['x0'])
                            y = float(word['top']) - SIG_HEIGHT - TEXT_HEIGHT - 5

                        # Ensure within page bounds
                        total_height = SIG_HEIGHT + TEXT_HEIGHT
                        if x + SIG_WIDTH > page_width:
                            x = page_width - SIG_WIDTH - 20
                        if x < 10:
                            x = 10
                        if y < 10:
                            y = 10
                        if y + total_height > page_height:
                            y = page_height - total_height - 20

                        page_position = {
                            'page': page_idx,
                            'x': x,
                            'y': y,
                            'width': SIG_WIDTH,
                            'height': SIG_HEIGHT,
                            'confidence': 'high',
                            'method': 'pdfplumber_blank_space',
                            'keyword': 'signature'
                        }
                        positions.append(page_position)
                        break  # Only one position per page

            # If no keyword found on any page, fallback to blank space on last page
            if not positions:
                last_page = pdf.pages[num_pages - 1]
                blank_pos = find_blank_space_on_page(last_page, SIG_WIDTH, SIG_HEIGHT, avoid_center=True)

                if blank_pos:
                    page_position = {
                        'page': num_pages - 1,
                        'x': blank_pos['x'],
                        'y': blank_pos['y'],
                        'width': SIG_WIDTH,
                        'height': SIG_HEIGHT,
                        'confidence': 'low',
                        'method': 'blank_space_fallback',
                        'keyword': None
                    }
                    positions.append(page_position)

            if positions:
                result['found'] = True
                # Sort by page number (ascending) for consistent ordering
                result['positions'] = sorted(positions, key=lambda p: p['page'])

    except Exception as e:
        print(f"Error detecting signature positions: {e}")

    return result


def detect_signature_position(pdf_path: str) -> dict:
    """
    Detect the best position for signature placement in a PDF.
    Uses pdfplumber only. Searches for the word "signature".
    Places signature in blank space nearest to the keyword.
    Searches from last page to first (signatures usually at end).
    Falls back to blank space on last page if no keyword found.

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
        'width': SIG_WIDTH,
        'height': SIG_HEIGHT,
        'confidence': 'low',
        'method': 'none',
        'keyword': None
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)

            if num_pages == 0:
                return result

            # Search from last page backwards (signature usually at end)
            for page_idx in range(num_pages - 1, -1, -1):
                page = pdf.pages[page_idx]
                page_height = float(page.height)
                page_width = float(page.width)

                # Extract text content
                text_content = page.extract_text() or ""

                # Only search for "signature"
                match = SIGNATURE_PATTERN.search(text_content)
                if not match:
                    continue

                # Extract words with positions
                words = page.extract_words()
                if not words:
                    continue

                # Find the word "signature" position
                for word in words:
                    word_text = word['text'].lower()
                    if 'signature' in word_text:
                        # Find blank space near this keyword
                        blank_pos = find_blank_space_near_keyword(
                            page, word, words, SIG_WIDTH, SIG_HEIGHT
                        )

                        if blank_pos:
                            x = blank_pos['x']
                            y = blank_pos['y']
                        else:
                            # Fallback to above keyword
                            x = float(word['x0'])
                            y = float(word['top']) - SIG_HEIGHT - TEXT_HEIGHT - 5

                        # Ensure within page bounds
                        total_height = SIG_HEIGHT + TEXT_HEIGHT
                        if x + SIG_WIDTH > page_width:
                            x = page_width - SIG_WIDTH - 20
                        if x < 10:
                            x = 10
                        if y < 10:
                            y = 10
                        if y + total_height > page_height:
                            y = page_height - total_height - 20

                        result['found'] = True
                        result['page'] = page_idx
                        result['x'] = x
                        result['y'] = y
                        result['width'] = SIG_WIDTH
                        result['height'] = SIG_HEIGHT
                        result['confidence'] = 'high'
                        result['method'] = 'pdfplumber_blank_space'
                        result['keyword'] = 'signature'

                        return result

            # If no keyword found, fallback to blank space on last page
            last_page = pdf.pages[num_pages - 1]
            blank_pos = find_blank_space_on_page(last_page, SIG_WIDTH, SIG_HEIGHT, avoid_center=True)

            if blank_pos:
                result['found'] = True
                result['page'] = num_pages - 1
                result['x'] = blank_pos['x']
                result['y'] = blank_pos['y']
                result['width'] = SIG_WIDTH
                result['height'] = SIG_HEIGHT
                result['confidence'] = 'low'
                result['method'] = 'blank_space_fallback'
                result['keyword'] = None

    except Exception as e:
        print(f"Error detecting signature position: {e}")

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


def detect_f2f_signature_position(pdf_path: str) -> dict:
    """
    Detect signature position for F2F (Face to Face) documents.
    F2F documents ONLY get a signature on the LAST page in blank space.
    No keyword searching - always uses blank space detection on last page.
    Falls back to bottom-left corner if no blank space found.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        dict with:
            - found: bool - whether a signature location was detected
            - positions: list of position dicts (only last page)
            - total_pages: int - total number of pages in PDF
    """
    result = {
        'found': False,
        'positions': [],
        'total_pages': 0
    }

    try:
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            result['total_pages'] = num_pages

            if num_pages == 0:
                return result

            # F2F: Only place signature on LAST page
            last_page = pdf.pages[num_pages - 1]
            page_width = float(last_page.width)
            page_height = float(last_page.height)

            blank_pos = find_blank_space_on_page(last_page, SIG_WIDTH, SIG_HEIGHT, avoid_center=True)

            if blank_pos:
                x = blank_pos['x']
                y = blank_pos['y']
                method = 'f2f_last_page_blank_space'
                confidence = 'high'
            else:
                # Fallback: random position within bottom-left quadrant
                # Bottom-left quadrant: x from PADDING to 50% of page, y in bottom 40% of page
                # For F2F box, we need more space (box is ~220px wide, ~120px tall)
                f2f_box_width = 220
                f2f_box_height = 120

                # X range: from padding to half the page width (minus box width)
                x_min = PADDING + 10
                x_max = max(x_min + 20, (page_width / 2) - f2f_box_width - PADDING)

                # Y range: bottom 40% of the page (leaving margin at very bottom)
                # Remember: y is from top, so higher y = further down the page
                y_min = page_height * 0.6  # Start at 60% down the page
                y_max = page_height - f2f_box_height - PADDING - 30  # Leave margin at bottom

                # Ensure valid ranges
                if x_max <= x_min:
                    x_max = x_min + 50
                if y_max <= y_min:
                    y_max = y_min + 50

                x = random.uniform(x_min, x_max)
                y = random.uniform(y_min, y_max)
                method = 'f2f_fallback_bottom_left_random'
                confidence = 'medium'

            page_position = {
                'page': num_pages - 1,
                'x': float(x),
                'y': float(y),
                'width': SIG_WIDTH,
                'height': SIG_HEIGHT,
                'confidence': confidence,
                'method': method,
                'keyword': None
            }
            result['found'] = True
            result['positions'] = [page_position]

    except Exception as e:
        print(f"Error detecting F2F signature position: {e}")
        import traceback
        traceback.print_exc()

    return result
