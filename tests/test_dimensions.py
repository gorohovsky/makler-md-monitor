"""Free-text dimension extraction — the core off-site filter criterion."""

import pytest

from makler_monitor.dimensions import parse_dimensions

# (text, width_cm, height_cm, depth_cm)
CASES = [
    # Labelled, full Russian words (the real example seen on makler.md).
    ('размеры ширина 190 см высота 215 см', 190, 215, None),
    ('Ширина 120 см, высота 220 см, глубина 45 см', 120, 220, 45),
    # Order is irrelevant; missing unit defaults to centimetres.
    ('высота 230, ширина 100, глубина 60', 100, 230, 60),
    ('ширина: 120, высота: 220, глубина: 50', 120, 220, 50),
    # Multi-letter abbreviations with a trailing dot.
    ('шир. 120 выс. 220 глуб. 50', 120, 220, 50),
    # Single-letter labels require a unit (spaced or attached) so prose isn't misread.
    ('Ш 120 см В 220 см Г 50 см', 120, 220, 50),
    ('Ш120см В220см Г50см', 120, 220, 50),
    # ...so bare single-letter-plus-number prose is NOT read as a dimension.
    ('куплен в2020 году', None, None, None),
    ('дешевле в2 раза', None, None, None),
    ('г.50 в адресе', None, None, None),
    # English labels appear occasionally in seller text.
    ('width 130 cm, height 230 cm, depth 50 cm', 130, 230, 50),
    # Unit conversion: metres and millimetres, decimal point and comma.
    ('высота 2.2 м', None, 220, None),
    ('ширина 1,2 м', 120, None, None),
    ('глубина 500 мм', None, None, 50),
    # A unit-less value below 10 is metres ("высота 2" or "высота 2.30"), never cm —
    # sampling real ads shows unit-less values cluster below 3 or at/above 30, never between.
    ('высота 2.30', None, 230, None),
    ('высота 2', None, 200, None),
    ('ширина 1', 100, None, None),
    ('размер 0.46 * 1.34, высота 2.30', None, 230, None),
    ('ширина 1.5', 150, None, None),
    ('глубина 0.5', None, None, 50),
    ('высота 0.92, глубина 0.32', None, 92, 32),
    ('Высота 2,10, ширина 1.50', 150, 210, None),
    # Compact NxNxN (assumed width x height x depth) — Cyrillic and Latin separators.
    ('Шкаф-купе 120х220х50', 120, 220, 50),
    ('размеры 120x220x50 см', 120, 220, 50),
    ('габариты 120*220*50', 120, 220, 50),
    ('120 × 220 × 50 см', 120, 220, 50),
    ('1.2х2.2х0.5 м', 120, 220, 50),
    # Compact axis order varies by seller, so assign by magnitude (largest=height,
    # smallest=depth, middle=width) — the same physical box whatever the written order.
    ('220х50х120', 120, 220, 50),
    ('50х120х220', 120, 220, 50),
    # False positives must NOT be read as dimensions.
    ('Продаю шкаф, цена 900 евро, куплен 3 года назад', None, None, None),
    ('Телефон 373 77 875053, звоните', None, None, None),
    ('Шкаф в идеальном состоянии, в наличии', None, None, None),
    ('Три полки, 2 двери', None, None, None),
]


@pytest.mark.parametrize('text, width, height, depth', CASES)
def test_parse_dimensions(text, width, height, depth):
    dims = parse_dimensions(text)

    assert (dims.width_cm, dims.height_cm, dims.depth_cm) == (width, height, depth)


def test_blank_input_is_empty():
    assert parse_dimensions('').is_empty
    assert parse_dimensions(None).is_empty


def test_is_empty_false_when_any_axis_known():
    assert not parse_dimensions('глубина 50 см').is_empty
