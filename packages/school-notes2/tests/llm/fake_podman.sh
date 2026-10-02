#!/bin/bash
# Fake podman for launcher tests: records argv, simulates the harness by $FAKE_MODE.
printf '%s\n' "$*" >> "$FAKE_LOG"
case "$1" in
    rm) exit 0 ;;
    stop) [ -f "$FAKE_PIDFILE" ] && kill "$(cat "$FAKE_PIDFILE")" 2>/dev/null; exit 0 ;;
    run) ;;
    *) exit 0 ;;
esac
for a in "$@"; do printf '%s\n' "$a"; done > "$FAKE_ARGV"
cat > "$FAKE_STDIN"
case "$FAKE_MODE" in
    ok) touch "$FAKE_WORK/new.md"; echo '{"status": "done"}' > "$FAKE_OUT"; exit 0 ;;
    nothing) exit 3 ;;
    changed_fail) touch "$FAKE_WORK/new.md"; exit 2 ;;
    zero_noout) exit 0 ;;
    bad_json) echo '{' > "$FAKE_OUT"; exit 0 ;;
    sleep) echo $$ > "$FAKE_PIDFILE"; sleep 30 & wait; exit 143 ;;
    stdout) echo 'thinking {not json}'; echo 'done: {"verdict": "ok", "findings": []} bye'; exit 0 ;;
    login_in) exit 0 ;;
    login_out) exit 1 ;;
    *) exit "$FAKE_MODE" ;;
esac
