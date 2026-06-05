#!/bin/bash
#===============================================================================
#
#  FILE: dev.sh
#
#  USAGE: ./dev.sh [start|stop|restart|status]
#
#  DESCRIPTION:
#    Manages the HackRitual API server in development mode.
#    Runs on 0.0.0.0:8888 with hot-reload. Applies migrations before
#    first start, logs to /tmp/hackritual_dev.log.
#
#    Features:
#      - Kills any existing server on port 8888 before starting
#      - Runs Alembic migrations automatically before start
#      - Hot-reload via uvicorn --reload
#      - Logs all output to /tmp/hackritual_dev.log
#      - Provides start/stop/restart/status commands
#      - Safe to run multiple times (idempotent)
#
#  OPTIONS:
#    start   - Start the dev server (kills existing if running)
#    stop    - Stop the dev server
#    restart - Restart the dev server
#    status  - Check if server is running and show recent logs
#    (none)  - Default: restart (stop + start)
#
#  REQUIREMENTS:
#    - uv (https://docs.astral.sh/uv/)
#    - Backend dependencies installed (uv sync --extra dev)
#    - Access to port 8888
#
#  ENVIRONMENT:
#    Reads from .env if present. Falls back to dev defaults for all
#    required vars (SMTP runs in console mode; codes print to log).
#
#  LOG FILE:
#    /tmp/hackritual_dev.log - Contains all server output and errors
#
#  EXAMPLES:
#    ./dev.sh start    # Start the server
#    ./dev.sh stop     # Stop the server
#    ./dev.sh restart  # Restart the server
#    ./dev.sh status   # Check server status + recent logs
#    ./dev.sh          # Default: restart
#
#  AUTHOR: HackRitual Team
#  VERSION: 1.0.0
#  CREATED: 2026-03-07
#
#===============================================================================

set -euo pipefail

#-------------------------------------------------------------------------------
# Configuration
#-------------------------------------------------------------------------------
readonly PORT=8888
readonly HOST="0.0.0.0"
readonly BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly BACKEND_DIR="${BASE_DIR}/backend"
readonly DATA_DIR="${BASE_DIR}/data"
readonly LOG_FILE="/tmp/hackritual_dev.log"
readonly PID_FILE="/tmp/hackritual_dev.pid"
readonly SCRIPT_NAME=$(basename "$0")
readonly UV="${BACKEND_DIR}/.venv/bin/python -m uvicorn"

#-------------------------------------------------------------------------------
# Dev defaults — used when a var is not set in the environment or .env
#-------------------------------------------------------------------------------
# SMTP_HOST=console means codes print to the log instead of sending email.
_apply_dev_defaults() {
    export APP_BASE_URL="${APP_BASE_URL:-http://localhost:${PORT}}"
    export LOG_LEVEL="${LOG_LEVEL:-INFO}"
    export DB_PATH="${DB_PATH:-${DATA_DIR}/app.db}"
    export UPLOAD_DIR="${UPLOAD_DIR:-${DATA_DIR}/uploads}"
    export JWT_SECRET="${JWT_SECRET:-dev-secret-not-for-production-$(hostname)}"
    export ADMIN_SEED_EMAILS="${ADMIN_SEED_EMAILS:-admin@dev.local}"
    export SMTP_HOST="${SMTP_HOST:-console}"
    export SMTP_PORT="${SMTP_PORT:-587}"
    export SMTP_USER="${SMTP_USER:-dev}"
    export SMTP_PASS="${SMTP_PASS:-dev}"
    export SMTP_FROM="${SMTP_FROM:-hackritual@dev.local}"
    export EVENT_ID="${EVENT_ID:-hackritual-dev}"
    export EVENT_TITLE="${EVENT_TITLE:-HackRitual Dev Event}"
    export EVENT_TYPE="${EVENT_TYPE:-hackathon}"
    export EVENT_START="${EVENT_START:-2026-01-01T09:00:00+00:00}"
    export EVENT_END="${EVENT_END:-2026-12-31T17:00:00+00:00}"
}

#-------------------------------------------------------------------------------
# Colors for output (disabled if not a terminal)
#-------------------------------------------------------------------------------
if [[ -t 1 ]]; then
    readonly RED='\033[0;31m'
    readonly GREEN='\033[0;32m'
    readonly YELLOW='\033[1;33m'
    readonly BLUE='\033[0;34m'
    readonly CYAN='\033[0;36m'
    readonly NC='\033[0m'
else
    readonly RED=''
    readonly GREEN=''
    readonly YELLOW=''
    readonly BLUE=''
    readonly CYAN=''
    readonly NC=''
fi

#-------------------------------------------------------------------------------
# Logging functions
#-------------------------------------------------------------------------------
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_detail() {
    echo -e "${CYAN}  →${NC} $*"
}

#-------------------------------------------------------------------------------
# Helper: find PID of whatever is holding port 8888
#-------------------------------------------------------------------------------
get_server_pid() {
    # Always prefer what is actually listening on the port (covers orphaned processes too)
    local pid=""
    pid=$(ss -tlnp 2>/dev/null | grep ":${PORT} " | grep -oP 'pid=\K[0-9]+' | head -1 || true)
    if [[ -z "$pid" ]]; then
        pid=$(fuser "${PORT}/tcp" 2>/dev/null | tr -d ' ' || true)
    fi
    # Fall back to PID file when the port scanner comes up empty
    if [[ -z "$pid" && -f "$PID_FILE" ]]; then
        pid=$(cat "$PID_FILE" 2>/dev/null || true)
        kill -0 "$pid" 2>/dev/null || pid=""
    fi
    echo "$pid"
}

is_server_running() {
    local pid
    pid=$(get_server_pid)
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

#-------------------------------------------------------------------------------
# Helper: stop the server gracefully, sweeping all related processes
#-------------------------------------------------------------------------------
kill_server() {
    local found=0

    # 1. Kill by pattern — catches the nohup wrapper, uv, uvicorn, and
    #    any watchfiles reloader children spawned by --reload.
    if pkill -TERM -f "hackritual serve" 2>/dev/null; then
        found=1
    fi

    # 2. Also kill anything still holding the port (e.g. old unified_server.py)
    local port_pid
    port_pid=$(ss -tlnp 2>/dev/null | grep ":${PORT} " | grep -oP 'pid=\K[0-9]+' | head -1 || true)
    if [[ -n "$port_pid" ]]; then
        log_info "Killing process on port ${PORT} (PID: ${port_pid})…"
        kill -TERM "$port_pid" 2>/dev/null || true
        found=1
    fi

    # 3. Wait for the port to actually be free (max 6 s), then force-kill stragglers
    local count=0
    while ss -tlnp 2>/dev/null | grep -q ":${PORT} " && [[ $count -lt 6 ]]; do
        sleep 1
        count=$((count + 1))
    done

    if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
        log_warning "Port ${PORT} still busy — force killing…"
        pkill -9 -f "hackritual serve" 2>/dev/null || true
        port_pid=$(ss -tlnp 2>/dev/null | grep ":${PORT} " | grep -oP 'pid=\K[0-9]+' | head -1 || true)
        [[ -n "$port_pid" ]] && kill -9 "$port_pid" 2>/dev/null || true
        sleep 1
    fi

    rm -f "$PID_FILE"

    if [[ $found -eq 1 ]]; then
        log_success "Server stopped"
        return 0
    else
        log_info "No server running on port ${PORT}"
        return 1
    fi
}

#-------------------------------------------------------------------------------
# Helper: run Alembic migrations
#-------------------------------------------------------------------------------
run_migrations() {
    log_info "Running migrations…"
    if cd "${BACKEND_DIR}" && uv run hackritual migrate >> "${LOG_FILE}" 2>&1; then
        log_success "Migrations up to date"
    else
        log_error "Migration failed — check ${LOG_FILE}"
        return 1
    fi
}

#-------------------------------------------------------------------------------
# start_server
#-------------------------------------------------------------------------------
start_server() {
    # Ensure backend exists
    if [[ ! -d "$BACKEND_DIR" ]]; then
        log_error "Backend directory not found: ${BACKEND_DIR}"
        exit 1
    fi

    # Load .env if present (values already in environment take precedence)
    if [[ -f "${BASE_DIR}/.env" ]]; then
        log_info "Loading .env"
        set -o allexport
        # shellcheck disable=SC1091
        source "${BASE_DIR}/.env"
        set +o allexport
    fi

    # Apply dev defaults for any var that is still unset
    _apply_dev_defaults

    # Create data directories
    mkdir -p "${DATA_DIR}/uploads"
    log_detail "Data dir: ${DATA_DIR}"

    # Kill any existing server on the port
    kill_server 2>/dev/null || true

    # Write log header
    {
        echo "========================================"
        echo "  HackRitual Dev Server"
        echo "  Started: $(date)"
        echo "  Host:    ${HOST}:${PORT}"
        echo "  DB:      ${DB_PATH}"
        echo "  SMTP:    ${SMTP_HOST} (console = print to log)"
        echo "========================================"
        echo ""
    } > "${LOG_FILE}"

    # Run migrations before starting the server
    run_migrations

    log_info "Starting server on ${HOST}:${PORT} (hot-reload enabled)…"
    log_detail "Scaffold UI will be at: http://localhost:${PORT}/scaffold/"
    log_detail "API docs:               http://localhost:${PORT}/api/docs"
    log_detail "Log file:               ${LOG_FILE}"

    # Launch uvicorn via hackritual CLI in background
    nohup bash -c "
        cd '${BACKEND_DIR}'
        exec uv run hackritual serve --host '${HOST}' --port '${PORT}' --reload
    " >> "${LOG_FILE}" 2>&1 &

    echo $! > "${PID_FILE}"

    # Wait for server to answer (up to 25 s — reload mode needs extra time)
    local retries=0
    echo -n "  Waiting for server"
    while [[ $retries -lt 25 ]]; do
        sleep 1
        echo -n "."
        retries=$((retries + 1))
        if curl -sf "http://localhost:${PORT}/api/health" > /dev/null 2>&1; then
            echo ""
            log_success "Server is up!  http://localhost:${PORT}"
            return 0
        fi
    done

    echo ""
    log_error "Server did not respond after 25 s — check ${LOG_FILE}"
    tail -20 "${LOG_FILE}" >&2
    return 1
}

#-------------------------------------------------------------------------------
# show_status
#-------------------------------------------------------------------------------
show_status() {
    echo ""
    echo "========================================"
    echo "  HackRitual Dev Server Status"
    echo "========================================"
    echo ""

    if is_server_running; then
        local pid
        pid=$(get_server_pid)
        echo -e "Status:   ${GREEN}RUNNING${NC}"
        echo    "PID:      ${pid}"
        echo    "Port:     ${PORT}"
        echo    "URL:      http://localhost:${PORT}"
        echo    "Scaffold: http://localhost:${PORT}/scaffold/"
        echo    "API docs: http://localhost:${PORT}/api/docs"
        echo    "Log:      ${LOG_FILE}"
        echo ""
        echo "Recent log:"
        echo "----------------------------------------"
        tail -15 "${LOG_FILE}" 2>/dev/null || echo "(no log entries)"
    else
        echo -e "Status: ${RED}STOPPED${NC}"
        echo    "Port:   ${PORT}"
        echo    "Log:    ${LOG_FILE}"
        if [[ -f "$LOG_FILE" ]]; then
            echo ""
            echo "Last log entries:"
            echo "----------------------------------------"
            tail -10 "${LOG_FILE}" 2>/dev/null
        fi
    fi

    echo ""
    echo "========================================"
}

#-------------------------------------------------------------------------------
# show_usage
#-------------------------------------------------------------------------------
show_usage() {
    cat << EOF
Usage: ${SCRIPT_NAME} [start|stop|restart|status]

Manage the HackRitual API server in development mode.

Commands:
  start    Start the dev server (kills existing if running)
  stop     Stop the dev server
  restart  Restart the dev server (default)
  status   Show server status and recent logs

Examples:
  ${SCRIPT_NAME} start    # Start on ${HOST}:${PORT}
  ${SCRIPT_NAME} stop     # Stop the server
  ${SCRIPT_NAME} restart  # Restart (default)
  ${SCRIPT_NAME} status   # Status + recent logs

Configuration:
  Host:    ${HOST}
  Port:    ${PORT}
  Log:     ${LOG_FILE}
  PID:     ${PID_FILE}

Environment variables are read from .env (if present), then fall back
to built-in dev defaults (SMTP_HOST=console prints codes to the log).

EOF
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------
main() {
    local command="${1:-restart}"

    case "$command" in
        start)
            start_server
            ;;
        stop)
            kill_server || exit 0
            ;;
        restart)
            log_info "Restarting server…"
            kill_server 2>/dev/null || true
            start_server
            ;;
        status)
            show_status
            ;;
        -h|--help|help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown command: ${command}"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
