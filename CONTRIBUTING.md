# Development workflow

To keep the repository tidy, all development happens on **one** long-lived branch:

- **`vibe/dev-5adb24`** — the only development branch. Every change (features, fixes,
  docs, tests) is committed there; no per-task branches.
- Pull requests are opened from `vibe/dev-5adb24` against `main` and stay **draft**
  until they have been tested on the maintainer's system (Home Assistant Integration
  Tester) and are approved there. Only then are they merged.
- Old per-task branches are deleted as soon as their content is merged (or moved
  onto the dev branch), so `main` + `vibe/dev-5adb24` are the only branches that
  should exist.

## Local checks before pushing

```bash
python scripts/validate_integration.py
python -m pytest tests/test_gamification.py tests/test_goat.py tests/test_frontend_assets.py -q   # no HA needed
python -m pytest tests/test_imports.py tests/test_setup.py tests/test_todo.py tests/test_manager.py -q  # needs `pip install homeassistant`
cp custom_components/gamified_gtd/www/gamified-gtd-cards.js /tmp/cards.mjs && node --check /tmp/cards.mjs
```

CI (`.github/workflows/ci.yml`) runs the same checks on every push and PR:
validate, unit tests, import smoke (with HA installed) and `node --check` for the cards.

## Card JS

`custom_components/gamified_gtd/www/gamified-gtd-cards.js` is the source (edit this).
`www/gamified-gtd-lit.js` is a checked-in, vendored lit bundle — only rebuild it with
`scripts/build_cards_lit.sh` when the lit version should change. After card changes:
restart HA and hard-refresh the browser (Ctrl/Cmd+Shift+R) so
`/gamified_gtd_static/gamified-gtd-cards.js?v=<version>` is re-fetched.
