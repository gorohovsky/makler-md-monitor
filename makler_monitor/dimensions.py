"""Extract physical dimensions from free-text descriptions, normalised to centimetres.

makler.md has no structured size fields, so width/height/depth live only in the seller's
prose. We recognise two shapes, in order of confidence:

1. Labelled values — "ширина 120 см", "Ш120", "width 130 cm".
2. Compact triples — "120x220x50" (assumed width x height x depth), used only as a
   fallback when no labelled value is found, to avoid guessing axis order needlessly.

Units (см/мм/м) are converted to centimetres. A unit-less decimal below 10 is read as
metres, because sellers write "высота 2.30" meaning 2.3 m; a plain integer stays in cm.

Single-letter labels (ш/в/г) are matched conservatively: attached to the number ("Ш120")
or spaced only when an explicit unit follows ("В 220 см"), so prose like "в 2020 году"
is never misread as a height.
"""

import re

from .models import Dimensions

_NUMBER = r'\d+(?:[.,]\d+)?'
# A unit token must not run into a longer word ("м" in "метро" is not metres here).
_UNIT = r'(?:см|мм|cm|mm|м|m)(?![а-яёa-z])'
_UNIT_FACTORS = {'см': 1.0, 'cm': 1.0, 'мм': 0.1, 'mm': 0.1, 'м': 100.0, 'm': 100.0}
_BARE_VALUE_IS_METRES_BELOW = 10.0

_LONG_LABELS = {
    'width': r'ширина|шир|width',
    'height': r'высота|выс|height',
    'depth': r'глубина|глуб|depth',
}
_SHORT_LABELS = {'width': 'ш', 'height': 'в', 'depth': 'г'}

_NOT_PRECEDED_BY_LETTER = r'(?<![а-яёa-z])'


def _axis_patterns():
    compiled = {}
    for axis, long_labels in _LONG_LABELS.items():
        short = _SHORT_LABELS[axis]
        long_label = rf'{_NOT_PRECEDED_BY_LETTER}(?:{long_labels})\.?\s*[:=-]?\s*({_NUMBER})\s*({_UNIT})?'
        short_spaced = rf'{_NOT_PRECEDED_BY_LETTER}{short}\.?\s*[:=-]?\s+({_NUMBER})\s*({_UNIT})'
        short_attached = rf'{_NOT_PRECEDED_BY_LETTER}{short}[.:=-]?({_NUMBER})\s*({_UNIT})?'
        compiled[axis] = [re.compile(p, re.IGNORECASE) for p in (long_label, short_spaced, short_attached)]
    return compiled


_AXIS_PATTERNS = _axis_patterns()
_COMPACT_TRIPLE = re.compile(
    rf'({_NUMBER})\s*[xх×*]\s*({_NUMBER})\s*[xх×*]\s*({_NUMBER})\s*({_UNIT})?',
    re.IGNORECASE,
)


def _to_cm(number, unit):
    value = float(number.replace(',', '.'))
    if unit:
        return round(value * _UNIT_FACTORS[unit.lower()], 2)

    # Unit-less: a fractional value below 10 is metres ("высота 2.30"); an integer is cm.
    if value < _BARE_VALUE_IS_METRES_BELOW and value != int(value):
        return round(value * 100.0, 2)

    return round(value, 2)


def _labelled(text):
    found = {}
    for axis, patterns in _AXIS_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                found[axis] = _to_cm(match.group(1), match.group(2))
                break

    return found


def _compact(text):
    match = _COMPACT_TRIPLE.search(text)
    if not match:
        return {}

    unit = match.group(4)
    return {axis: _to_cm(match.group(i), unit) for i, axis in enumerate(('width', 'height', 'depth'), start=1)}


def parse_dimensions(text):
    """Parse width/height/depth in cm from ``text``; unknown axes stay ``None``."""
    if not text:
        return Dimensions()

    found = _labelled(text) or _compact(text)
    return Dimensions(width_cm=found.get('width'), height_cm=found.get('height'), depth_cm=found.get('depth'))
