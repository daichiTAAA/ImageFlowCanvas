#!/usr/bin/env bash
set -euo pipefail

APP_ID="com.imageflow.kmp.app"
MAIN_ACTIVITY=".MainActivity"

here() { cd "$(dirname "$0")"/..; }

ensure_adb() {
  if ! command -v adb >/dev/null 2>&1; then
    echo "[ERROR] adb が見つかりません。Android SDK Platform-Tools をインストールしてください。" >&2
    exit 1
  fi
}

pick_gradle() {
  if [ -x ./gradlew ]; then
    echo ./gradlew
  elif command -v gradle >/dev/null 2>&1; then
    echo gradle
  else
    echo "[ERROR] Gradle が見つかりません。Android Studio で 'gradle wrapper' を実行するか、Gradle を導入してください。" >&2
    exit 1
  fi
}

ensure_device() {
  if ! adb get-state >/dev/null 2>&1; then
    echo "[WARN] 接続済みデバイス/エミュレーターが見つかりません。" >&2
    echo "       Android Studio の Device Manager で AVD を起動してから再実行してください。" >&2
    exit 1
  fi
}

build_install_start() {
  local GRADLE_BIN
  GRADLE_BIN=$(pick_gradle)

  echo "[INFO] Building :shared and :androidApp (debug)…"
  "$GRADLE_BIN" :shared:build
  "$GRADLE_BIN" :androidApp:installDebug

  echo "[INFO] Launching app on device/emulator…"
  adb shell am start -n "${APP_ID}/${MAIN_ACTIVITY}"
}

main() {
  here
  ensure_adb
  ensure_device
  build_install_start
  echo "[DONE] 起動コマンドを実行しました。画面が表示されない場合は Logcat を確認してください。"
}

main "$@"

