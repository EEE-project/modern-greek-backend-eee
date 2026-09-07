"""ModernGreekBackend — delegates to modern-greek-inflexion-eee."""
from __future__ import annotations

import csv
import functools
import importlib.resources

from modern_greek_backend_eee._mg_features import (
    ACTIVE,
    FEM,
    MASC,
    MG_VERB_PERIPHRASTIC_PASSIVE_PATH,
    NEUT,
    PASSIVE,
    mg_adj_path,
    mg_noun_path,
    mg_pron_path,
    mg_pron_strong,
    mg_verb_is_periphrastic,
    mg_verb_path,
    suppletive_lemma,
)

_GENDER_KEYS = frozenset({MASC, FEM, NEUT})

# pos → filename stem of the label TSVs in eee_project.data.labels
_LABEL_STEM = {
    "noun": "noun", "adjective": "adj", "verb": "verb",
    "pronoun": "pronoun", "article": "article", "numeral": "numeral",
}

# Article only ever accepts these two lemmas -- see Article.all()'s own
# "it's not a Greek article" check.
_ARTICLE_LEMMAS = ("ο", "ένας")


@functools.lru_cache(maxsize=None)
def _pron_shape(lemma: str) -> str:
    """Classify a pronoun lemma into the shape mg_pron_path() needs.

    Reads modern_greek_inflexion_eee's own PRONOUN_LEMMAS_* sets -- the
    single source of truth for which lemmas exist and what shape each
    produces (see that module for how this was derived). Unknown lemmas
    default to "gendered", matching Pronoun.all()'s own majority shape;
    they'll simply fail against mg_pron_path() the same way an unknown verb
    fails against mg_verb_path() -- not this function's job to validate.
    """
    from modern_greek_inflexion_eee import PRONOUN_LEMMAS_INDECLINABLE, PRONOUN_LEMMAS_PERSONAL

    if lemma in PRONOUN_LEMMAS_INDECLINABLE:
        return "indeclinable"
    if lemma in PRONOUN_LEMMAS_PERSONAL:
        return "personal"
    return "gendered"


@functools.lru_cache(maxsize=None)
def _numeral_pos(lemma: str) -> str:
    """Classify a numeral lemma as noun-type or adjective-type for Numeral(pos=).

    Reads modern_greek_inflexion_eee's own quant_noun list. Defaults to
    "adj" (Numeral's own default and the majority case: ordinals,
    multiplicatives, and basic cardinals are all adjective-shaped; only
    collective/quantity words like χιλιάδα "thousand" are noun-shaped).
    """
    from modern_greek_inflexion_eee import quant_noun

    return "noun" if lemma in quant_noun else "adj"


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


def _inflect_noun_shaped(full_paradigm: dict, features: dict[str, str]) -> set[str]:
    """Shared noun-gender-path walk for pos="noun" and noun-shaped numerals."""
    gender_path = mg_noun_path(features)
    if gender_path is None:
        rest_path = mg_noun_path({**features, "Gender": "Masc"})[1:]
        return _walk_gender_union(full_paradigm, rest_path)
    return _walk(full_paradigm, gender_path)


def _gendered_case_num_rows() -> list[dict[str, str]]:
    """4 cases x 2 numbers x 3 genders -- shared by get_tags()'s noun/adjective
    and pronoun/article/numeral branches."""
    return [
        {"tag": f"{case}|{num}|{gender}", "Case": case, "Number": num, "Gender": gender}
        for case in ("Nom", "Gen", "Acc", "Voc")
        for num in ("Sing", "Plur")
        for gender in ("Masc", "Fem", "Neut")
    ]


class ModernGreekBackend:
    """Morphology backend for Modern Greek (language tag: 'el').

    Delegates to modern-greek-inflexion-eee. Satisfies the MorphologyBackend Protocol.
    """

    language: str = "el"

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str, bool], dict] = {}
        self._slot_cache: dict[tuple[str, str], list] = {}

    def inflect(self, lemma: str, features: dict[str, str], pos: str, **_kw) -> set[str]:
        """Return inflected forms matching the given UD feature bundle.

        Returns an empty set if the requested path doesn't exist in the paradigm.
        Raises NotInGreekException or NotLegalVerbException from the underlying
        library without wrapping.
        """
        if pos == "verb":
            if mg_verb_is_periphrastic(features):
                return self._inflect_verb_periphrastic(lemma, features)
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
            return _inflect_noun_shaped(full_paradigm, features)

        elif pos in ("adjective", "adverb"):
            full_paradigm = self.paradigm(lemma, pos)
            path = mg_adj_path(features)
            return _walk(full_paradigm, path)

        elif pos == "pronoun":
            strong = mg_pron_strong(features)
            full_paradigm = self.paradigm(lemma, pos, strong=strong)
            path = mg_pron_path(_pron_shape(lemma), features)
            return _walk(full_paradigm, path)

        elif pos == "article":
            full_paradigm = self.paradigm(lemma, pos)
            path = mg_pron_path("gendered", features)
            return _walk(full_paradigm, path)

        elif pos == "numeral":
            full_paradigm = self.paradigm(lemma, pos)
            if _numeral_pos(lemma) == "noun":
                return _inflect_noun_shaped(full_paradigm, features)
            path = mg_adj_path(features)
            return _walk(full_paradigm, path)

        else:
            raise ValueError(f"Unknown POS for inflect: {pos!r}")

    def _inflect_verb_periphrastic(self, lemma: str, features: dict[str, str]) -> set[str]:
        """Perfect/pluperfect: [conjugated έχω/είχα] + [invariant non-finite form].

        Not a single synthetic word -- periphrastic, two words. UD's own Tense
        feature has no value for present/periphrastic perfect at all (only
        Fut/Imp/Past/Pqp/Pres); their documented convention for such
        constructions is to tag the auxiliary and the non-finite form
        separately rather than invent a combined tense value. This method
        does the composition at the API boundary instead (see get_tags()'s
        comment on why Pres+Aspect=Perf/Pqp are used as the calling features
        anyway), keeping inflect()'s one-call-one-form-set contract intact
        for callers.

        Active: the non-finite piece is the aparemfato -- historically the
        same form Modern Greek's simple future already uses (θα γράψει /
        έχει γράψει are the identical word), so it's just the existing
        Fut.Perf.Act.3.Sg cell, fetched via a recursive inflect() call so
        suppletion and deponent fallback still apply automatically.

        Passive: no single-word slot for this exists anywhere else in the
        API. Pulled directly from paradigm()'s raw passive_perfect_participle
        (already generated by modern-greek-inflexion-eee, just never routed
        through inflect()/get_tags() before now) at its neuter singular
        cell -- invariant when used with έχω this way, and neuter nominative
        and accusative are always identical in Greek, so either case works.
        """
        aux_tense = (
            {"Tense": "Past", "Aspect": "Imp", "Mood": "Ind"}
            if features["Tense"] == "Pqp"
            else {"Tense": "Pres", "Mood": "Ind"}
        )
        aux_forms = self.inflect(
            "έχω",
            {**aux_tense, "Voice": "Act", "Person": features["Person"], "Number": features["Number"]},
            "verb",
        )
        if features["Voice"] == "Act":
            non_finite = self.inflect(
                lemma,
                {"Tense": "Fut", "Aspect": "Perf", "Mood": "Ind", "Voice": "Act", "Person": "3", "Number": "Sing"},
                "verb",
            )
        else:
            full_paradigm = self.paradigm(lemma, "verb")
            non_finite = _walk(full_paradigm, MG_VERB_PERIPHRASTIC_PASSIVE_PATH)
        return {f"{aux} {nf}" for aux in aux_forms for nf in non_finite}

    def get_tags(self, pos: str) -> list[dict[str, str]]:
        """Enumerate all slot feature combinations for pos.

        Returns rows of {tag, ...UD features}. tag is a canonical string
        for identification; dispatch uses tag_type='ud' (features, not tag).
        Modern Greek nouns/adj use 4 cases (no Dative).
        """
        if pos in ("noun", "adjective"):
            rows = _gendered_case_num_rows()
            for case in ("Nom", "Gen", "Acc", "Voc"):
                for num in ("Sing", "Plur"):
                    rows.append({"tag": f"{case}|{num}", "Case": case, "Number": num})
            return rows

        if pos in ("article", "numeral"):
            # No gender-omitted variant here (unlike noun/adjective above):
            # inflect()'s article/numeral paths require Gender present for
            # the "gendered" shape (mg_pron_path raises KeyError without
            # it) -- omitting it would produce a slot that crashes when
            # actually used, not one that unions across genders.
            return _gendered_case_num_rows()

        if pos == "pronoun":
            # Unlike article/numeral above, pronoun has a real strong/weak
            # (UD Clitic) distinction -- see _mg_features.py's
            # mg_pron_strong() -- that get_tags() never used to surface,
            # making it reachable only by a caller who already knew to
            # hand-build {"Clitic": "Yes"} out of band. The 24 base rows
            # keep their exact existing tags with Clitic absent (preserving
            # mg_pron_strong()'s "absent = strong" contract, so nothing
            # dispatching on today's tags breaks); 24 more rows add
            # Clitic="Yes" with a distinct tag. Harmless duplication for
            # pronoun families where Clitic doesn't change anything
            # (mg_pron_strong()'s own docstring: "no-op for every other
            # pronoun lemma") -- get_tags() enumerates per POS, not per
            # lemma, so there's no narrower point to hook this at.
            base_rows = _gendered_case_num_rows()
            clitic_rows = [{**row, "tag": f"{row['tag']}|Clitic", "Clitic": "Yes"} for row in base_rows]
            return base_rows + clitic_rows

        if pos == "verb":
            rows = []
            # Indicative: 7 tense-aspect forms × 2 voices × 6 (person × number) = 84
            for base in (
                {"Tense": "Pres", "Mood": "Ind"},
                {"Tense": "Past", "Aspect": "Imp", "Mood": "Ind"},
                {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind"},
                {"Tense": "Fut", "Aspect": "Imp", "Mood": "Ind"},
                {"Tense": "Fut", "Aspect": "Perf", "Mood": "Ind"},
                # Periphrastic perfect/pluperfect (έχω/είχα + invariant non-finite
                # form) -- not a UD Tense value at all for present perfect (UD's own
                # convention is to tag the two words separately, see
                # _inflect_verb_periphrastic below), so Pres+Aspect=Perf is a local
                # choice here, consistent with how Aspect=Perf already marks
                # perfective-stem-based forms elsewhere in this same table. Pqp is a
                # real UD value UD documents as conceptually correct even though they
                # don't apply it to periphrastic constructions either.
                {"Tense": "Pres", "Aspect": "Perf", "Mood": "Ind"},
                {"Tense": "Pqp", "Mood": "Ind"},
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

    def list_lemmas(self, pos: str) -> list[str]:
        """Return known lemmas for pos, or [] for open/unbounded word classes.

        verb/noun/adjective/adverb work from arbitrary input strings via
        pattern-matched stemming rules, not a bundled lexicon -- there is no
        finite list to enumerate for them, matching eee-project's own
        "[] for algorithm-based backends with no finite vocabulary"
        convention. pronoun and article are genuinely closed classes.
        numeral's list only covers modern_greek_inflexion_eee's own
        quant_adj/quant_noun (ordinals, multiplicatives, and quantity nouns)
        -- basic cardinal numbers (one/two/three...) live in that library's
        separate quant/hundreds lists, which use a comma/slash-delimited
        multi-spelling format not cleanly enumerable without new parsing
        work; inflect()/paradigm() still work for them directly by lemma,
        this only affects lemma-picker UIs.
        """
        if pos == "pronoun":
            from modern_greek_inflexion_eee import PRONOUN_LEMMAS
            return sorted(PRONOUN_LEMMAS)
        if pos == "article":
            return sorted(_ARTICLE_LEMMAS)
        if pos == "numeral":
            from modern_greek_inflexion_eee import quant_adj, quant_noun
            return sorted(set(quant_adj) | set(quant_noun))
        return []

    def paradigm(self, lemma: str, pos: str, *, strong: bool = True) -> dict:
        """Return the full inflectional paradigm for a lemma.

        Results are cached per (lemma, pos, strong). strong only affects
        pos="pronoun" (see Pronoun's own strong= constructor arg -- weak vs
        strong/emphatic forms); every other pos ignores it, so its default
        keeps their cache key stable at (lemma, pos, True). Not part of the
        MorphologyBackend Protocol — available on ModernGreekBackend
        directly. The cache is not thread-safe; use a separate instance per
        thread for concurrent use.

        Raises ValueError for unknown pos values.
        Raises NotInGreekException or NotLegalVerbException from the library.
        """
        key = (lemma, pos, strong)
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
        elif pos == "pronoun":
            from modern_greek_inflexion_eee import Pronoun
            result = Pronoun(lemma, strong=strong).all()
        elif pos == "article":
            from modern_greek_inflexion_eee import Article
            result = Article(lemma).all()
        elif pos == "numeral":
            from modern_greek_inflexion_eee import Numeral
            result = Numeral(lemma, pos=_numeral_pos(lemma)).all()
        else:
            raise ValueError(f"Unknown POS: {pos!r}")

        self._cache[key] = result
        return result
