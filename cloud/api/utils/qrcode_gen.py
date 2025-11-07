"""QR code generation for share links."""

import io
import base64
from typing import Optional

try:
    import qrcode
    from qrcode.image.pure import PyPNGImage
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False
    print("WARNING: qrcode package not installed. QR code generation will be limited.")
    print("   Run: pip install qrcode[pil]")


def generate_qr_code(
    data: str,
    size: int = 10,
    border: int = 2
) -> Optional[str]:
    """
    Generate QR code as base64-encoded PNG image.

    Args:
        data: Data to encode (typically a URL)
        size: Size of QR code (1-40, default: 10)
        border: Border size in boxes (default: 2)

    Returns:
        Base64-encoded PNG image data or None if qrcode not available
    """
    if not QRCODE_AVAILABLE:
        return None

    try:
        # Create QR code
        qr = qrcode.QRCode(
            version=1,  # Auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)

        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        # Encode as base64
        img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')

        return f"data:image/png;base64,{img_base64}"

    except Exception as e:
        print(f"ERROR: Failed to generate QR code: {e}")
        return None


def generate_qr_code_svg(data: str, size: int = 10) -> Optional[str]:
    """
    Generate QR code as SVG.

    Args:
        data: Data to encode (typically a URL)
        size: Size of QR code

    Returns:
        SVG string or None if qrcode not available
    """
    if not QRCODE_AVAILABLE:
        return None

    try:
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=size,
            border=2,
        )
        qr.add_data(data)
        qr.make(fit=True)

        # Generate SVG factory
        factory = qrcode.image.svg.SvgPathImage
        img = qr.make_image(image_factory=factory)

        # Convert to string
        svg_bytes = io.BytesIO()
        img.save(svg_bytes)
        return svg_bytes.getvalue().decode('utf-8')

    except Exception as e:
        print(f"ERROR: Failed to generate QR code SVG: {e}")
        return None
