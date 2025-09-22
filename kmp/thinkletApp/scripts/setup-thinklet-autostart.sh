#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
CONFIG_PATH="${APP_ROOT}/provisioning/key_config_autostart.json"
DEST_DIR="/sdcard/Android/data/ai.fd.thinklet.app.launcher/files"
DEST_PATH="${DEST_DIR}/key_config.json"

if ! command -v adb >/dev/null 2>&1; then
  echo "adb command not found; install Android platform-tools." >&2
  exit 1
fi

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Config file not found at ${CONFIG_PATH}" >&2
  exit 1
fi

adb wait-for-device
adb shell mkdir -p "${DEST_DIR}"
adb push "${CONFIG_PATH}" "${DEST_PATH}"
adb shell input keyevent KEYCODE_APP_SWITCH
adb shell input keyevent HOME

if [[ "${1:-}" == "--trigger-start" ]]; then
  adb shell input keyevent KEYCODE_CAMERA
fi
