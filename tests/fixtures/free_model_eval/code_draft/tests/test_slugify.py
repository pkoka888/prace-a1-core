from solution.slugify import slugify


def test_words_are_separated_and_trimmed():
    assert slugify("  Synthetic Atlas Portal  ") == "synthetic-atlas-portal"


def test_repeated_separators_collapse():
    assert slugify("alpha___beta---gamma") == "alpha-beta-gamma"


def test_empty_and_symbols():
    assert slugify(" !!! ") == ""
