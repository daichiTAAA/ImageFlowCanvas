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

ensure_wrapper() {
  # Ensure gradlew is executable if present
  if [ -f ./gradlew ] && [ ! -x ./gradlew ]; then chmod +x ./gradlew || true; fi
  # If wrapper script exists but wrapper JAR is missing, try to bootstrap via local gradle
  if [ -f ./gradlew ] && [ ! -f ./gradle/wrapper/gradle-wrapper.jar ]; then
    if command -v gradle >/dev/null 2>&1; then
      echo "[INFO] gradle-wrapper.jar が見つかりません。wrapper を生成します（Gradle 8.14）。"
      gradle wrapper --gradle-version 8.14
    else
      echo "[ERROR] gradle-wrapper.jar が見つかりません。" >&2
      echo "       次のいずれかを実行してください:" >&2
      echo "       1) Android Studio の Gradle タスク 'wrapper' を実行" >&2
      echo "       2) 'brew install gradle' 後に 'gradle wrapper --gradle-version 8.14' を実行" >&2
      exit 1
    fi
  fi
}

pick_gradle() {
  if [ -f ./gradlew ]; then
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

ensure_jdk17() {
  # Ensure Gradle runs with JDK 17+
  get_version() {
    "$1" -version 2>&1 | awk -F '"' '/version/ {print $2}'
  }
  is_17_or_newer() {
    ver="$(get_version "$1")" || return 1
    major="${ver%%.*}"
    if [ "$major" = "1" ]; then
      # e.g. 1.8
      minor="$(echo "$ver" | cut -d. -f2)"
      [ "$minor" -ge 17 ]
    else
      [ "$major" -ge 17 ]
    fi
  }

  # 1) If JAVA_HOME points to 17+, keep it
  if [ -n "${JAVA_HOME:-}" ] && [ -x "$JAVA_HOME/bin/java" ] && is_17_or_newer "$JAVA_HOME/bin/java"; then
    echo "[INFO] Using JDK $(get_version "$JAVA_HOME/bin/java") at $JAVA_HOME"
    return 0
  fi

  # 2) Try current java in PATH
  if command -v java >/dev/null 2>&1 && is_17_or_newer "$(command -v java)"; then
    export JAVA_HOME="$(dirname "$(dirname "$(command -v java)")")"
    echo "[INFO] Using JDK $(get_version "$JAVA_HOME/bin/java") at $JAVA_HOME"
    return 0
  fi

  # 3) Try macOS helper for a specific 17 runtime first
  if command -v /usr/libexec/java_home >/dev/null 2>&1; then
    J17="$(/usr/libexec/java_home -v 17 2>/dev/null || true)"
    if [ -n "$J17" ] && [ -x "$J17/bin/java" ] && is_17_or_newer "$J17/bin/java"; then
      export JAVA_HOME="$J17"
      echo "[INFO] Using JDK $(get_version "$JAVA_HOME/bin/java") at $JAVA_HOME"
      return 0
    fi
  fi

  # 4) Try Android Studio embedded JDK (macOS)
  STUDIO_JDK="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
  if [ -x "$STUDIO_JDK/bin/java" ] && is_17_or_newer "$STUDIO_JDK/bin/java"; then
    export JAVA_HOME="$STUDIO_JDK"
    echo "[INFO] Using Android Studio embedded JDK $(get_version "$JAVA_HOME/bin/java") at $JAVA_HOME"
    return 0
  fi

  echo "[ERROR] JDK 17 が見つかりません。Gradle は Java 17 以上が必要です。" >&2
  echo "       対応例: Android Studio の埋め込み JDK を使用 (Gradle 設定)" >&2
  echo "             または macOS: 'brew install temurin17' 後に 'export JAVA_HOME=\"$(/usr/libexec/java_home -v 17)\"'" >&2
  exit 1
}

build_install_start() {
  local GRADLE_BIN
  GRADLE_BIN=$(pick_gradle)

  echo "[INFO] Building :shared and :androidApp (debug)…"
  # Ensure a fresh daemon picks up the new JAVA_HOME
  JAVA_HOME="${JAVA_HOME:-}" "$GRADLE_BIN" --stop >/dev/null 2>&1 || true
  JAVA_HOME="${JAVA_HOME:-}" "$GRADLE_BIN" --no-daemon :shared:clean :androidApp:clean
  JAVA_HOME="${JAVA_HOME:-}" "$GRADLE_BIN" --no-daemon :shared:build
  JAVA_HOME="${JAVA_HOME:-}" "$GRADLE_BIN" --no-daemon :androidApp:installDebug

  echo "[INFO] Launching app on device/emulator…"
  adb shell am start -n "${APP_ID}/${MAIN_ACTIVITY}"
}

main() {
  here
  ensure_adb
  ensure_wrapper
  ensure_jdk17
  ensure_device
  build_install_start
  echo "[DONE] 起動コマンドを実行しました。画面が表示されない場合は Logcat を確認してください。"
}

main "$@"
