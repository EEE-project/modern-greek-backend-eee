"""ModernGreekBackend — delegates to modern-greek-inflexion-eee."""
from __future__ import annotations

from modern_greek_backend_eee._mg_features import (
    ACTIVE,
    FEM,
    MASC,
    NEUT,
    PASSIVE,
    mg_adj_path,
    mg_noun_path,
    mg_verb_path,
    suppletive_lemma,
)

_GENDER_KEYS = frozenset({MASC, FEM, NEUT})


def _walk(d: dict, path: list[str]) -> set[str]:
    """Walk nested dict along path; return leaf set or empty set if any key missing."""
    for key in path:
        if not isinstance(d, dict):
            return set()
        d = d.get(key, {})
    if isinstance(d, set):
        return d
    if isinstance(d, (list, frozenset)):
        return set(d)
    if isinstance(d, str):
        return {d}
    return set()


def _walk_gender_union(paradigm: dict, number_case_path: list[str]) -> set[str]:
    result: set[str] = set()
    for gender_key in _GENDER_KEYS:
        if gender_key in paradigm:
            result |= _walk(paradigm[gender_key], number_case_path)
    return result


class ModernGreekBackend:
    """Morphology backend for Modern Greek (language tag: 'el').

    Delegates to modern-greek-inflexion-eee. Satisfies the MorphologyBackend Protocol.
    """

    language: str = "el"

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], dict] = {}

    def inflect(self, lemma: str, features: dict[str, str], pos: str, **_kw) -> set[str]:
        """Return inflected forms matching the given UD feature bundle.

        Returns an empty set if the requested path doesn't exist in the paradigm.
        Raises NotInGreekException or NotLegalVerbException from the underlying
        library without wrapping.
        """
        if pos == "verb":
            aspect = features.get("Aspect")
            actual_lemma = suppletive_lemma(lemma, aspect)
            full_paradigm = self.paradigm(actual_lemma, pos)
            try:
                path = mg_verb_path(features)
            except KeyError:
                return set()
            result = _walk(full_paradigm, path)
            # Deponent fallback: if ACTIVE path yields nothing, retry with PASSIVE
            assert len(path) == 5, f"Unexpected verb path length: {path!r}"
            if not result and path[1] == ACTIVE:
                deponent_path = [path[0], PASSIVE] + path[2:]
                result = _walk(full_paradigm, deponent_path)
            return result

        elif pos == "noun":
            full_paradigm = self.paradigm(lemma, pos)
            gender_path = mg_noun_path(features)
            if gender_path is None:
                rest_path = mg_noun_path({**features, "Gender": "Masc"})[1:]
                return _walk_gender_union(full_paradigm, rest_path)
            return _walk(full_paradigm, gender_path)

        elif pos in ("adjective", "adverb"):
            full_paradigm = self.paradigm(lemma, pos)
            path = mg_adj_path(features)
            return _walk(full_paradigm, path)

        else:
            raise ValueError(f"Unknown POS for inflect: {pos!r}")

    def paradigm(self, lemma: str, pos: str) -> dict:
        """Return the full inflectional paradigm for a lemma.

        Results are cached per (lemma, pos). Not part of the MorphologyBackend
        Protocol — available on ModernGreekBackend directly. The cache is not
        thread-safe; use a separate instance per thread for concurrent use.

        Raises ValueError for unknown pos values.
        Raises NotInGreekException or NotLegalVerbException from the library.
        """
        key = (lemma, pos)
        if key in self._cache:
            return self._cache[key]

        if pos == "verb":
            from modern_greek_inflexion_eee import Verb
            result = Verb(lemma).all()
        elif pos == "noun":
            from modern_greek_inflexion_eee import Noun
            result = Noun(lemma).all()
        elif pos == "adjective":
            from modern_greek_inflexion_eee import Adjective
            result = Adjective(lemma).all()
        elif pos == "adverb":
            from modern_greek_inflexion_eee import Adverb
            result = Adverb(lemma).all()
        else:
            raise ValueError(f"Unknown POS: {pos!r}")

        self._cache[key] = result
        return result
