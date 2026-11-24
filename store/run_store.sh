#!/usr/bin/env bash
# =============================================================================
# run_store.sh — Omni-Mind filesystem store runner (Phase 1 prototype)
#
# Walks the store graph from a start id with a fuel budget, following +1
# edges only (exactly like `walk` in mind/graph.omni), then activates the
# final node and prints its value.
#
#   Usage: ./run_store.sh <start> <fuel>
#     start : node id to start from (integer)
#     fuel  : max steps to walk (integer, >= 0)
#
#   Output: the activated value of the final node (an integer).
#     Unknown node (no mem file) -> 0.
#
#   Examples (v0.1 golden_walk cases, reproduced through the store):
#     ./run_store.sh 0 10  -> 99   (walk 0 -> 1 via +1 edge, activate 1)
#     ./run_store.sh 1 10  -> 99   (no +1 edge from 1, stay, activate 1)
#     ./run_store.sh 0 0   -> 42   (fuel 0, stay at 0, activate 0)
#     ./run_store.sh 0 1   -> 99   (one step 0 -> 1, activate 1)
#     ./run_store.sh 2 10  -> 0    (unknown node 2, no mem file -> 0)
#     ./run_store.sh 3 0   -> 7    (persistence proof: mem_3, direct)
#
# How it works:
#   1. Walk in the shell (not in Omni): read +1 edges from links.txt,
#      follow them until fuel runs out or no +1 edge exists. The walk
#      loop lives in the shell, so the 64-frame call-depth cap is
#      irrelevant.
#   2. Activate the final node once: run its mem_<id>.omni through
#      `omnic run` and unpack the value as (packed / 10) - 100.
#      The packed format is (value + 100) * 10 + (confidence + 1),
#      the same as mem_activate in mind/memory.omni.
#   3. A missing mem file means an unknown node -> 0 (value 0, conf 0).
#
# Constraints (see the Phase 1 plan):
#   - Uses the default `run` path only, NOT --rust. Each mem file is
#     single-function, and `run --rust` fails a memory-budget check on
#     any single-function file (Grok's third bug). The --rust
#     differential cross-check is unavailable for the store until that
#     bug is fixed.
#   - Calls main with at most 1 arg (ctx), so the `run` arg bug (args
#     past the third arrive as 0) never bites.
#   - No kv_put / db_get, no pack5. The store is files + a script.
#
# Configuration (environment variables):
#   OMNIC     : path to the omnic binary. Default: `omnic` on PATH,
#               else $HOME/workspace/omnic-fix.
#   OMNI_DIR  : Omni checkout containing a pure/ tree. `omnic run`
#               must be invoked from a directory containing pure/.
#               Default: $HOME/workspace/omni-fix-m3builtins.
# =============================================================================
set -euo pipefail

STORE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MEM_DIR="$STORE_DIR/memories"
LINKS="$STORE_DIR/links.txt"

# --- locate omnic ---------------------------------------------------------
if [ -n "${OMNIC:-}" ]; then
  OMNIC_BIN="$OMNIC"
elif command -v omnic >/dev/null 2>&1; then
  OMNIC_BIN="omnic"
elif [ -x "$HOME/workspace/omnic-fix" ]; then
  OMNIC_BIN="$HOME/workspace/omnic-fix"
else
  echo "run_store.sh: cannot find omnic (set \$OMNIC)" >&2
  exit 1
fi

# --- locate the Omni checkout (needs pure/) --------------------------------
if [ -n "${OMNI_DIR:-}" ]; then
  OMNI_DIR_ABS="$OMNI_DIR"
elif [ -d "$HOME/workspace/omni-fix-m3builtins/pure" ]; then
  OMNI_DIR_ABS="$HOME/workspace/omni-fix-m3builtins"
else
  echo "run_store.sh: cannot find an Omni checkout with pure/ (set \$OMNI_DIR)" >&2
  exit 1
fi

START="${1:?usage: run_store.sh <start> <fuel>}"
FUEL="${2:?usage: run_store.sh <start> <fuel>}"

# --- helpers ---------------------------------------------------------------
# next_plus1 <cur> : print the target of the +1 edge from <cur>, or nothing.
# Deterministic: the first matching line in links.txt wins.
next_plus1() {
  local cur="$1"
  awk -v c="$cur" '$1 == c && ($3 == "+1" || $3 == 1) { print $2; exit }' "$LINKS"
}

# activate <id> : run mem_<id>.omni, print its unpacked value.
# Missing mem file -> unknown node -> 0.
activate() {
  local id="$1"
  local f="$MEM_DIR/mem_${id}.omni"
  if [ ! -f "$f" ]; then
    echo 0
    return
  fi
  local out
  out="$(cd "$OMNI_DIR_ABS" && "$OMNIC_BIN" run "$f" 0)"
  # out looks like "Int(1422)". Extract the number.
  local packed
  packed="$(printf '%s' "$out" | sed -n 's/.*Int(\(-*[0-9]*\)).*/\1/p')"
  if [ -z "$packed" ]; then
    echo "run_store.sh: unexpected omnic output for mem_${id}: $out" >&2
    exit 1
  fi
  # Unpack: value = (packed / 10) - 100. (packed is positive here,
  # so bash integer division truncating toward zero is exact.)
  echo $(( packed / 10 - 100 ))
}

# --- walk (in the shell; +1 edges only) -------------------------------------
cur="$START"
f="$FUEL"
while [ "$f" -gt 0 ]; do
  nxt="$(next_plus1 "$cur")"
  [ -n "$nxt" ] || break
  cur="$nxt"
  f=$(( f - 1 ))
done

# --- activate the final node -------------------------------------------------
activate "$cur"
