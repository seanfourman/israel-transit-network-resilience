"""Correct Hebrew (RTL) rendering for Matplotlib figures.

Matplotlib lays glyphs out left-to-right and does not apply the Unicode
bidirectional algorithm, so Hebrew labels come out visually reversed. This
module fixes that for the whole project in one place:

* ``install_hebrew()`` sets a Hebrew-capable font (Arial on Windows) and
  monkeypatches ``matplotlib.text.Text.set_text`` so that every label, tick,
  legend entry and annotation is passed through ``python-bidi`` automatically.
  Data-derived labels (e.g. station names read from CSV) are fixed too, without
  having to wrap each call site by hand.
* English words, numbers and acronyms keep their natural left-to-right order
  because that is exactly what the bidi algorithm does.

Call ``install_hebrew()`` once, right after ``matplotlib.use("Agg")`` and
before any figure is drawn.
"""
from __future__ import annotations

import re

from bidi.algorithm import get_display

_HEBREW_RE = re.compile(r"[֐-׿]")


def fix(text: object) -> object:
    """Return display-ordered text for Matplotlib. Non-Hebrew is untouched."""
    if not isinstance(text, str) or not _HEBREW_RE.search(text):
        return text
    return get_display(text)


def install_hebrew(font: str = "Arial") -> None:
    """Set a Hebrew font and auto-apply the bidi algorithm to all Matplotlib text."""
    import matplotlib

    matplotlib.rcParams["font.family"] = [font, "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False

    import matplotlib.text as mtext

    if getattr(mtext.Text, "_bidi_patched", False):
        return

    _original_set_text = mtext.Text.set_text

    def set_text(self, s):  # type: ignore[no-untyped-def]
        # If we are handed back a string we already produced (e.g. via a
        # get_text round-trip), do not reverse it a second time.
        if isinstance(s, str) and getattr(self, "_bidi_display", None) == s:
            return _original_set_text(self, s)
        fixed = fix(s)
        if isinstance(fixed, str):
            self._bidi_display = fixed
        return _original_set_text(self, fixed)

    mtext.Text.set_text = set_text
    mtext.Text._bidi_patched = True
