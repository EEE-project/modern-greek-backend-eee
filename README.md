# modern-greek-backend-eee

Modern Greek (`el`) morphology backend for the
Ελληνικά Εκπαιδευτικά Εργαλεία (EEE) — Greek Language Educational Tools.

Implements `ModernGreekBackend`, satisfying the `MorphologyBackend` protocol
defined in the [`eee`](https://codeberg.org/EEE-project/eee-project) package.

Wraps [modern-greek-inflexion-eee](https://github.com/EEE-project/modern-greek-inflexion-eee),
a fork of Picus Zeus's [modern-greek-inflexion](https://github.com/PicusZeus/modern-greek-inflexion).


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

Rule-based algorithm: accepts any valid Modern Greek lemma. No `list_lemmas()` —
the vocabulary is unbounded.

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


## Development

```bash
uv sync --dev
uv run pytest
```


## Status

v0.1.0
