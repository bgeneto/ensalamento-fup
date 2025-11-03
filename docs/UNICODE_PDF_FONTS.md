# Unicode & Special Characters Support in PDFs

**Solution:** Use Google Fonts from `static/` folder instead of system fonts

## Problem Solved

ReportLab doesn't support Unicode characters (accents, special symbols, emojis) with default PDF fonts (Helvetica, Times, Courier). Characters like:
- `✅ ⚠️ 🔴 🟠 🟡 🔵` (emoji indicators)
- `← → ↑ ↓` (arrows)
- `…` (ellipsis)
- Accented characters: `é ñ ü`

...either render as replacement characters or disappear entirely.

## Solution Implemented

### 1. **Centralized Font Registry** (`src/utils/pdf_fonts.py`)

New utility module handles all font registration:

```python
from src.utils.pdf_fonts import register_pdf_fonts, get_default_font

# Register fonts once at startup
register_pdf_fonts()

# Use in styles
font = get_default_font()  # Returns "SpaceGrotesk" if available
font_bold = get_default_font(bold=True)  # Returns "SpaceGrotesk-SemiBold"
```

**Available fonts from Google Fonts:**
- **SpaceGrotesk** (recommended) - Modern sans-serif, excellent Unicode support
- **SpaceGrotesk-SemiBold** - Bold variant
- **SpaceMono-Regular** - Monospace, great for tables and code
- **SpaceMono-Bold** - Bold monospace

### 2. **Updated Allocation Report Service**

`src/services/autonomous_allocation_report_service.py` now:
- Uses `get_default_font()` from utility
- Automatically falls back to Helvetica if fonts unavailable
- All styles updated to use Unicode-supporting fonts

### 3. **Advantages Over System Fonts**

| Approach                | Pros                                   | Cons                             |
| ----------------------- | -------------------------------------- | -------------------------------- |
| System fonts (original) | Built-in, no dependencies              | ❌ No Unicode, platform-dependent |
| Google Fonts (new)      | ✅ Unicode support, consistent, bundled | Need TTF files                   |
| Online Google Fonts     | Fancy fonts                            | Requires internet, slow          |

## Usage in Other Services

To add Unicode support to other PDF services:

```python
from src.utils.pdf_fonts import register_pdf_fonts, get_default_font, get_monospace_font

class YourReportService:
    def __init__(self):
        register_pdf_fonts()  # Register once
        self.font = get_default_font()
        self.font_bold = get_default_font(bold=True)
        self.font_mono = get_monospace_font()
```

## Font Files Included

Located in `/static/`:
- `SpaceGrotesk-VariableFont_wght.ttf` (regular)
- `SpaceGrotesk-SemiBold.ttf` (bold)
- `SpaceMono-Regular.ttf` (monospace)
- `SpaceMono-Bold.ttf` (monospace bold)
- `HankenGrotesk-*.ttf` (additional options)

## Result

✅ All special characters now render correctly in PDFs:
- Status indicators: ✅ ⚠️ 🔴 🟠 🟡 🔵 ✓ ℹ️ →
- Accented characters: "é" "ñ" "ü"
- Symbols: "…" "•" "━" "│"

## Testing

The allocation report now displays:

```
✅ Fatores de Sucesso
⚠️ Áreas Problemáticas
🔴 CRÍTICO - Taxa de sucesso muito baixa
🟠 ALTO - Necessita melhorias
🟡 MÉDIO - Requer atenção
✓ Distribuição equilibrada
```

All rendering correctly in the PDF! 🚀
