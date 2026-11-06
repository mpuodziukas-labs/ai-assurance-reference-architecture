#!/usr/bin/env bash
# Verify the whole repository. Prints GREEN and exits 0 only if every step passes.
#   scripts/verify.sh              run all checks
#   scripts/verify.sh --selftest   plant 4 defects and 1 control, expect 5/5
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/.verify-out"
mkdir -p "$OUT"

# Fresh clean copy of the checked files into $OUT/st<n>; prints the directory.
fresh() {
  local d="$OUT/st$1"
  mkdir -p "$d/adr" "$d/capacity" "$d/orchestrator"
  cp "$ROOT/ARCHITECTURE.md" "$d/"
  cp "$ROOT"/adr/*.md "$d/adr/"
  cp "$ROOT"/capacity/*.py "$ROOT"/capacity/*.yaml "$d/capacity/"
  cp "$ROOT"/orchestrator/*.py "$d/orchestrator/"
  echo "$d"
}

selftest() {
  local pass=0 d f
  local adrs=("$ROOT"/adr/*.md)
  f="${adrs[0]}"

  d="$(fresh 1)"
  sed 's/^## Trade-offs/## Tradeoffs/' "$f" >"$d/adr/$(basename "$f")"
  if ! cmp -s "$f" "$d/adr/$(basename "$f")" \
    && ! python3 "$ROOT/scripts/arch-lint.py" --root "$d" >/dev/null 2>&1; then
    echo "ok 1: ADR missing a section is rejected"; pass=$((pass + 1))
  else echo "MISS 1: ADR missing a section was accepted"; fi

  d="$(fresh 2)"
  # shellcheck disable=SC2016
  sed '/^|/s/`taint-flow-guard`/`bogus-repo`/' "$ROOT/ARCHITECTURE.md" >"$d/ARCHITECTURE.md"
  if ! cmp -s "$ROOT/ARCHITECTURE.md" "$d/ARCHITECTURE.md" \
    && ! python3 "$ROOT/scripts/arch-lint.py" --root "$d" >/dev/null 2>&1; then
    echo "ok 2: unknown repo in the table is rejected"; pass=$((pass + 1))
  else echo "MISS 2: unknown repo in the table was accepted"; fi

  d="$(fresh 3)"
  sed 's/if used > lane.budget:/if False:/' "$ROOT/orchestrator/director.py" >"$d/orchestrator/director.py"
  if ! cmp -s "$ROOT/orchestrator/director.py" "$d/orchestrator/director.py" \
    && ! python3 -m pytest -q -p no:cacheprovider "$d/orchestrator" >/dev/null 2>&1; then
    echo "ok 3: budget breach accepted is caught by the tests"; pass=$((pass + 1))
  else echo "MISS 3: budget breach accepted went unnoticed"; fi

  d="$(fresh 4)"
  sed 's/if not 0\.0 <= rate <= 1\.0:/if False:/' "$ROOT/capacity/cost_model.py" >"$d/capacity/cost_model.py"
  if ! cmp -s "$ROOT/capacity/cost_model.py" "$d/capacity/cost_model.py" \
    && ! python3 -m pytest -q -p no:cacheprovider "$d/capacity" >/dev/null 2>&1; then
    echo "ok 4: negative cache rate accepted is caught by the tests"; pass=$((pass + 1))
  else echo "MISS 4: negative cache rate accepted went unnoticed"; fi

  d="$(fresh 5)"
  if python3 "$ROOT/scripts/arch-lint.py" --root "$d" >/dev/null 2>&1 \
    && python3 -m pytest -q -p no:cacheprovider "$d/orchestrator" "$d/capacity" >/dev/null 2>&1; then
    echo "ok 5: control (clean copy) passes"; pass=$((pass + 1))
  else echo "MISS 5: control (clean copy) failed"; fi

  echo "selftest $pass/5"
  [ "$pass" -eq 5 ]
}

if [ "${1:-}" = "--selftest" ]; then
  selftest
  exit $?
fi

echo "== pytest"
python3 -m pytest -q -p no:cacheprovider "$ROOT/capacity" "$ROOT/orchestrator"

echo "== arch-lint"
python3 "$ROOT/scripts/arch-lint.py" --root "$ROOT"

echo "== cost model on the example, twice, byte-identical"
python3 "$ROOT/capacity/cost_model.py" "$ROOT/capacity/example.yaml" >"$OUT/cost-a.json"
python3 "$ROOT/capacity/cost_model.py" "$ROOT/capacity/example.yaml" >"$OUT/cost-b.json"
cmp "$OUT/cost-a.json" "$OUT/cost-b.json"
echo "identical"

echo "== orchestrator demo"
python3 "$ROOT/orchestrator/demo.py"

echo GREEN
