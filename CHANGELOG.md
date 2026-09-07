# Changelog

## 1.1.0 - 2026-09-07
- `get_tags("pronoun")` now returns 48 rows (was 24): the original 24 keep
  their exact existing tags with `Clitic` absent, plus 24 more add
  `Clitic="Yes"` for the weak/clitic forms. Surfaces the strong/weak
  distinction that `inflect()` already accepted via a `Clitic="Yes"`
  feature but `get_tags()`/`get_slot_templates()` never enumerated —
  a caller had to already know to hand-build that feature out of band.
  `article`/`numeral` keep their existing 24-row shape unchanged.
