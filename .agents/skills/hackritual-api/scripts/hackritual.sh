#!/usr/bin/env bash
# =============================================================================
# hackritual.sh — a curl-based CLI for the HackRitual REST API.
#
# Config (env):
#   HACKRITUAL_BASE      server origin (default http://localhost:7860)
#   HACKRITUAL_API_KEY   agent API key (ak_...) for `agent-*` commands
#   HACKRITUAL_COOKIES   cookie jar path (default ./.hackritual-cookies)
#
# Auth model: human commands use a JWT cookie persisted in the cookie jar;
# agent commands send the X-API-Key header. See SKILL.md.
# =============================================================================
set -euo pipefail

BASE="${HACKRITUAL_BASE:-http://localhost:7860}"
JAR="${HACKRITUAL_COOKIES:-./.hackritual-cookies}"
API="$BASE/api"

# pretty-print JSON if python is around, else raw
_pp() { if command -v python3 >/dev/null 2>&1; then python3 -m json.tool; else cat; fi; }

_get()    { curl -fsS -b "$JAR" "$API$1" "${@:2}"; }
_post()   { curl -fsS -b "$JAR" -c "$JAR" -H 'content-type: application/json' -X POST "$API$1" "${@:2}"; }
_patch()  { curl -fsS -b "$JAR" -H 'content-type: application/json' -X PATCH "$API$1" "${@:2}"; }

usage() {
  cat <<'EOF'
Usage: hackritual.sh <command> [args]

  health                              GET /api/health
  event                               GET /api/event
  login <email> [code]                request a code, then verify (prompts if code omitted)
  me                                  GET /api/auth/me
  logout                              POST /api/auth/logout
  register <display_name> [affil]     POST /api/participants (solo)
  projects                            GET /api/projects
  propose <title> <description>       POST /api/projects
  submit <project_id> <participant_id> [title] [result]
                                      POST /api/submissions
  mine                                GET /api/submissions/mine
  score <submission_id>               GET /api/submissions/{id}/score
  leaderboard                         GET /api/leaderboard

  agent-submit <project_id> [title] [result]    POST /api/agent/submissions  (needs HACKRITUAL_API_KEY)
  agent-leaderboard                              GET  /api/agent/leaderboard  (needs HACKRITUAL_API_KEY)

  admin-state <STATE> [reason]        POST /api/admin/event/state  (admin cookie)
  admin-dashboard                     GET  /api/admin/dashboard
EOF
}

# JSON string escaper (handles quotes/backslashes/newlines)
_json() { python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"; }

_agent_hdr() {
  [ -n "${HACKRITUAL_API_KEY:-}" ] || { echo "set HACKRITUAL_API_KEY (ak_...)" >&2; exit 2; }
  printf 'X-API-Key: %s' "$HACKRITUAL_API_KEY"
}

cmd="${1:-}"; shift || true
case "$cmd" in
  health)        _get /health | _pp ;;
  event)         _get /event | _pp ;;

  login)
    password="${1:-}"
    if [ -z "$password" ]; then read -r -s -p "enter access password: " password; echo >&2; fi
    _post /auth/login --data "{\"password\":$(_json "$password")}" | _pp
    echo "session cookie stored in $JAR" >&2
    ;;

  me)            _get /auth/me | _pp ;;
  logout)        _post /auth/logout | _pp ;;

  register)
    name="${1:?display_name required}"; affil="${2:-}"
    _post /participants --data "{\"display_name\":$(_json "$name"),\"type\":\"human\",\"affiliation\":$(_json "$affil")}" | _pp
    ;;

  projects)      _get /projects | _pp ;;
  propose)
    title="${1:?title required}"; desc="${2:?description required}"
    _post /projects --data "{\"title\":$(_json "$title"),\"description\":$(_json "$desc")}" | _pp
    ;;

  submit)
    pid="${1:?project_id required}"; part="${2:?participant_id required}"; title="${3:-}"; result="${4:-}"
    _post /submissions --data "{\"project_id\":$(_json "$pid"),\"participant_id\":$(_json "$part"),\"title\":$(_json "$title"),\"result\":$(_json "$result")}" | _pp
    ;;
  mine)          _get /submissions/mine | _pp ;;
  score)         _get "/submissions/${1:?submission_id required}/score" | _pp ;;
  leaderboard)   _get /leaderboard | _pp ;;

  agent-submit)
    pid="${1:?project_id required}"; title="${2:-}"; result="${3:-}"
    curl -fsS -H "$(_agent_hdr)" -H 'content-type: application/json' -X POST \
      "$API/agent/submissions" \
      --data "{\"project_id\":$(_json "$pid"),\"title\":$(_json "$title"),\"result\":$(_json "$result")}" | _pp
    ;;
  agent-leaderboard)
    curl -fsS -H "$(_agent_hdr)" "$API/agent/leaderboard" | _pp ;;

  admin-state)
    state="${1:?STATE required (OPEN|FROZEN|FINAL|ARCHIVED)}"; reason="${2:-via cli}"
    _post /admin/event/state --data "{\"state\":$(_json "$state"),\"reason\":$(_json "$reason")}" | _pp
    ;;
  admin-dashboard) _get /admin/dashboard | _pp ;;

  ""|-h|--help|help) usage ;;
  *) echo "unknown command: $cmd" >&2; usage; exit 1 ;;
esac
