"""UD feature dict → modern-greek-inflexion-eee nested-dict key paths.

No imports from modern-greek-inflexion-eee. Pure mapping logic.
Library string constants are reproduced here as module-level strings
so this module has zero runtime dependencies.
"""
from __future__ import annotations

# ── Library key constants (from modern-greek-inflexion-eee/resources/variables.py) ──

# Number
SG = "sg"
PL = "pl"

# Cases
NOM = "nom"
GEN = "gen"
ACC = "acc"
VOC = "voc"

# Genders
MASC = "masc"
FEM = "fem"
NEUT = "neut"

# Person
PRI = "pri"
SEC = "sec"
TER = "ter"  # 3rd person — library uses TER, not TRI

# Voice
ACTIVE = "active"
PASSIVE = "passive"

# Tense/aspect keys (top-level verb paradigm keys)
PRESENT = "present"
PARATATIKOS = "paratatikos"
AORIST = "aorist"
CONJUNCTIVE = "conjunctive"

# Mood (second-level under voice)
IND = "ind"   # indicative
IMP = "imp"   # imperative

# Adjective degree keys (Adjective.all() top-level keys)
ADJ = "adj"      # positive degree
COMP = "comp"    # comparative
SUPERL = "superl"  # superlative

# ── UD → library lookup tables ─────────────────────────────────────────────────

_UD_NUMBER = {"Sing": SG, "Plur": PL}
_UD_PERSON = {"1": PRI, "2": SEC, "3": TER}
_UD_VOICE = {"Act": ACTIVE, "Pass": PASSIVE}
_UD_MOOD_INNER = {"Ind": IND, "Imp": IMP, "Sub": IND}  # Sub inner mood is always IND
_UD_CASE = {"Nom": NOM, "Gen": GEN, "Acc": ACC, "Voc": VOC}
_UD_GENDER = {"Masc": MASC, "Fem": FEM, "Neut": NEUT}
_UD_DEGREE = {"Pos": ADJ, "Cmp": COMP, "Sup": SUPERL}

# ── Suppletive table ────────────────────────────────────────────────────────────

# Verbs where the imperfective stem comes from a different lemma.
# The backend calls suppletive_lemma() before invoking the library for
# imperfective (present/paratatikos) forms.
# Source: modern-greek-eee-checker's _SUPPLETIVE_SUBJUNCTIVE — one entry as of v2.x.
_SUPPLETIVE: dict[str, dict[str, str]] = {
    "πάω": {"Imp": "πηγαίνω"},
}


def suppletive_lemma(lemma: str, aspect: str | None) -> str:
    """Return the suppletive lemma for the given aspect, or lemma unchanged."""
    if aspect is None:
        return lemma
    entry = _SUPPLETIVE.get(lemma)
    if entry is None:
        return lemma
    return entry.get(aspect, lemma)


# ── Path builders ────────────────────────────────────────────────────────────────


def mg_verb_path(features: dict[str, str]) -> list[str]:
    """Map UD features to [tense, voice, mood, number, person] library key path.

    Raises KeyError if Number or Person is absent, or if tense cannot be
    determined from the features. Unknown UD feature keys are silently ignored.
    Returns bare path — deponent voice fallback is the caller's responsibility.
    Voice defaults to ACTIVE if absent. θα/να prefixes are NOT added here.
    Note: {Mood: Sub, Aspect: Imp} (continuous subjunctive) is not supported
    and raises KeyError — not in the v1 spec.
    """
    mood = features.get("Mood", "Ind")
    aspect = features.get("Aspect")
    tense = features.get("Tense")

    # Determine tense key
    if mood == "Sub" and aspect == "Perf":
        tense_key = CONJUNCTIVE
    elif mood == "Imp" and aspect == "Perf":
        # library shares the conjunctive key for both aorist subjunctive and aorist imperative
        tense_key = CONJUNCTIVE
    elif tense == "Pres" and (aspect is None or aspect == "Imp"):
        # Pres without explicit Aspect is always imperfective in Greek
        tense_key = PRESENT
    elif tense == "Past" and aspect == "Imp":
        tense_key = PARATATIKOS
    elif tense == "Past" and aspect == "Perf":
        tense_key = AORIST
    elif tense == "Fut" and (aspect is None or aspect == "Imp"):
        # θα/να Ipfv: same stem as Present
        tense_key = PRESENT
    elif tense == "Fut" and aspect == "Perf":
        # θα/να Pfv: same stem as Conjunctive
        tense_key = CONJUNCTIVE
    else:
        raise KeyError(f"Cannot determine tense from features: {features!r}")

    voice_key = _UD_VOICE[features["Voice"]] if "Voice" in features else ACTIVE
    mood_key = _UD_MOOD_INNER.get(mood, IND)
    number_key = _UD_NUMBER[features["Number"]]
    person_key = _UD_PERSON[features["Person"]]

    return [tense_key, voice_key, mood_key, number_key, person_key]


def mg_noun_path(features: dict[str, str]) -> list[str] | None:
    """Map UD features to [gender, number, case] library key path.

    Returns None if Gender is not in features (caller iterates all genders).
    Raises KeyError if Number or Case is absent.
    """
    gender = features.get("Gender")
    if gender is None:
        return None

    gender_key = _UD_GENDER[gender]
    number_key = _UD_NUMBER[features["Number"]]
    case_key = _UD_CASE[features["Case"]]

    return [gender_key, number_key, case_key]


def mg_adj_path(features: dict[str, str]) -> list[str]:
    """Map UD features to [degree, number, gender, case] library key path.

    Degree defaults to positive (ADJ) if not in features.
    Raises KeyError if Number, Gender, or Case is absent.
    """
    degree_ud = features.get("Degree", "Pos")
    degree_key = _UD_DEGREE[degree_ud]

    number_key = _UD_NUMBER[features["Number"]]
    gender_key = _UD_GENDER[features["Gender"]]
    case_key = _UD_CASE[features["Case"]]

    return [degree_key, number_key, gender_key, case_key]
