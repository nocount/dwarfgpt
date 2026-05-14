"""
khuzdul_translator — a faithful port of The Dwarrow Scholar's Excel "Sentence Maker"
to Python. Provides word-by-word Neo-Khuzdul phrase lookup, deterministic phonological
post-processing (schwa epenthesis, long-vowel marking, gemination), and Cirth
rendering in both Angerthas Moria and Angerthas Erebor scripts.

Public API:
    >>> from khuzdul_translator import translate
    >>> result = translate("the dwarves")
    >>> result.khuzdul        # Neo-Khuzdul orthography
    >>> result.phonetic       # IPA-style phonetic form
    >>> result.moria_cirth    # Angerthas Moria glyphs (font-keyed)
    >>> result.erebor_cirth   # Angerthas Erebor glyphs (font-keyed)
    >>> result.tokens         # per-token detail with alternatives

Data files live in the sibling `data/` directory at the project root and are loaded
lazily on first import of the relevant module.
"""

from __future__ import annotations

from pathlib import Path

# Resolve the project-root `data/` directory at import time. We do not load any
# JSON here so importing the package stays cheap; the heavier loads happen the
# first time `translate()` or a submodule is touched.
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data"

__all__ = [
    "DATA_DIR",
    "translate",
    "translate_phrase",
    "TranslationResult",
    "TokenTranslation",
]

# Re-exports happen at the bottom to avoid circular imports during scaffolding.
from .pipeline import (  # noqa: E402
    TokenTranslation,
    TranslationResult,
    translate,
    translate_phrase,
)
