# modern-greek-backend-eee

Modern Greek (`el`) morphology backend for the
Ελληνικά Εκπαιδευτικά Εργαλεία (EEE) — Greek Language Educational Tools.

Implements `ModernGreekBackend`, satisfying the `MorphologyBackend` protocol
defined in the [`eee`](https://codeberg.org/EEE-project/eee-project) package.

Wraps [modern-greek-inflexion-eee](https://github.com/EEE-project/modern-greek-inflexion-eee),
a fork of Picus Zeus's [modern-greek-inflexion](https://github.com/PicusZeus/modern-greek-inflexion).
Deployed at [ellinika.com.pl](https://ellinika.com.pl). License: **MIT**.

Per the upstream README, the library "works thanks to a big corpus on which it
tests forms it tries to create." Word lists from
[Wikileksiko](https://wikilex.gr/) are used as lexical reference data for
accentuation and declension details (genitive existence, vocative endings in
-ος nouns).

**Period:** Standard Modern Greek (Demotic, post-1976). Primarily targets Νέα
Ελληνική Κοινή after the 1976 language reform that established Demotic as the
official standard. Some archaic forms are explicitly suppressed.


## Installation

```bash
pip install "modern-greek-backend-eee @ git+https://codeberg.org/EEE-project/modern-greek-backend-eee.git"
```


## Usage

```python
from modern_greek_backend_eee import ModernGreekBackend

backend = ModernGreekBackend()

# Verb — present active 1sg
forms = backend.inflect("γράφω", {
    "Tense": "Pres", "Person": "1", "Number": "Sing"
}, "verb")
# {"γράφω"}

# Noun — genitive plural
forms = backend.inflect("γυναίκα", {
    "Case": "Gen", "Number": "Plur"
}, "noun")
# {"γυναικών"}
```

Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).

Auto-registered via two entry point groups on install:
- `eee_project.backends.v1` → key `el` (default backend for Modern Greek)
- `eee_project.named_backends.v1` → key `modern-greek` (selectable via `backend="modern-greek"`)

This means `eee.inflect(..., language="el")` and `eee.inflect(..., backend="modern-greek")`
both work without explicit registration.


## Coverage

Rule-based algorithm: accepts any lemma as input, applies Modern Greek
morphological rules, and validates candidate forms against the corpus.
Returns an empty set only when the lemma is unrecognizable. Because there is
no finite lexicon, `list_lemmas()` is not supported.

| POS | Support |
|-----|---------|
| Verb | Full paradigm (all persons, tenses, moods) |
| Noun | All cases and numbers |
| Adjective | All genders, cases, numbers |
| Adverb | Positive / comparative |

**Limitations**

- Perfect and pluperfect are periphrastic in Modern Greek and not modeled —
  `inflect()` returns an empty set for `{"Tense": "Perf"}` or `{"Tense": "Pqp"}`.
- Some Katharevousa forms are explicitly suppressed.


## Diachronic paradigm rung (Odyssey)

`ModernGreekBackend` also powers the final **Modern** rung of the per-word
diachronic paradigm dropdown (Epic → Classical Attic → Hellenistic → Roman
Koine → **Modern**) in the Odyssey notebooks, wired via
`build_grc_lexicon_tabs(..., el_backend=ModernGreekBackend())`. The Ancient
polytonic lemma is normalized to monotonic (`poly_to_mono`) before inflection;
the rung is shown only when the backend yields a paradigm — words with no
living Modern reflex show no Modern rung (no changed/dead-lemma override map
yet, so archaic-but-inflectable lemmas render as the rule-based backend
produces them).


## Backend comparison — vs. `unimorph`

For `el` verbs, [unimorph-backend-eee](https://codeberg.org/EEE-project/unimorph-backend-eee)
is the other available backend. They differ in coverage shape rather than one
strictly superseding the other. Quick-glance summary — `unimorph-backend-eee`'s
own [Limitations](https://codeberg.org/EEE-project/unimorph-backend-eee#bundled-coverage)
section is the canonical source for the `unimorph` column's specifics:

| Feature | `modern-greek` (this package) | `unimorph` |
|---------|:--------------|:-----------|
| Perfect / pluperfect | empty set | verbal adjective (same form for all persons) |
| Imp Cont vs Imp Aor | correctly distinct | identical (no aspect tag in bundled `ell.tsv`) |
| Aor 3pl | standard -σαν only | may include -αν variant |
| Particle prefix (θα/να) | not included | stripped on load, re-added on display |


## Development

```bash
uv sync --dev
uv run pytest
```


## Status

v0.1.2
