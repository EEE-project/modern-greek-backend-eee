"""ModernGreekBackend — delegates to modern-greek-inflexion-eee."""
from __future__ import annotations

import csv
import importlib.resources

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

# pos → filename stem of the label TSVs in eee_project.data.labels
_LABEL_STEM = {"noun": "noun", "adjective": "adj", "verb": "verb"}


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
        self._slot_cache: dict[tuple[str, str], list] = {}

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

    def get_tags(self, pos: str) -> list[dict[str, str]]:
        """Enumerate all slot feature combinations for pos.

        Returns rows of {tag, ...UD features}. tag is a canonical string
        for identification; dispatch uses tag_type='ud' (features, not tag).
        Modern Greek nouns/adj use 4 cases (no Dative).
        """
        if pos in ("noun", "adjective"):
            rows = []
            for case in ("Nom", "Gen", "Acc", "Voc"):
                for num in ("Sing", "Plur"):
                    for gender in ("Masc", "Fem", "Neut"):
                        rows.append({"tag": f"{case}|{num}|{gender}", "Case": case, "Number": num, "Gender": gender})
            for case in ("Nom", "Gen", "Acc", "Voc"):
                for num in ("Sing", "Plur"):
                    rows.append({"tag": f"{case}|{num}", "Case": case, "Number": num})
            return rows

        if pos == "verb":
            rows = []
            # Indicative: 5 tense-aspect forms × 2 voices × 6 (person × number) = 60
            for base in (
                {"Tense": "Pres", "Mood": "Ind"},
                {"Tense": "Past", "Aspect": "Imp", "Mood": "Ind"},
                {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind"},
                {"Tense": "Fut", "Aspect": "Imp", "Mood": "Ind"},
                {"Tense": "Fut", "Aspect": "Perf", "Mood": "Ind"},
            ):
                for voice in ("Act", "Pass"):
                    for person in ("1", "2", "3"):
                        for num in ("Sing", "Plur"):
                            feats = {**base, "Voice": voice, "Person": person, "Number": num}
                            tense = feats["Tense"]
                            tense_part = f"{tense}.{feats['Aspect']}" if "Aspect" in feats else tense
                            tag = f"{tense_part}|{feats['Mood']}|{voice}|{person}|{num}"
                            rows.append({"tag": tag, **feats})
            # Subjunctive (perfective): 2 voices × 6 = 12
            for voice in ("Act", "Pass"):
                for person in ("1", "2", "3"):
                    for num in ("Sing", "Plur"):
                        feats = {"Mood": "Sub", "Aspect": "Perf", "Voice": voice, "Person": person, "Number": num}
                        rows.append({"tag": f"Sub.Perf|{voice}|{person}|{num}", **feats})
            # Imperative: 2 aspects × 2 voices × 2 numbers = 8
            for aspect in ("Imp", "Perf"):
                for voice in ("Act", "Pass"):
                    for num in ("Sing", "Plur"):
                        feats = {"Mood": "Imp", "Aspect": aspect, "Voice": voice, "Person": "2", "Number": num}
                        rows.append({"tag": f"Imp.{aspect}|{voice}|2|{num}", **feats})
            return rows

        return []

    def get_slot_templates(
        self, lang: str, pos: str, terms_lang: str = "en"
    ) -> "list | None":
        """Return slot templates for (pos, terms_lang) built from get_tags() + bundled label TSV.

        Each SlotTemplate has tag_type='ud' and features matching the UD feature dict
        used by inflect(). Labels come from eee_project.data.labels/{stem}-{terms_lang}.tsv;
        falls back to the English TSV when the requested terms_lang is absent.
        Returns None for unknown pos values. Results are cached per (pos, terms_lang).
        """
        from eee_project._slot_template import SlotTemplate

        cache_key = (pos, terms_lang)
        if cache_key in self._slot_cache:
            return self._slot_cache[cache_key]

        tags = self.get_tags(pos)
        if not tags:
            return None

        pkg = importlib.resources.files("eee_project.data.labels")
        stem = _LABEL_STEM.get(pos, pos)
        text: "str | None" = None
        for lng in dict.fromkeys((terms_lang, "en")):
            try:
                text = (pkg / f"{stem}-{lng}.tsv").read_text(encoding="utf-8")
                break
            except FileNotFoundError:
                pass

        labels: "dict[frozenset, str]" = {}
        if text:
            for row in csv.DictReader(text.splitlines(), delimiter="\t"):
                key = frozenset((k, v) for k, v in row.items() if k != "label" and v)
                labels[key] = row["label"]

        result = []
        for tag_row in tags:
            feat_key = frozenset((k, v) for k, v in tag_row.items() if k != "tag" and v)
            label = labels.get(feat_key, tag_row["tag"])
            features = {k: v for k, v in tag_row.items() if k != "tag"}
            result.append(SlotTemplate(
                label=label,
                tag=tag_row["tag"],
                tag_type="ud",
                features=features,
            ))
        self._slot_cache[cache_key] = result
        return result

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
