"""Tests for UD ↔ modern-greek-inflexion-eee feature path mapping."""
import pytest

from modern_greek_backend_eee._mg_features import (
    ACC,
    ADJ,
    ACTIVE,
    AORIST,
    COMP,
    CONJUNCTIVE,
    FEM,
    GEN,
    IMP,
    IND,
    MASC,
    NEUT,
    NOM,
    PARATATIKOS,
    PASSIVE,
    PL,
    PRESENT,
    PRI,
    SEC,
    SG,
    SUPERL,
    TER,
    VOC,
    mg_adj_path,
    mg_noun_path,
    mg_verb_path,
    suppletive_lemma,
)


# ── mg_verb_path ──────────────────────────────────────────────────────────────


def test_verb_present_active_ind_sg_pri():
    feats = {"Tense": "Pres", "Aspect": "Imp", "Voice": "Act", "Mood": "Ind", "Number": "Sing", "Person": "1"}
    assert mg_verb_path(feats) == [PRESENT, ACTIVE, IND, SG, PRI]


def test_verb_paratatikos_first_key():
    feats = {"Tense": "Past", "Aspect": "Imp", "Voice": "Act", "Mood": "Ind", "Number": "Sing", "Person": "1"}
    assert mg_verb_path(feats)[0] == PARATATIKOS


def test_verb_aorist_first_key():
    feats = {"Tense": "Past", "Aspect": "Perf", "Voice": "Act", "Mood": "Ind", "Number": "Sing", "Person": "1"}
    assert mg_verb_path(feats)[0] == AORIST


def test_verb_conjunctive_first_key():
    feats = {"Mood": "Sub", "Aspect": "Perf", "Voice": "Act", "Number": "Sing", "Person": "1"}
    assert mg_verb_path(feats)[0] == CONJUNCTIVE


def test_verb_passive_second_key():
    feats = {"Voice": "Pass", "Tense": "Pres", "Aspect": "Imp", "Mood": "Ind", "Number": "Sing", "Person": "1"}
    assert mg_verb_path(feats)[1] == PASSIVE


def test_verb_unknown_feature_silently_ignored():
    feats = {
        "Tense": "Pres", "Aspect": "Imp", "Voice": "Act", "Mood": "Ind",
        "Number": "Sing", "Person": "1",
        "Polarity": "Neg",  # unknown key
    }
    assert mg_verb_path(feats) == [PRESENT, ACTIVE, IND, SG, PRI]


def test_verb_missing_number_raises():
    feats = {"Tense": "Pres", "Aspect": "Imp", "Voice": "Act", "Mood": "Ind", "Person": "1"}
    with pytest.raises(KeyError):
        mg_verb_path(feats)


def test_verb_missing_person_raises():
    feats = {"Tense": "Pres", "Aspect": "Imp", "Voice": "Act", "Mood": "Ind", "Number": "Sing"}
    with pytest.raises(KeyError):
        mg_verb_path(feats)


def test_verb_third_person_plural():
    feats = {"Tense": "Pres", "Aspect": "Imp", "Voice": "Act", "Mood": "Ind", "Number": "Plur", "Person": "3"}
    path = mg_verb_path(feats)
    assert path == [PRESENT, ACTIVE, IND, PL, TER]


def test_verb_second_person_singular():
    feats = {"Tense": "Pres", "Aspect": "Imp", "Voice": "Act", "Mood": "Ind", "Number": "Sing", "Person": "2"}
    path = mg_verb_path(feats)
    assert path[4] == SEC


# ── mg_noun_path ──────────────────────────────────────────────────────────────


def test_noun_masc_sg_nom():
    feats = {"Gender": "Masc", "Number": "Sing", "Case": "Nom"}
    assert mg_noun_path(feats) == [MASC, SG, NOM]


def test_noun_fem_pl_gen():
    feats = {"Gender": "Fem", "Number": "Plur", "Case": "Gen"}
    assert mg_noun_path(feats) == [FEM, PL, GEN]


def test_noun_no_gender_returns_none():
    feats = {"Number": "Sing", "Case": "Nom"}
    assert mg_noun_path(feats) is None


def test_noun_neut_sg_nom():
    feats = {"Gender": "Neut", "Number": "Sing", "Case": "Nom"}
    assert mg_noun_path(feats)[0] == NEUT


def test_noun_voc_at_index_two():
    feats = {"Case": "Voc", "Gender": "Masc", "Number": "Sing"}
    assert mg_noun_path(feats)[2] == VOC


def test_noun_missing_case_raises():
    feats = {"Gender": "Masc", "Number": "Sing"}
    with pytest.raises(KeyError):
        mg_noun_path(feats)


# ── mg_adj_path ───────────────────────────────────────────────────────────────


def test_adj_positive_degree():
    feats = {"Degree": "Pos", "Number": "Sing", "Gender": "Masc", "Case": "Nom"}
    path = mg_adj_path(feats)
    assert len(path) == 4
    assert path[0] == ADJ


def test_adj_degree_defaults_to_positive():
    feats = {"Number": "Sing", "Gender": "Masc", "Case": "Nom"}
    path = mg_adj_path(feats)
    assert path[0] == ADJ


def test_adj_comparative_degree():
    feats = {"Degree": "Cmp", "Number": "Sing", "Gender": "Masc", "Case": "Nom"}
    assert mg_adj_path(feats)[0] == COMP


def test_adj_superlative_degree():
    feats = {"Degree": "Sup", "Number": "Sing", "Gender": "Masc", "Case": "Nom"}
    assert mg_adj_path(feats)[0] == SUPERL


def test_adj_full_path_neut_pl_gen():
    feats = {"Degree": "Pos", "Number": "Plur", "Gender": "Neut", "Case": "Gen"}
    assert mg_adj_path(feats) == [ADJ, PL, NEUT, GEN]


# ── suppletive_lemma ──────────────────────────────────────────────────────────


def test_suppletive_pao_imperfective():
    assert suppletive_lemma("πάω", "Imp") == "πηγαίνω"


def test_suppletive_pao_perfective_unchanged():
    assert suppletive_lemma("πάω", "Perf") == "πάω"


def test_suppletive_regular_verb_unchanged():
    assert suppletive_lemma("λύω", "Imp") == "λύω"


def test_suppletive_none_aspect_unchanged():
    assert suppletive_lemma("πάω", None) == "πάω"


def test_verb_present_without_aspect_defaults_to_present():
    # UD may omit Aspect for present tense; Greek Pres is always imperfective
    feats = {"Tense": "Pres", "Mood": "Ind", "Voice": "Act", "Number": "Sing", "Person": "1"}
    assert mg_verb_path(feats)[0] == PRESENT


def test_verb_imperative_aorist():
    # Aorist imperative forms live under the conjunctive key in the paradigm, not aorist
    feats = {"Mood": "Imp", "Aspect": "Perf", "Voice": "Act", "Number": "Sing", "Person": "2"}
    assert mg_verb_path(feats) == [CONJUNCTIVE, ACTIVE, IMP, SG, SEC]


def test_noun_missing_number_raises():
    feats = {"Gender": "Masc", "Case": "Nom"}
    with pytest.raises(KeyError):
        mg_noun_path(feats)


def test_adj_unknown_degree_raises():
    feats = {"Degree": "Abs", "Number": "Sing", "Gender": "Masc", "Case": "Nom"}
    with pytest.raises(KeyError):
        mg_adj_path(feats)
