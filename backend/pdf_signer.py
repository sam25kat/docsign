"""
PDF signing utilities.
Overlay signature onto PDF documents with "Digitally signed by" text and timestamp.
"""

import io
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.colors import black
from PIL import Image


def get_pdf_info(pdf_path: str) -> dict:
    """Get PDF metadata and page information."""
    reader = PdfReader(pdf_path)
    pages = []

    for i, page in enumerate(reader.pages):
        mediabox = page.mediabox
        pages.append({
            'page_number': i + 1,
            'width': float(mediabox.width),
            'height': float(mediabox.height)
        })

    # Safely extract metadata
    metadata = {}
    if reader.metadata:
        try:
            metadata = dict(reader.metadata) if reader.metadata else {}
        except:
            metadata = {}

    return {
        'num_pages': len(reader.pages),
        'pages': pages,
        'metadata': metadata
    }


def draw_signature_with_text(
    overlay_canvas,
    sig_reader,
    x: float,
    y: float,
    sig_width: float,
    sig_height: float,
    signer_name: str = None,
    timestamp: datetime = None
):
    """
    Draw signature image with "Digitally signed by" text and timestamp.

    Layout:
    +---------------------------+
    | [Signature Image]         |
    | Digitally signed by       |
    | {Name}                    |
    | Date: YYYY-MM-DD HH:MM:SS |
    +---------------------------+
    """
    # Draw signature image
    overlay_canvas.drawImage(
        sig_reader,
        x, y,
        width=sig_width,
        height=sig_height,
        mask='auto'
    )

    # Add text below signature if signer_name provided
    if signer_name:
        overlay_canvas.setFillColor(black)

        # Font settings
        font_size = 7
        line_height = 9
        overlay_canvas.setFont("Helvetica", font_size)

        # Calculate text position (below signature)
        text_x = x
        text_y = y - line_height  # Start below signature

        # "Digitally signed by"
        overlay_canvas.drawString(text_x, text_y, "Digitally signed by")
        text_y -= line_height

        # Signer name
        overlay_canvas.setFont("Helvetica-Bold", font_size)
        overlay_canvas.drawString(text_x, text_y, signer_name)
        text_y -= line_height

        # Timestamp
        overlay_canvas.setFont("Helvetica", font_size)
        if timestamp:
            date_str = timestamp.strftime("Date: %Y-%m-%d %H:%M:%S")
        else:
            date_str = datetime.now().strftime("Date: %Y-%m-%d %H:%M:%S")
        overlay_canvas.drawString(text_x, text_y, date_str)


def draw_f2f_signature_with_textbox(
    overlay_canvas,
    sig_reader,
    x: float,
    y: float,
    sig_width: float,
    sig_height: float,
    signer_name: str = None,
    timestamp: datetime = None,
    document_id: str = None,
    ip_address: str = None
):
    """
    Draw F2F signature with text box similar to electronic signature format.
    Used for Face-to-Face documents.

    Layout:
    +----------------------------------+--------+
    | Electronic Signature             |        |
    |                                  |        |
    | [Signature Image]                |  [QR]  |
    |                                  |        |
    | Document ID:                     |        |
    | {uuid}                           |        |
    | IP Address: {ip}                 |        |
    | Time: {datetime}                 |        |
    | Signer: {Name}                   |        |
    +----------------------------------+--------+
    """
    from reportlab.lib.colors import HexColor
    import uuid as uuid_module

    # Generate document ID if not provided
    if not document_id:
        document_id = str(uuid_module.uuid4())

    # Default IP address
    if not ip_address:
        ip_address = "::1"

    # Box styling - wider to accommodate QR code
    qr_size = 50
    qr_margin = 10
    text_area_width = max(sig_width + 40, 220)
    box_width = text_area_width + qr_size + qr_margin
    box_padding = 8

    # Font settings
    title_font_size = 10
    label_font_size = 8
    value_font_size = 7
    line_height = 11

    # Calculate heights
    title_height = 18
    sig_area_height = sig_height + 8
    info_lines = 5  # Document ID label, ID value, IP Address, Time, Signer
    info_height = info_lines * line_height + 8

    total_box_height = title_height + sig_area_height + info_height + (box_padding * 2)

    # Background fill (light cream/yellow like the example)
    overlay_canvas.setFillColor(HexColor('#FFF8DC'))  # Cornsilk color
    overlay_canvas.setStrokeColor(HexColor('#D4A574'))  # Tan border
    overlay_canvas.setLineWidth(1.5)
    box_y = y - total_box_height + sig_height
    overlay_canvas.rect(x, box_y, box_width, total_box_height, fill=1, stroke=1)

    # Title: "Electronic Signature"
    overlay_canvas.setFillColor(HexColor('#333333'))
    overlay_canvas.setFont("Helvetica-Bold", title_font_size)
    title_y = y + sig_height - box_padding - title_font_size
    overlay_canvas.drawString(x + box_padding, title_y, "Electronic Signature")

    # Draw signature image
    sig_y = title_y - sig_height - 5
    overlay_canvas.drawImage(
        sig_reader,
        x + box_padding,
        sig_y,
        width=sig_width,
        height=sig_height,
        mask='auto'
    )

    # Draw QR code placeholder (simple square pattern to simulate QR)
    qr_x = x + text_area_width
    qr_y = box_y + (total_box_height - qr_size) / 2  # Center vertically

    # Draw QR code border
    overlay_canvas.setStrokeColor(HexColor('#333333'))
    overlay_canvas.setLineWidth(0.5)
    overlay_canvas.rect(qr_x, qr_y, qr_size, qr_size, fill=0, stroke=1)

    # Draw simple QR-like pattern
    overlay_canvas.setFillColor(HexColor('#333333'))
    cell_size = qr_size / 7
    # Corner squares (QR code positioning patterns)
    for corner in [(0, 0), (0, 5), (5, 0)]:
        cx, cy = corner
        overlay_canvas.rect(qr_x + cx * cell_size, qr_y + cy * cell_size,
                           2 * cell_size, 2 * cell_size, fill=1, stroke=0)
    # Some random-looking data cells
    import hashlib
    hash_bytes = hashlib.md5(document_id.encode()).digest()
    for i, byte in enumerate(hash_bytes[:12]):
        if byte % 3 == 0:
            row = (i // 4) + 2
            col = (i % 4) + 2
            if row < 6 and col < 6:
                overlay_canvas.rect(qr_x + col * cell_size, qr_y + row * cell_size,
                                   cell_size * 0.8, cell_size * 0.8, fill=1, stroke=0)

    # Info section below signature
    info_y = sig_y - 12

    # Document ID label
    overlay_canvas.setFont("Helvetica", label_font_size)
    overlay_canvas.setFillColor(HexColor('#666666'))
    overlay_canvas.drawString(x + box_padding, info_y, "Document ID:")
    info_y -= line_height

    # Document ID value (in blue like example)
    overlay_canvas.setFont("Helvetica", value_font_size)
    overlay_canvas.setFillColor(HexColor('#0066CC'))
    # Truncate ID if too long
    display_id = document_id[:36] if len(document_id) > 36 else document_id
    overlay_canvas.drawString(x + box_padding, info_y, display_id)
    info_y -= line_height

    # IP Address
    overlay_canvas.setFillColor(HexColor('#666666'))
    overlay_canvas.setFont("Helvetica", label_font_size)
    overlay_canvas.drawString(x + box_padding, info_y, f"IP Address: {ip_address}")
    info_y -= line_height

    # Time
    overlay_canvas.setFillColor(HexColor('#333333'))
    overlay_canvas.setFont("Helvetica", label_font_size)
    if timestamp:
        time_str = timestamp.strftime("Time: %A, %d %B %Y %H:%M:%S")
    else:
        time_str = datetime.now().strftime("Time: %A, %d %B %Y %H:%M:%S")
    overlay_canvas.drawString(x + box_padding, info_y, time_str)
    info_y -= line_height

    # Signer
    overlay_canvas.setFont("Helvetica", label_font_size)
    overlay_canvas.setFillColor(HexColor('#333333'))
    overlay_canvas.drawString(x + box_padding, info_y, "Signer: ")
    overlay_canvas.setFont("Helvetica-Bold", label_font_size)
    overlay_canvas.setFillColor(HexColor('#0066CC'))
    signer_x = x + box_padding + overlay_canvas.stringWidth("Signer: ", "Helvetica", label_font_size)
    overlay_canvas.drawString(signer_x, info_y, signer_name or "Unknown")


def add_f2f_signature_to_pdf(
    pdf_path: str,
    signature_data: bytes,
    position: dict,
    output_path: str = None,
    signer_name: str = None,
    document_id: str = None,
    ip_address: str = None
) -> bytes:
    """
    Add F2F signature with text box to PDF (last page only).
    Used for Face-to-Face documents.

    Args:
        pdf_path: Path to original PDF
        signature_data: PNG bytes of signature
        position: {x, y, page, width, height}
        output_path: Optional path to save signed PDF
        signer_name: Name for text box
        document_id: Optional document ID for the signature box
        ip_address: IP address of the signer

    Returns:
        Signed PDF as bytes
    """
    reader = PdfReader(pdf_path)
    num_pages = len(reader.pages)

    # F2F: Always sign on last page only
    page_num = num_pages - 1
    target_page = reader.pages[page_num]
    page_width = float(target_page.mediabox.width)
    page_height = float(target_page.mediabox.height)

    # Prepare signature image
    sig_image = Image.open(io.BytesIO(signature_data))
    if sig_image.mode != 'RGBA':
        sig_image = sig_image.convert('RGBA')

    sig_width = position.get('width', sig_image.width)
    sig_height = position.get('height', sig_image.height)

    # Calculate text box height (4 lines + padding)
    text_box_height = (4 * 11) + 10  # ~54px for text box

    # Convert position
    x = float(position.get('x', 100))
    y_from_top = float(position.get('y', 100))
    y = page_height - y_from_top - sig_height

    # Ensure space for text box below signature
    y = max(text_box_height + 10, min(y, page_height - sig_height - 10))
    x = max(10, min(x, page_width - max(sig_width, 150) - 10))

    # Create overlay
    packet = io.BytesIO()
    overlay_canvas = canvas.Canvas(packet, pagesize=(page_width, page_height))

    sig_buffer = io.BytesIO()
    sig_image.save(sig_buffer, format='PNG')
    sig_buffer.seek(0)
    sig_reader = ImageReader(sig_buffer)

    # Draw F2F signature with text box
    draw_f2f_signature_with_textbox(
        overlay_canvas,
        sig_reader,
        x, y,
        sig_width, sig_height,
        signer_name=signer_name,
        timestamp=datetime.now(),
        document_id=document_id,
        ip_address=ip_address
    )

    overlay_canvas.save()

    # Merge
    packet.seek(0)
    overlay_reader = PdfReader(packet)
    writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        if i == page_num:
            page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

    if reader.metadata:
        writer.add_metadata(reader.metadata)

    output_buffer = io.BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    result_bytes = output_buffer.getvalue()

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(result_bytes)

    return result_bytes


def add_signature_to_pdf(
    pdf_path: str,
    signature_data: bytes,
    position: dict,
    output_path: str = None,
    signer_name: str = None
) -> bytes:
    """
    Add signature image to PDF at specified position with optional signer info.

    Args:
        pdf_path: Path to original PDF
        signature_data: PNG bytes of signature (with transparent background)
        position: {
            'x': float,  # X position from left
            'y': float,  # Y position from top (will be converted)
            'page': int,  # Page number (0-indexed)
            'width': float,  # Signature width (optional)
            'height': float  # Signature height (optional)
        }
        output_path: Optional path to save signed PDF
        signer_name: Name for "Digitally signed by" text

    Returns:
        Signed PDF as bytes
    """
    # Read original PDF
    reader = PdfReader(pdf_path)

    # Get target page dimensions
    page_num = position.get('page', 0)
    if page_num >= len(reader.pages):
        raise ValueError(f"Page {page_num} does not exist. PDF has {len(reader.pages)} pages.")

    target_page = reader.pages[page_num]
    page_width = float(target_page.mediabox.width)
    page_height = float(target_page.mediabox.height)

    # Prepare signature image
    sig_image = Image.open(io.BytesIO(signature_data))
    if sig_image.mode != 'RGBA':
        sig_image = sig_image.convert('RGBA')

    # Get signature dimensions
    sig_width = position.get('width', sig_image.width)
    sig_height = position.get('height', sig_image.height)

    # Scale signature if needed (maintain aspect ratio)
    if sig_width != sig_image.width or sig_height != sig_image.height:
        aspect = sig_image.width / sig_image.height
        if sig_width / sig_height > aspect:
            sig_width = sig_height * aspect
        else:
            sig_height = sig_width / aspect

    # Calculate text height if signer_name provided
    text_height = 30 if signer_name else 0  # 3 lines * ~10px each

    # Convert position from top-left origin to PDF bottom-left origin
    # Account for text below signature
    x = float(position.get('x', 100))
    y_from_top = float(position.get('y', 100))
    y = page_height - y_from_top - sig_height

    # Ensure coordinates are within valid bounds (including space for text)
    x = max(0, min(x, page_width - sig_width))
    y = max(text_height, min(y, page_height - sig_height))

    # Create overlay PDF with signature
    packet = io.BytesIO()
    overlay_canvas = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Draw signature with transparency support
    sig_buffer = io.BytesIO()
    sig_image.save(sig_buffer, format='PNG')
    sig_buffer.seek(0)
    sig_reader = ImageReader(sig_buffer)

    # Draw signature with optional text
    draw_signature_with_text(
        overlay_canvas,
        sig_reader,
        x, y,
        sig_width, sig_height,
        signer_name=signer_name,
        timestamp=datetime.now()
    )

    overlay_canvas.save()

    # Merge overlay with original PDF
    packet.seek(0)
    overlay_reader = PdfReader(packet)
    writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        if i == page_num:
            page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

    # Copy metadata
    if reader.metadata:
        writer.add_metadata(reader.metadata)

    # Output
    output_buffer = io.BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    result_bytes = output_buffer.getvalue()

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(result_bytes)

    return result_bytes


def add_multiple_signatures(
    pdf_path: str,
    signatures: list[dict],
    output_path: str = None,
    signer_name: str = None
) -> bytes:
    """
    Add multiple signatures to a PDF with optional signer info.

    Args:
        pdf_path: Path to original PDF
        signatures: List of {
            'signature_data': bytes,
            'position': {x, y, page, width, height}
        }
        output_path: Optional path to save signed PDF
        signer_name: Name for "Digitally signed by" text

    Returns:
        Signed PDF as bytes
    """
    # Start with original PDF
    current_pdf_bytes = open(pdf_path, 'rb').read()
    timestamp = datetime.now()

    for sig_info in signatures:
        # Create temp reader from current state
        temp_buffer = io.BytesIO(current_pdf_bytes)

        # For each signature, we need to work with the bytes
        reader = PdfReader(temp_buffer)
        page_num = sig_info['position'].get('page', 0)
        target_page = reader.pages[page_num]
        page_width = float(target_page.mediabox.width)
        page_height = float(target_page.mediabox.height)

        # Prepare signature
        sig_data = sig_info['signature_data']
        sig_image = Image.open(io.BytesIO(sig_data))
        if sig_image.mode != 'RGBA':
            sig_image = sig_image.convert('RGBA')

        pos = sig_info['position']
        sig_width = pos.get('width', sig_image.width)
        sig_height = pos.get('height', sig_image.height)

        # Calculate text height if signer_name provided
        text_height = 30 if signer_name else 0

        x = float(pos.get('x', 100))
        y_from_top = float(pos.get('y', 100))
        y = page_height - y_from_top - sig_height

        # Ensure space for text
        y = max(text_height, y)

        # Create overlay
        packet = io.BytesIO()
        overlay_canvas = canvas.Canvas(packet, pagesize=(page_width, page_height))

        sig_buffer = io.BytesIO()
        sig_image.save(sig_buffer, format='PNG')
        sig_buffer.seek(0)
        sig_reader = ImageReader(sig_buffer)

        # Draw signature with optional text
        draw_signature_with_text(
            overlay_canvas,
            sig_reader,
            x, y,
            sig_width, sig_height,
            signer_name=signer_name,
            timestamp=timestamp  # Use same timestamp for all signatures
        )

        overlay_canvas.save()

        # Merge
        packet.seek(0)
        overlay_reader = PdfReader(packet)
        writer = PdfWriter()

        temp_buffer.seek(0)
        reader = PdfReader(temp_buffer)

        for i, page in enumerate(reader.pages):
            if i == page_num:
                page.merge_page(overlay_reader.pages[0])
            writer.add_page(page)

        # Update current state
        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)
        current_pdf_bytes = output_buffer.getvalue()

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(current_pdf_bytes)

    return current_pdf_bytes
