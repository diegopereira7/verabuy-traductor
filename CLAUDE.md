# Claude guidance for this repository

You are working on **VeraBuy Traductor**, a hybrid repository with a Python processing engine and a PHP web layer.

## Project purpose

The repository translates flower supplier invoice PDF lines into internal VeraBuy article matches.
The goal is to detect the supplier, parse invoice lines, normalize product attributes and match them against the VeraBuy article catalog.

## Core architecture

- `verabuy_trainer.py`
  - Main domain engine.
  - Contains provider registry, PDF provider detection, invoice dataclasses, article loader, synonym store, matcher, history, rescue logic and supplier parsers.
- `procesar_pdf.py`
  - Non-interactive wrapper used by the web layer.
  - Input: PDF path.
  - Output: JSON to stdout.
- `exportar_excel.py`
  - Exports synonyms and history to Excel.
- `web/config.php`
  - Local Windows configuration.
- `web/api.php`
  - PHP bridge between browser and Python.
- `web/index.php`
  - Main UI.
- `web/assets/app.js`
  - Frontend interaction logic.
- `web/assets/style.css`
  - UI styling.

## Environment assumptions

- Local Windows setup.
- PHP served in localhost / WAMP style environment.
- Python executable configured explicitly in `web/config.php`.
- Do not assume Docker or Linux unless explicitly requested.

## Data sources

- `articulos (3).sql`
  - Large VeraBuy article dump used as the catalog for matching.
- `sinonimos_universal.json`
  - Persistent synonym dictionary for provider-specific invoice names.
- `historial_universal.json`
  - Persistent processing history.

## Important invariants

Do not break these unless explicitly requested:

1. `procesar_pdf.py` must keep returning valid JSON.
2. The JSON response shape expected by `web/assets/app.js` must remain compatible.
3. `web/api.php` expects to execute the Python processor and echo its JSON response.
4. Synonyms are stored with a composite key based on `provider_id` and `line.match_key()`.
5. Matching must remain incremental and conservative.
6. Parser changes must not silently regress already supported supplier formats.

## Domain conventions

Common normalized fields:
- `provider_id`
- `provider_name`
- `invoice_number`
- `date`
- `awb`
- `hawb`
- `species`
- `variety`
- `grade`
- `origin`
- `size`
- `stems_per_bunch`
- `bunches`
- `stems`
- `price_per_stem`
- `line_total`
- `articulo_id`
- `articulo_name`
- `match_status`
- `match_method`

Observed normalized species values:
- `ROSES`
- `CARNATIONS`
- `HYDRANGEAS`
- `ALSTROEMERIA`
- `GYPSOPHILA`
- `CHRYSANTHEMUM`
- `OTHER`

Observed grade values:
- `FANCY`
- `SELECT`
- `PREMIUM`
- `STANDARD`

## Matching logic expectations

Observed matching priority includes:
- existing synonym
- provider brand-aware match
- exact expected-name match
- additional automatic matching from the engine
- fuzzy match when similarity is high enough
- fallback to `sin_match`

Be conservative with fuzzy logic. Avoid increasing false positives.

## Web behavior expectations

The web layer supports at least these actions in `api.php`:
- `process`
- `synonyms`
- `history`
- `save_synonym`

If you touch API behavior, review both backend and frontend compatibility.

## How to work

When implementing a change:
1. Identify the exact files affected.
2. Minimize scope.
3. Preserve compatibility.
4. Explain assumptions briefly.
5. Prefer targeted patches over large rewrites.

## Preferred output style

When asked for code changes, prefer one of these formats depending on the request:
- exact patch
- full function replacement
- only modified blocks
- short explanation plus code

## Avoid

- broad refactors without a concrete need
- changing output formats casually
- introducing heavy dependencies
- mixing unrelated cleanups into functional changes
