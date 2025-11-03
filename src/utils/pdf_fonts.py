"""
PDF Font Registration Utility

Handles registration of Unicode-compatible Google Fonts from static/ folder.
This enables special characters, accents, and symbols in ReportLab PDFs.

Available fonts:
  - HankenGrotesk: Modern sans-serif, excellent Unicode support (recommended for general use)
  - SpaceMono: Monospace font, great for code/tables

Example usage:
    from src.utils.pdf_fonts import register_pdf_fonts, get_default_font

    register_pdf_fonts()  # Call once at app startup

    # In your styles:
    font = get_default_font()  # Returns "HankenGrotesk" if available, else "Helvetica"
    font_bold = get_default_font(bold=True)  # Returns "HankenGrotesk-SemiBold"
"""

import os
import logging
from pathlib import Path
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# Global registry of registered fonts
_REGISTERED_FONTS = set()


def register_pdf_fonts():
    """
    Register Unicode-compatible Google Fonts from static folder.

    Call this once at application startup to enable special characters in PDFs.
    Safe to call multiple times - won't re-register already registered fonts.

    Returns:
        dict: Summary of registered fonts
    """
    global _REGISTERED_FONTS

    try:
        # Get path to static folder
        static_dir = Path(__file__).parent.parent.parent / "static"

        # Register HankenGrotesk family with proper variants (not variable fonts!)
        fonts_to_register = [
            # HankenGrotesk family - static variants (not variable fonts)
            ("HankenGrotesk", "HankenGrotesk-Regular.ttf"),
            ("HankenGrotesk-Bold", "HankenGrotesk-Bold.ttf"),
            ("HankenGrotesk-Italic", "HankenGrotesk-Italic.ttf"),
            ("HankenGrotesk-BoldItalic", "HankenGrotesk-BoldItalic.ttf"),
            # SpaceMono as backup
            ("SpaceMono-Regular", "SpaceMono-Regular.ttf"),
            ("SpaceMono-Bold", "SpaceMono-Bold.ttf"),
        ]

        fonts_registered = []
        fonts_failed = []

        for font_name, font_file in fonts_to_register:
            # Skip if already registered
            if font_name in _REGISTERED_FONTS:
                fonts_registered.append(font_name)
                continue

            font_path = static_dir / font_file

            if not font_path.exists():
                fonts_failed.append((font_name, f"File not found: {font_path}"))
                continue

            try:
                pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
                _REGISTERED_FONTS.add(font_name)
                fonts_registered.append(font_name)
                logger.debug(f"✓ Registered font: {font_name}")
            except Exception as e:
                fonts_failed.append((font_name, str(e)))
                logger.warning(f"✗ Failed to register {font_name}: {e}")

        result = {
            "success": len(fonts_registered) > 0,
            "registered": fonts_registered,
            "failed": fonts_failed,
            "total": len(fonts_to_register),
        }

        if result["success"]:
            logger.info(
                f"✓ Registered {len(fonts_registered)}/{len(fonts_to_register)} PDF fonts with Unicode support"
            )
        else:
            logger.warning(
                "⚠️ No PDF fonts registered - special characters may not render"
            )

        return result

    except Exception as e:
        logger.error(f"Failed to register PDF fonts: {e}")
        return {
            "success": False,
            "registered": [],
            "failed": [("all", str(e))],
            "total": 0,
        }


def get_default_font(bold: bool = False, italic: bool = False) -> str:
    """
    Get the default font for PDF generation.

    Returns the best available Unicode-supporting font, with fallback to standard fonts.

    Args:
        bold: If True, return bold variant
        italic: If True, return italic variant

    Returns:
        str: Font name suitable for ReportLab

    Example:
        font = get_default_font()  # "HankenGrotesk"
        font_bold = get_default_font(bold=True)  # "HankenGrotesk-Bold"
        font_italic = get_default_font(italic=True)  # "HankenGrotesk-Italic"
        font_bold_italic = get_default_font(bold=True, italic=True)  # "HankenGrotesk-BoldItalic"
    """
    if bold and italic:
        preferred = ["HankenGrotesk-BoldItalic", "Helvetica-BoldOblique"]
    elif bold:
        preferred = ["HankenGrotesk-Bold", "Helvetica-Bold"]
    elif italic:
        preferred = ["HankenGrotesk-Italic", "Helvetica-Oblique"]
    else:
        preferred = ["HankenGrotesk", "Helvetica"]

    for font in preferred:
        if _font_available(font):
            return font

    # Fallback
    if bold and italic:
        return "Helvetica-BoldOblique"
    elif bold:
        return "Helvetica-Bold"
    elif italic:
        return "Helvetica-Oblique"
    else:
        return "Helvetica"


def get_monospace_font(bold: bool = False) -> str:
    """
    Get a monospace font for tables and code.

    Args:
        bold: If True, return bold variant

    Returns:
        str: Monospace font name suitable for ReportLab
    """
    if bold:
        preferred = ["SpaceMono-Bold", "Courier-Bold"]
    else:
        preferred = ["SpaceMono-Regular", "Courier"]

    for font in preferred:
        if _font_available(font):
            return font

    return "Courier-Bold" if bold else "Courier"


def get_table_header_font() -> str:
    """
    Get font for table headers.

    Returns:
        str: Bold font name suitable for table headers
    """
    return get_default_font(bold=True)


def get_table_cell_font() -> str:
    """
    Get font for table cells.

    Returns:
        str: Regular font name suitable for table cells
    """
    return get_default_font(bold=False)


def _font_available(font_name: str) -> bool:
    """Check if a font is available in ReportLab's font registry."""
    try:
        from reportlab.pdfbase.pdfmetrics import _fonts

        return font_name in _fonts
    except Exception:
        return False


# Auto-register fonts on module import for convenience
try:
    _registration_result = register_pdf_fonts()
except Exception as e:
    logger.warning(f"Could not auto-register fonts on import: {e}")
