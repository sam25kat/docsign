"""
PDF signing utilities.
Overlay signature onto PDF documents.
"""

import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
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


def add_signature_to_pdf(
    pdf_path: str,
    signature_data: bytes,
    position: dict,
    output_path: str = None
) -> bytes:
    """
    Add signature image to PDF at specified position.

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

    # Convert position from top-left origin to PDF bottom-left origin
    x = float(position.get('x', 100))
    y_from_top = float(position.get('y', 100))
    y = page_height - y_from_top - sig_height

    # Create overlay PDF with signature
    packet = io.BytesIO()
    overlay_canvas = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # Draw signature with transparency support
    sig_buffer = io.BytesIO()
    sig_image.save(sig_buffer, format='PNG')
    sig_buffer.seek(0)
    sig_reader = ImageReader(sig_buffer)

    overlay_canvas.drawImage(
        sig_reader,
        x, y,
        width=sig_width,
        height=sig_height,
        mask='auto'  # Preserve transparency
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
    output_path: str = None
) -> bytes:
    """
    Add multiple signatures to a PDF.

    Args:
        pdf_path: Path to original PDF
        signatures: List of {
            'signature_data': bytes,
            'position': {x, y, page, width, height}
        }
        output_path: Optional path to save signed PDF

    Returns:
        Signed PDF as bytes
    """
    # Start with original PDF
    current_pdf_bytes = open(pdf_path, 'rb').read()

    for sig_info in signatures:
        # Create temp reader from current state
        temp_buffer = io.BytesIO(current_pdf_bytes)
        temp_path = temp_buffer  # PdfReader can read from BytesIO

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

        x = float(pos.get('x', 100))
        y_from_top = float(pos.get('y', 100))
        y = page_height - y_from_top - sig_height

        # Create overlay
        packet = io.BytesIO()
        overlay_canvas = canvas.Canvas(packet, pagesize=(page_width, page_height))

        sig_buffer = io.BytesIO()
        sig_image.save(sig_buffer, format='PNG')
        sig_buffer.seek(0)
        sig_reader = ImageReader(sig_buffer)

        overlay_canvas.drawImage(sig_reader, x, y, width=sig_width, height=sig_height, mask='auto')
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
