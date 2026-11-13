#!/bin/bash
# Start sol_resume.sh at a given time (HHMM), when the Codex usage limit has lifted.
T=$1; shift
until [ "$(date +%H%M)" -ge "$T" ]; do sleep 30; done
exec "$(dirname "$0")/sol_resume.sh" "$@"
