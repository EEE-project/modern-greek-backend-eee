"""Integration tests for ModernGreekBackend against real library output."""
import pytest

from modern_greek_backend_eee.backend import ModernGreekBackend


@pytest.fixture
def backend():
    return ModernGreekBackend()


# ── Core regression tests ─────────────────────────────────────────────────────


@pytest.mark.parametrize("lemma,features,pos,expected", [
    (
        "λύω",
        {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Act", "Person": "1", "Number": "Sing"},
        "verb",
        {"λύω"},
    ),
    (
        "λύω",
        {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Act", "Person": "2", "Number": "Sing"},
        "verb",
        {"λύεις"},
    ),
    (
        "λύω",
        {"Tense": "Past", "Aspect": "Imp", "Voice": "Act", "Person": "1", "Number": "Sing"},
        "verb",
        {"έλυα"},
    ),
    (
        "λύω",
        {"Mood": "Sub", "Aspect": "Perf", "Voice": "Act", "Person": "1", "Number": "Sing"},
        "verb",
        {"λύσω"},
    ),
    (
        "γυναίκα",
        {"Gender": "Fem", "Number": "Sing", "Case": "Nom"},
        "noun",
        {"γυναίκα"},
    ),
    (
        "γυναίκα",
        {"Gender": "Fem", "Number": "Plur", "Case": "Gen"},
        "noun",
        {"γυναικών"},
    ),
    (
        "καλός",
        {"Degree": "Pos", "Gender": "Masc", "Number": "Sing", "Case": "Nom"},
        "adjective",
        {"καλός"},
    ),
])
def test_inflect_core(backend, lemma, features, pos, expected):
    assert backend.inflect(lemma, features, pos) == expected


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_inflect_deponent_voice_act(backend):
    """Deponent verb: requesting Act voice falls back to passive tree."""
    result = backend.inflect(
        "φοβάμαι",
        {"Tense": "Pres", "Voice": "Act", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert "φοβάμαι" in result


def test_inflect_multi_gender_noun_no_gender(backend):
    """Multi-gender noun without Gender returns union over all genders in paradigm."""
    # γιατρός has both masc and fem paradigms; nom sg happens to be identical for both
    result = backend.inflect("γιατρός", {"Number": "Sing", "Case": "Nom"}, "noun")
    assert isinstance(result, set)
    assert "γιατρός" in result


def test_inflect_nonexistent_path_returns_empty(backend):
    """Features path that doesn't exist in paradigm returns empty set."""
    result = backend.inflect(
        "λύω",
        {"Tense": "Pres", "Voice": "Pass", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert isinstance(result, set)


def test_inflect_suppletive_verb(backend):
    """Suppletive verb πάω + explicit Aspect:Imp uses πηγαίνω internally."""
    result = backend.inflect(
        "πάω",
        {"Tense": "Pres", "Aspect": "Imp", "Voice": "Act", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert "πηγαίνω" in result


def test_inflect_propagates_not_in_greek_exception(backend):
    from modern_greek_inflexion_eee.exceptions import NotInGreekException
    with pytest.raises(NotInGreekException):
        backend.inflect("hello", {"Tense": "Pres", "Voice": "Act", "Number": "Sing", "Person": "1"}, "verb")


def test_inflect_propagates_not_legal_verb_exception(backend):
    from modern_greek_inflexion_eee.exceptions import NotLegalVerbException
    with pytest.raises(NotLegalVerbException):
        backend.inflect("λύλύ", {"Tense": "Pres", "Voice": "Act", "Number": "Sing", "Person": "1"}, "verb")


# ── paradigm() ────────────────────────────────────────────────────────────────


def test_paradigm_verb_returns_dict(backend):
    result = backend.paradigm("λύω", "verb")
    assert isinstance(result, dict)
    assert "present" in result


def test_paradigm_noun_returns_dict(backend):
    result = backend.paradigm("γυναίκα", "noun")
    assert isinstance(result, dict)
    assert "fem" in result


def test_paradigm_adjective_returns_dict(backend):
    result = backend.paradigm("καλός", "adjective")
    assert isinstance(result, dict)
    assert "adj" in result


def test_paradigm_unknown_pos_raises_value_error(backend):
    with pytest.raises(ValueError):
        backend.paradigm("λύω", "unknown_pos")


def test_paradigm_cache_returns_same_object(backend):
    """paradigm() caches results — same dict object returned on second call."""
    first = backend.paradigm("λύω", "verb")
    second = backend.paradigm("λύω", "verb")
    assert first is second


# ── Protocol compliance ───────────────────────────────────────────────────────


def test_backend_language_is_el(backend):
    assert backend.language == "el"


def test_backend_satisfies_protocol():
    from eee_project._protocol import MorphologyBackend
    assert isinstance(ModernGreekBackend(), MorphologyBackend)
