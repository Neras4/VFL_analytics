# Baseline v0.1 — 2026-10-12

Unmodified archive imported as commit d192276, then branch
`feature/analytics-v0.2.1` created. Separate repository; VFL Assistant untouched.

Python 3.12 (bundled runtime), isolated `.venv` with NumPy 2.5.4,
SciPy 1.18.1, pytest 9.1.1. Dependencies installed using bundled pip's
`--python .venv/Scripts/python.exe` option; initial ensurepip failed and
the environment has no own pip module. No system package installation.

Command: `.venv/Scripts/python.exe -m pytest -q`.
Result: **12 passed, 0 failed**, 17.33 seconds. One infrastructure warning:
pytest could not create its cache under Windows sandbox. Subsequent runs use
`-p no:cacheprovider`; this does not disable or change tests.

Final isolation verification: `include-system-site-packages=false`, all three
required packages resolve inside `.venv/Lib/site-packages`. The original
d192276 tree was independently extracted to `work/baseline-v0.1` and rerun
using this interpreter: **12 passed, 0 failed**, 1.28 seconds, no cache warning.
The initial environment temporarily allowed bundled site packages; the final
baseline reproduction and v0.2.1 validation use full package isolation.

Passing baseline does not establish correctness: old assertions explicitly
expect unrounded youth growth and overstated minute targets. Audit mapping:
AUD-01 rules.py/season.py; AUD-02 and AUD-03 season.py; AUD-04 rules.py and
lineup.py; AUD-05 models.py/adapters.py; AUD-14 rules.py/models.py.

Plan: introduce validated mathematical result types; correct usefulness and
integer minute boundaries; preserve absent study percentages; propagate
chemistry intervals and explicit empty/League endpoints; validate captain
age; update consumers and justified regression expectations; add selected
research vectors and independent boundary tests; document deferred audits.
