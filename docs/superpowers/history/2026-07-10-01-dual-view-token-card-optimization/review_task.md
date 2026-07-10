# Dual View Token Card Optimization Review

Date: 2026-07-10
Reviewer: main agent (GPT-5.6)

## Scope and review order

Reviewed the commits listed in `docs/superpowers/finish_task.md` in commit-time
order, against the design and implementation plan:

1. `516eac3` `feat: add dual-view segment metadata contract`
2. `a533f5f` `fix: switch dual view to raw-element cards`
3. `54617ae` `fix: render math cards with MathML and remove segment aria-label`
4. `6f9f64f` `fix: remove Translation segment from localization artifacts`

The review covered the conversion metadata contract, token-level alignment
ranges, source-kind handling, MathML rendering/trust boundary, HTML
accessibility structure, GUI cache lifecycle, and localization artifacts.

## Review cycle 1

Found one implementation/spec mismatch:

- `build_dual_view_model()` accepted an arbitrary `DualViewSegment.source_kind`
  and silently rendered it as text. The design requires model-build validation
  accepting only `"text"` and `"math"`.

The required correction was delegated to a sub-agent (GPT-5.4). It added
source-kind validation before result processing and the regression test
`test_unknown_source_kind_raises_value_error`.

Also found the localization binary catalog was stale: the `.mo` file still
contained `Translation segment`, despite the `.pot` removal and obsolete `.po`
entry. Regenerated `client/locales/zh_TW/LC_MESSAGES/dotexpress.mo` with
`msgfmt` after a successful `msgfmt --check`.

## Review cycle 2

Re-reviewed the correction and final diff. No remaining findings in the scoped
commits.

Confirmed behavior:

- Each `TranslationResult.raw` element produces exactly one card, including
  atomic multi-character tokens and raw elements containing embedded whitespace.
- Only an exact single space is a space card, and only an exact newline becomes
  a line-break node.
- Text and math source kinds are retained in the dual-view cache; math source
  is generated through `latex_to_mathml()` and rendered as trusted MathML DOM.
- Text and braille output remain escaped, sections remain present without an
  `aria-label` or region role, and GUI document cache updates remain scoped to
  successful manual conversion.
- `Translation segment` is absent from active source/catalog entries and from
  the compiled `.mo`; its obsolete `.po` entry is valid gettext behavior.

## Verification

Passed:

```text
cd client && python3 -m unittest tests.test_conversion_service tests.test_dual_view_model tests.test_dual_view_html tests.test_gui_document_flows -v
# 77 tests passed

cd client && python3 -m unittest tests.test_dual_view_frame -v
# 6 tests passed when isolated

msgfmt --check client/locales/zh_TW/LC_MESSAGES/dotexpress.po -o /tmp/dotexpress.check.mo
```

The combined focused command reports one known pre-existing test isolation
failure in `test_initial_geometry_matches_parent`:
`TypeError: 'function' object is not subscriptable`. This matches
`finish_task.md`, predates this change, and the same test passes in isolation;
it is not a finding against the reviewed commits.

`git diff --check 516eac3^..HEAD` passed. Unrelated pre-existing worktree
changes, including trailing whitespace in `docs/refactor/refactor.md`, were not
modified or included in this review.
