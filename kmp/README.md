# Kotlin Multiplatform (KMP) モジュール — ImageFlowCanvas クライアント共通

ImageFlowCanvas のエッジ/端末クライアント向け共通ライブラリ（Kotlin Multiplatform）です。カメラ・センサー抽象化、軽量DB、ネットワークIF（gRPC/REST/WebSocket）と簡易UIを提供し、Android/iOS/Desktop で再利用します。

## 役割と特徴
- 共通ロジック: `commonMain` にドメイン/ネットワーク/DB 抽象を集約
- プラットフォーム実装: `androidMain`/`iosMain`/`desktopMain` でカメラ、ファイル、通知、センサーを実装
- データ永続化: SQLDelight によるローカルDB（`AppDatabase`）
- UI: Compose Multiplatform による軽量 UI（`RootUI` にプレースホルダー）
- Desktopプレビュー: `PreviewApp.kt` の `main()` で簡易起動

## リポジトリ内の実体
本プロジェクトは 2 モジュール構成（`:shared`, `:androidApp`）です。

```
kmp/
├─ settings.gradle.kts         # `:shared`, `:androidApp` を含む
├─ build.gradle.kts            # ルート（必要最低限）
├─ gradle.properties           # バージョン/Android 設定
├─ scripts/                    # 補助スクリプト
│  └─ run-android.sh           # エミュレーターにビルド/インストール/起動
├─ androidApp/                 # Android 実行アプリ（最小）
│  ├─ build.gradle.kts
│  └─ src/
│     └─ main/
│        ├─ AndroidManifest.xml
│        └─ kotlin/com/imageflow/kmp/app/MainActivity.kt
└─ shared/                     # KMP ライブラリ本体
   ├─ build.gradle.kts         # ターゲット/依存の定義
   └─ src/
      ├─ commonMain/           # ネットワークIF, DB抽象, UIなど
      ├─ androidMain/          # Android 実装（カメラ等）
      ├─ iosMain/              # iOS 実装（Native driver 等）
      ├─ desktopMain/          # Desktop 実装（プレビューエントリ）
      ├─ handheldMain/         # 小型端末向け補助ソースセット
      ├─ thinkletMain/         # THINKLET 向け補助ソースセット
      └─ commonTest/           # 共通テスト
```

## 必要環境
- JDK: 17
- Kotlin: 2.0 以降 / Gradle 8.x / AGP 8.x（本モジュールは Gradle Wrapper 8.14 を同梱）
- Android SDK: compileSdk 34 / minSdk 24
- Xcode: 15 以降（iOS ビルド）
- IDE: Android Studio または IntelliJ IDEA（Compose Multi 対応版）

## 開発フロー（順番）
1) 初回セットアップ
- Android Studio を使う場合（推奨）
  - Android Studio を起動（埋め込み JDK 17/SDK は自動セットアップ）
  - SDK Manager で「Android SDK Platform-Tools」をインストール（`adb` 確認: `adb version`）
  - Device Manager で AVD を作成（初回はシステムイメージDL）
- CLI も使う場合の補足
  - 本リポジトリは `kmp/` に Gradle Wrapper（8.14）を同梱（`kmp/gradlew`）
  - もし `kmp/gradle/wrapper/gradle-wrapper.jar` が無い場合は、以下のいずれかで生成
    - Android Studio: Gradle ツールウィンドウ > Tasks > build > `wrapper`
    - CLI: `brew install gradle` → `cd kmp && gradle wrapper --gradle-version 8.14`
  - `chmod +x kmp/gradlew` を実行して実行権限を付与

2) Android Studio で実行（最も簡単）
- Android Studio で `ImageFlowCanvas/kmp` を開く
- Gradle 設定: Use Gradle from = Gradle Wrapper、Gradle JDK = 17（通常は自動）
- AVD を起動（Device Manager）
- 実行方法（いずれか）
  - Gradle タスク: `:androidApp > installDebug` を実行 → エミュレータで `com.imageflow.kmp.app` を起動
  - もしくは Run 構成で `androidApp` を選び起動

3) CLI で実行（ワンコマンド）
- プロジェクトルートから実行
  - `bash kmp/scripts/run-android.sh`

4) CLI で実行（手動）
- エミュレータ起動 → `adb devices` で接続確認
- ビルド〜起動
  - `cd kmp`
  - `./gradlew :shared:build`
  - `./gradlew :androidApp:assembleDebug`
  - `./gradlew :androidApp:installDebug`
  - `adb shell am start -n com.imageflow.kmp.app/.MainActivity`

5) 開発サイクルの目安
- 変更する主な場所
  - 共有ロジック/UI: `shared/src/commonMain/...`（例: `ui/placeholder/RootUI.kt`）
  - Android固有: `shared/src/androidMain/...`（例: カメラやセンサー実装）
- 反映
  - Studio: 再ビルド/再実行（または `installDebug`）
  - CLI: `./gradlew :androidApp:installDebug` → 既存アプリを上書きインストール
- ログ確認
  - `adb logcat | grep -i imageflow`（例: `AndroidCameraController` のログ）

## ビルドとテスト（何をしているか）
- 目的: `:shared` はKMPライブラリ（共通コード）です。この節はライブラリ単体のビルド/テストをまとめています。Androidアプリ（`:androidApp`）のAPKは次の節で扱います。
- 共通ビルド（ライブラリのビルド）: `./gradlew :shared:build`
  - 生成物の例: `shared/build/` 配下（ターゲット別にKLIB/JVMクラス/JARなど）
  - 備考: Androidアプリをビルドするときは、Gradleが依存として自動ビルドするため省略可です。
- 共通テスト（ライブラリのテスト）: `./gradlew :shared:check`
  - 実行されるもの: `shared/src/commonTest` 等のユニットテスト（現状はプレースホルダ）
  - 成果物: テストレポート（`shared/build/reports/tests` など）

### Androidエミュレーターで試す（順番に実行）
1) 前提（初回のみ）
  - JDK 17: Android Studio の埋め込み JDK（17）を利用するのが最も簡単です（Studio が自動設定）。CLI のみで使う場合に限り、別途 JDK 17 をインストールして `java -version` で確認してください。
  - SDK/Platform-Tools: Android Studio 初回セットアップで SDK/Platform-Tools（adb, emulator）がインストールされます。run-android.sh を使う場合は `adb` が PATH にある必要があります。SDK Manager で「Android SDK Platform-Tools」を入れ、必要なら `export PATH=$ANDROID_HOME/platform-tools:$PATH` を設定（確認: `adb version`）。
  - AVD（エミュレーター）: Android Studio の Device Manager で作成（初回はシステムイメージのダウンロードが走ります）。
  - Gradle Wrapper の準備（重要）
    - 通常は `kmp/` に Wrapper（8.14）を同梱していますが、`kmp/gradle/wrapper/gradle-wrapper.jar` が無い場合は次のいずれかで生成してください。
      - Android Studio: `ImageFlowCanvas/kmp` を開き、Gradle ツールウィンドウ > Tasks > build > `wrapper` を実行
      - CLI: `brew install gradle` → `cd kmp && gradle wrapper --gradle-version 8.14`
    - 念のため `chmod +x kmp/gradlew` を実行して実行権限を付与
  - 補足: AndroidX は `kmp/gradle.properties` にて有効化済み（`android.useAndroidX=true`）

2) エミュレーターを起動
  ```bash
  # いずれか（Android Studio から起動でもOK）
  emulator -list-avds
  emulator -avd <AVD名>
  adb devices   # 起動済みデバイスが一覧に出ることを確認
  ```

3) プロジェクトへ移動
  ```bash
  cd kmp
  ```

4) 依存を解決してビルド
  ```bash
  ./gradlew :shared:build
  ./gradlew :androidApp:assembleDebug
  ```

5) エミュレーターへインストール
  ```bash
  ./gradlew :androidApp:installDebug
  ```

6) アプリを起動
  ```bash
  adb shell am start -n com.imageflow.kmp.app/.MainActivity
  ```

7) ワンコマンドで実行（上記2〜6をまとめて実行）
  ```bash
  # プロジェクトルートから
  bash kmp/scripts/run-android.sh
  ```

トラブル時のヒント:
- `Plugin … not found` の場合: `kmp/settings.gradle.kts` 内でプラグイン/リポジトリを定義済みです。インターネット接続とプロキシ設定を確認してください。
- `No connected devices` の場合: AVD が起動しているか（`adb devices` で確認）をチェックしてください。
- 依存解決エラー: `kmp/gradle.properties` のバージョン値（`compose.version`, `ktor.version` など）やネットワーク環境を確認してください。

### よくあるエラーと対処
- `[ERROR] Gradle が見つかりません。…` が出る
  - 原因: `./gradlew` が見えていないディレクトリでコマンドを実行した可能性があります。
  - 対処:
    - `cd kmp` の上で `./gradlew ...` を実行
    - あるいはプロジェクトルートから `bash kmp/scripts/run-android.sh` を実行

- Compose Compiler プラグイン関連（Kotlin 2.0 以降）
  - エラー例:
    - `Starting in Kotlin 2.0, the Compose Compiler Gradle plugin is required when compose is enabled.`
    - `Configuration problem: ... you must apply "org.jetbrains.kotlin.plugin.compose" plugin.`
  - 原因: Kotlin 2.0 以降は Compose 利用モジュールに `org.jetbrains.kotlin.plugin.compose` の適用が必須。
  - 本リポジトリの対応:
    - `kmp/settings.gradle.kts` の `pluginManagement` に `id("org.jetbrains.kotlin.plugin.compose") version "2.0.21"` を追加済み
    - `kmp/shared/build.gradle.kts` と `kmp/androidApp/build.gradle.kts` の `plugins { ... }` に
      `id("org.jetbrains.kotlin.plugin.compose")` を適用済み
  - それでも解決しない場合:
    - Android Studio を再起動し、`File > Invalidate Caches / Restart` を実行
    - Gradle を `./gradlew --stop && ./gradlew clean build` でクリーン
    - Kotlin/Compose/AGP のバージョン整合: Kotlin 2.0.21 / Compose 1.8.2 / AGP 8.5.2 を前提に同期

- Gradle と Compose の不整合（Gradle 9.x milestone 使用時）
  - 症状例:
    - `An exception occurred applying plugin request [id: 'org.jetbrains.compose', version: '1.6.11']`
    - `Shared build service ... ConfigurationProblemReporterService parameters have unexpected type: org.gradle.api.services.BuildServiceParameters`
  - 原因: `org.jetbrains.compose` 1.6.11 は Gradle 9.0-milestone 系と互換性が不十分。Gradle 8.x の安定版で実行する必要があります。
  - 対処（推奨: Gradle 8.14 に固定）:
    1. Wrapper を作成（未作成の場合）: Android Studio の Gradle タスク `wrapper`、または `cd kmp && gradle wrapper --gradle-version 8.14`
    2. Android Studio 設定: Gradle > Use Gradle from: Gradle Wrapper、Gradle JDK: 17
    3. 既存 Wrapper の場合は `kmp/gradle/wrapper/gradle-wrapper.properties` を編集:
       `distributionUrl=https\://services.gradle.org/distributions/gradle-8.14-bin.zip`
    4. 再同期後に `./gradlew :androidApp:installDebug` で確認

### Android Studio の「Updates available（AGPを8.12.0へ）」表示について
- これはIDEの推奨でありエラーではありません。本モジュールはKotlin Multiplatformの互換性の都合により、AGPを8.5.2に固定しています。
- 理由: Kotlin 2.0.21時点のKotlin Gradle Pluginがテスト済みとしているAGPの上限は8.5系のため、それ以上に上げると未検証領域となり不具合の可能性があります。
- 対応: この提案は無視してください。将来Kotlin/Composeの対応が進んだ段階でAGPを更新します。
- どうしても警告を抑止したい場合は `kotlin.mpp.androidGradlePluginCompatibility.nowarn=true` を `kmp/gradle.properties` に追加できます（推奨はしません）。
- 代替案: Compose を 1.7.x に上げる（Gradle 9 系との互換性向上）
    - `kmp/settings.gradle.kts` の pluginManagement で `id("org.jetbrains.compose") version "1.7.0"`
    - `kmp/gradle.properties` の `compose.version=1.7.0`
    - 周辺バージョンの整合確認が必要

 


### Android（ライブラリとして利用）
- AAR 生成: `./gradlew :shared:assembleRelease`
  - 出力例: `shared/build/outputs/aar/shared-release.aar`
- 利用例（別 Android アプリから）:
  - 同一 Gradle プロジェクト: `implementation(project(":shared"))`
  - アプリ起動時に DB 用 Context 初期化:
    ```kotlin
    // Application#onCreate など
    AndroidDbContextHolder.context = applicationContext
    ```

### iOS（Framework 出力）
- デバッグ用フレームワーク（シミュレータ）:
  - `./gradlew :shared:linkDebugFrameworkIosSimulatorArm64`
- 実機向けリリース:
  - `./gradlew :shared:linkReleaseFrameworkIosArm64`
- 出力例:
  - `shared/build/bin/iosSimulatorArm64/debugFramework/Shared.framework`
  - `shared/build/bin/iosArm64/releaseFramework/Shared.framework`
- Xcode への組み込み: 生成された `*.framework` を Xcode プロジェクトに追加（現在 CocoaPods/SwiftPM は未設定）

### Desktop（プレビュー起動）
- `shared/src/desktopMain/kotlin/com/imageflow/kmp/desktop/PreviewApp.kt` の `main()` を IDE から実行
  - 画面タイトル: "ImageFlow KMP Preview"
  - `RootUI()` が起動し、カメラ制御の開始を確認できる最小UI
  - Gradle タスクでの起動は未設定（必要なら `compose.desktop.application` の追加を検討）

## 付録: `kmp/scripts/run-android.sh` の概要と使い方

このスクリプトは、以下の処理を順番に自動実行します。

### 概要（何をするか）
- `adb` の存在チェックと、接続済みデバイス/エミュレーターの確認
- Gradle 実行コマンドの選択（`./gradlew` があればそれを優先、無ければ `gradle`）
- `:shared` のビルドと `:androidApp` の `installDebug` 実行
- `adb shell am start` で `com.imageflow.kmp.app/.MainActivity` を起動
- デバイス未接続や `adb` 未インストール時は分かりやすいエラーメッセージを表示して中断

### 使い方
- 事前に Android エミュレーター（AVD）を起動し、`adb devices` で表示されることを確認してください。
- プロジェクトルート（`ImageFlowCanvas/`）から実行:
  ```bash
  bash kmp/scripts/run-android.sh
  ```

## 提供 API/抽象（抜粋）
- ネットワーク IF: `com.imageflow.kmp.network.ApiClient`（`GrpcClient`/`RestClient`/`WebSocketClient`）
- プラットフォーム抽象: `CameraController`/`SensorManager`/`FileManager`/`Notifier`
- DB: `com.imageflow.kmp.database.DatabaseProvider` と `AppDatabase`（SQLDelight）
- UI: `com.imageflow.kmp.ui.placeholder.RootUI`

バックエンドとの接続はプロジェクト全体の設計（docs/0300_設計_アプローチ1）に準拠します。
- 認証・設定: `POST /api/v1/kmp/devices/register`, `POST /api/v1/kmp/auth/login`, `GET/PUT /api/v1/kmp/config`
- リアルタイム通知: `ws://.../ws/system-status`, `ws://.../ws/camera-stream` ほか
- 高速処理: gRPC 直接呼び出し（フォールバックに Kafka）

## 実装メモ（プラットフォーム別）
- Android: `AndroidDbContextHolder` を初期化してから DB を使用。カメラ/センサー/通知は `androidMain` 実装を利用。
- iOS: SQLDelight の Native ドライバを使用。生成 Framework を Xcode に追加して呼び出し。
- Desktop: IDE で `PreviewApp.main()` を実行して開発中 UI を確認。

## トラブルシューティング
- Gradle JDK は 17 を使用（IDE の Gradle JVM 設定を確認）
- 依存解決エラー時は `gradle.properties` のバージョン値（`ktor.version`/`coroutines.version`/`sqldelight.version` 等）を確認
- iOS Framework 出力で失敗する場合は Xcode のコマンドラインツール設定やターゲットの選択を確認

## 今後の拡張（TODO）
- gRPC/REST/WS クライアントの実装（現在は IF のみ）
- CocoaPods/SwiftPM 統合の公式化
- Desktop 実行用 Gradle タスク（`compose.desktop.application`）の追加
- DB スキーマとマイグレーション定義

本モジュールは ImageFlowCanvas 全体の「端末/エッジ側」コンポーネントです。Web/Backend とあわせて利用することで、高速な画像処理パイプラインやリアルタイム監視を端末側で活用できます。
