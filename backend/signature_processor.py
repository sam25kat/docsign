"""
Signature processing utilities.
- Background removal
- Image optimization
- Transparency handling
"""

import io
from PIL import Image

# Try to import rembg, fallback to simple threshold-based removal
try:
    from rembg import remove as rembg_remove
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False
    print("Warning: rembg not installed. Using simple background removal.")


def remove_background_simple(image_data: bytes) -> bytes:
    """
    Simple background removal using threshold.
    Works well for signatures on white/light backgrounds.
    """
    img = Image.open(io.BytesIO(image_data))

    # Convert to RGBA
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Get pixel data
    pixels = img.load()
    width, height = img.size

    # Threshold for "white" (adjust as needed)
    threshold = 240

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            # If pixel is close to white, make it transparent
            if r > threshold and g > threshold and b > threshold:
                pixels[x, y] = (r, g, b, 0)
            # If pixel is light gray, make it semi-transparent
            elif r > 200 and g > 200 and b > 200:
                pixels[x, y] = (r, g, b, int(a * 0.5))

    # Save to bytes
    output = io.BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    return output.getvalue()


def remove_background(image_data: bytes) -> bytes:
    """
    Remove background from signature image.
    Uses rembg if available, otherwise falls back to simple threshold method.
    """
    if HAS_REMBG:
        return rembg_remove(image_data)
    else:
        return remove_background_simple(image_data)


def process_signature_image(image_data: bytes, max_width: int = 400, max_height: int = 150) -> bytes:
    """
    Process uploaded signature image:
    1. Remove background (make transparent)
    2. Resize to appropriate dimensions
    3. Optimize for PDF embedding

    Returns: PNG bytes with transparent background
    """
    # Remove background
    transparent_data = remove_background(image_data)

    # Open the transparent image
    img = Image.open(io.BytesIO(transparent_data))

    # Ensure RGBA mode for transparency
    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    # Trim transparent edges
    img = trim_transparent(img)

    # Resize while maintaining aspect ratio
    img = resize_maintain_aspect(img, max_width, max_height)

    # Save to bytes
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    output.seek(0)

    return output.getvalue()


def trim_transparent(img: Image.Image) -> Image.Image:
    """Remove transparent edges from image."""
    # Get the alpha channel
    if img.mode != 'RGBA':
        return img

    # Get bounding box of non-transparent pixels
    bbox = img.getbbox()

    if bbox:
        return img.crop(bbox)
    return img


def resize_maintain_aspect(img: Image.Image, max_width: int, max_height: int) -> Image.Image:
    """Resize image maintaining aspect ratio to fit within max dimensions."""
    width, height = img.size

    # Calculate scaling factor
    width_ratio = max_width / width
    height_ratio = max_height / height
    ratio = min(width_ratio, height_ratio, 1.0)  # Don't upscale

    if ratio < 1.0:
        new_width = int(width * ratio)
        new_height = int(height * ratio)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    return img


def validate_image(image_data: bytes) -> tuple[bool, str]:
    """
    Validate that the uploaded file is a valid image.
    Returns: (is_valid, error_message)
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        img.verify()

        # Re-open after verify (verify closes the file)
        img = Image.open(io.BytesIO(image_data))

        # Check dimensions
        width, height = img.size
        if width < 50 or height < 20:
            return False, "Image too small. Minimum size is 50x20 pixels."
        if width > 4000 or height > 4000:
            return False, "Image too large. Maximum size is 4000x4000 pixels."

        # Check format
        if img.format not in ['PNG', 'JPEG', 'WEBP']:
            return False, f"Unsupported format: {img.format}. Use PNG, JPEG, or WEBP."

        return True, ""

    except Exception as e:
        return False, f"Invalid image file: {str(e)}"


def get_signature_preview(encrypted_path: str, encryption) -> bytes:
    """
    Get a preview of the stored signature (decrypted).
    Returns PNG bytes.
    """
    return encryption.decrypt_file(encrypted_path)
