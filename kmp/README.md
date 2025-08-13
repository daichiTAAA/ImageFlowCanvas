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
- **JDK: 17以上（必須）** - SQLDelight 2.0.2 がJava 17を要求します
- Kotlin: 2.0 以降 / Gradle 8.x / AGP 8.x（本モジュールは Gradle Wrapper 8.14 を同梱）
- Android SDK: compileSdk 35 / minSdk 24
- Xcode: 15 以降（iOS ビルド）
- IDE: Android Studio または IntelliJ IDEA（Compose Multi 対応版）

### Java 17 のセットアップ（重要）

#### macOS
```bash
# Homebrewでインストール
brew install openjdk@17

# システムJavaとして認識させる（管理者権限が必要）
sudo ln -sfn /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk /Library/Java/JavaVirtualMachines/openjdk-17.jdk

# インストール確認
/usr/libexec/java_home -V
java -version
```

現在のセッションでJava 17を使用する場合：
```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
```

#### Windows
1. **手動インストール**
   - [Eclipse Temurin](https://adoptium.net/temurin/releases/?version=17) からJDK 17をダウンロード
   - インストーラーを実行し、「Set JAVA_HOME environment variable」をチェック
   - 環境変数PATHにJavaのbinディレクトリを追加

2. **Chocolateyを使用**
   ```powershell
   # Chocolateyでインストール
   choco install openjdk17

   # インストール確認
   java -version
   ```

3. **Scoopを使用**
   ```powershell
   # Scoopでインストール
   scoop bucket add java
   scoop install openjdk17

   # インストール確認
   java -version
   ```

#### Linux (Ubuntu/Debian)
```bash
# APTでインストール
sudo apt update
sudo apt install openjdk-17-jdk

# インストール確認
java -version

# 複数のJavaがインストールされている場合の切り替え
sudo update-alternatives --config java
```

#### Linux (CentOS/RHEL/Fedora)
```bash
# DNF/YUMでインストール
sudo dnf install java-17-openjdk-devel
# または
sudo yum install java-17-openjdk-devel

# インストール確認
java -version

# 複数のJavaがインストールされている場合の切り替え
sudo alternatives --config java
```

#### SDKMAN（全プラットフォーム共通）
```bash
# SDKMANをインストール
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"

# Java 17をインストール
sdk list java                    # 利用可能なJavaバージョンを確認
sdk install java 17.0.16-tem    # Eclipse Temurin 17をインストール
sdk use java 17.0.16-tem        # Java 17を使用

# インストール確認
java -version
```

## 開発フロー（順番）

### クイックスタート（Android Studio使用 - 推奨）
1. **Java 17の確認**
   ```bash
   java -version  # "17.0.x" が表示されることを確認
   ```

2. **Android Studioでプロジェクトを開く**
   - Android Studio を起動
   - 「Open」を選択して `/Users/YOUR_USERNAME/ImageFlowCanvas/kmp` を開く
   - Gradle 設定: Use Gradle from = Gradle Wrapper、Gradle JDK = 17（通常は自動）

3. **エミュレーターの起動**
   - Device Manager でAVDを作成・起動

4. **アプリの実行**
   - Run Configuration で「androidApp」を選択
   - 緑の再生ボタンでビルド＆実行

### コマンドライン実行

#### ワンコマンド実行（最も簡単）
```bash
# プロジェクトルートから
bash kmp/scripts/run-android.sh
```

#### 手動実行
```bash
# 1. エミュレーター起動確認
adb devices

# 2. プロジェクトフォルダに移動
cd kmp

# 3. ビルド（Java 17環境で実行）
./gradlew :androidApp:assembleDebug

# 4. インストール
./gradlew :androidApp:installDebug

# 5. アプリ起動
adb shell am start -n com.imageflow.kmp.app/.MainActivity
```

## ビルドとテスト（何をしているか）
- 目的: `:shared` はKMPライブラリ（共通コード）です。この節はライブラリ単体のビルド/テストをまとめています。Androidアプリ（`:androidApp`）のAPKは次の節で扱います。
- 共通ビルド（ライブラリのビルド）: `./gradlew :shared:build`
  - 生成物の例: `shared/build/` 配下（ターゲット別にKLIB/JVMクラス/JARなど）
  - 備考: Androidアプリをビルドするときは、Gradleが依存として自動ビルドするため省略可です。
- 共通テスト（ライブラリのテスト）: `./gradlew :shared:check`
  - 実行されるもの: `shared/src/commonTest` 等のユニットテスト（現状はプレースホルダ）
  - 成果物: テストレポート（`shared/build/reports/tests` など）

### Android Studioでの実行（詳細手順）

#### 手順1: プロジェクトを開く
1. Android Studioを起動
2. 「Open」を選択
3. `/Users/YOUR_USERNAME/ImageFlowCanvas/kmp` フォルダを選択
4. 「Open」をクリック

#### 手順2: Gradle設定の確認
1. `File` > `Settings` (macOSでは `Android Studio` > `Preferences`)
2. `Build, Execution, Deployment` > `Build Tools` > `Gradle`
3. 設定を確認:
   - Use Gradle from: **Gradle Wrapper**
   - Gradle JDK: **17** （通常は自動選択）

#### 手順3: エミュレーターの起動
1. `Tools` > `Device Manager`
2. 既存のAVDを起動、または「Create Device」で新規作成
3. エミュレーターが起動するまで待機

#### 手順4: アプリの実行
1. 上部のRun Configurationで「androidApp」を選択
2. 緑の再生ボタン（▶️）をクリック
3. エミュレーターが選択されていることを確認して「OK」

#### 手順5: ビルド成功の確認
- **Build** ウィンドウでビルドログを確認
- **Run** ウィンドウでインストールログを確認
- エミュレーターでアプリが自動起動

### エミュレーターを手動で起動する場合
### 初回セットアップ（詳細）

#### Android Studio使用の場合（推奨）

##### 全プラットフォーム共通
1. **Android Studio のダウンロード・インストール**
   - [Android Studio公式サイト](https://developer.android.com/studio) からダウンロード
   - 各OS用のインストーラーを実行

2. **初回セットアップ**
   - Android Studio を起動
   - セットアップウィザードに従ってSDKをインストール
   - 埋め込みJDK 17/SDK は自動セットアップされます

3. **SDK Manager で「Android SDK Platform-Tools」をインストール**
   - `Tools` → `SDK Manager`
   - `SDK Tools` タブで「Android SDK Platform-Tools」をチェック
   - `Apply` をクリックしてインストール

4. **Device Manager で AVD を作成**
   - `Tools` → `Device Manager`
   - `Create Device` で新しいAVDを作成
   - 初回はシステムイメージのダウンロードが実行されます

5. **プロジェクトを開く**: `ImageFlowCanvas/kmp` フォルダを選択

6. **Gradle同期**: 初回は依存関係のダウンロードに時間がかかります

##### プラットフォーム固有の注意事項

**Windows**
- Windows Defenderやウイルス対策ソフトが Gradle ビルドを遅延させる可能性があります
- `%USERPROFILE%\.gradle` フォルダをウイルススキャンの除外に追加することを推奨
- Android SDKのパスにスペースや日本語文字が含まれないように注意

**Linux**
- KVM (Kernel Virtual Machine) の有効化が推奨されます（エミュレーター高速化）:
  ```bash
  # KVMサポートの確認
  egrep -c '(vmx|svm)' /proc/cpuinfo
  
  # KVMのインストール（Ubuntu/Debian）
  sudo apt install qemu-kvm libvirt-daemon-system
  sudo usermod -a -G kvm $USER
  ```
- `ANDROID_HOME` 環境変数の設定が必要な場合があります:
  ```bash
  export ANDROID_HOME=$HOME/Android/Sdk
  export PATH=$PATH:$ANDROID_HOME/platform-tools
  ```

#### CLI使用の場合

##### 1. Gradle Wrapper の準備
- 通常は `kmp/` に Wrapper（8.14）を同梱
- `kmp/gradle/wrapper/gradle-wrapper.jar` が無い場合：
  - Android Studio: Gradle ツールウィンドウ > Tasks > build > `wrapper`
  - CLI: `gradle wrapper --gradle-version 8.14`（要：Gradle事前インストール）

**実行権限の付与**
```bash
# macOS/Linux
chmod +x kmp/gradlew

# Windows（不要、.batファイルを使用）
# kmp/gradlew.bat が使用されます
```

##### 2. Android SDK/Platform-Tools の設定

**macOS/Linux**
```bash
# Android SDKのパス確認（Android Studio経由でインストールした場合）
echo $ANDROID_HOME
# 通常: $HOME/Library/Android/sdk (macOS) または $HOME/Android/Sdk (Linux)

# PATHに追加（必要な場合）
export PATH=$ANDROID_HOME/platform-tools:$PATH

# 確認
adb version
```

**Windows**
```powershell
# Android SDKのパス確認
echo $env:ANDROID_HOME
# 通常: C:\Users\%USERNAME%\AppData\Local\Android\Sdk

# PATHに追加（PowerShell）
$env:PATH += ";$env:ANDROID_HOME\platform-tools"

# 確認
adb version
```

##### 3. エミュレーターのコマンドライン起動

**全プラットフォーム共通**
```bash
# 利用可能なAVD一覧
emulator -list-avds

# エミュレーター起動
emulator -avd <AVD名>

# 接続確認
adb devices
```

#### 補足事項
- **AndroidX**: `kmp/gradle.properties` にて有効化済み（`android.useAndroidX=true`）
- **コンパイルSDK**: 35に更新（Android SDK Platform 35が自動ダウンロードされます）

### ビルド成功の確認

ビルドが正常に完了すると、以下の場所にAPKファイルが生成されます：
```
kmp/androidApp/build/outputs/apk/debug/androidApp-debug.apk
```

エミュレーターでアプリを確認するには：
1. **エミュレーターのホーム画面でアプリアイコンを探す**
2. **アプリ名**: 「ImageFlow KMP」または「AndroidApp」として表示
3. **タップして起動**

### 開発サイクル

日常的な開発では以下のコマンドが便利です：

```bash
# ビルドしてエミュレーターにインストール
./gradlew :androidApp:installDebug

# クリーン＆リビルド＆インストール
./gradlew clean :androidApp:installDebug

# ログを確認
adb logcat | grep -i imageflow
```

#### 主な変更箇所
- **共有ロジック/UI**: `shared/src/commonMain/...`（例: `ui/placeholder/RootUI.kt`）
- **Android固有実装**: `shared/src/androidMain/...`（例: カメラやセンサー実装）
- **SQLスキーマ**: `shared/src/commonMain/sqldelight/com/imageflow/kmp/db/`

#### 変更の反映
- **Android Studio**: 再ビルド/再実行（または `installDebug` タスク）
- **CLI**: `./gradlew :androidApp:installDebug` → 既存アプリを上書きインストール
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

#### Java 17関連のエラー
- **エラー**: `Dependency requires at least JVM runtime version 17. This build uses a Java 11 JVM.`
- **原因**: SQLDelight 2.0.2がJava 17以上を要求するが、Java 11を使用している
- **対処**: 
  1. Java 17をインストール（上記「Java 17のセットアップ」参照）
  2. 環境変数の設定：
     ```bash
     export JAVA_HOME=/opt/homebrew/opt/openjdk@17
     export PATH="$JAVA_HOME/bin:$PATH"
     ```
  3. 確認：`java -version` で "17.0.x" が表示されることを確認

#### SQLDelight関連のエラー
- **エラー**: `Unresolved reference 'AndroidSqliteDriver'`
- **原因**: SQLDelightのAndroidドライバーが依存関係に含まれていない
- **対処**: `shared/build.gradle.kts`の`androidMain`セクションに以下を追加
  ```kotlin
  implementation("app.cash.sqldelight:android-driver:$sqldelightVersion")
  ```

#### Ktor関連のエラー
- **エラー**: `Unresolved reference 'ContentNegotiation'`
- **原因**: Ktorのプラグインインポートパスが間違っている
- **対処**: 正しいインポートパスを使用
  ```kotlin
  import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
  import io.ktor.client.plugins.logging.Logging
  ```

#### 型の不一致エラー
- **エラー**: `Operator '==' cannot be applied to 'kotlin.Long' and 'kotlin.Int'`
- **原因**: SQLiteの数値型（Long）とKotlinのInt型の比較
- **対処**: Long型リテラルを使用
  ```kotlin
  synced = row.synced == 1L  // 1 ではなく 1L
  ```

#### Gradle関連のエラー
- **エラー**: `[ERROR] Gradle が見つかりません。…`
- **原因**: `./gradlew` が見えていないディレクトリでコマンドを実行
- **対処**:
  - `cd kmp` の上で `./gradlew ...` を実行
  - あるいはプロジェクトルートから `bash kmp/scripts/run-android.sh` を実行

#### Compose Compiler プラグイン関連のエラー
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

### 環境関連
- **Java バージョン**: JDK 17以上が必須（`java -version` で確認）
- **Gradle JDK**: IDE の Gradle JVM 設定を17に設定
- **Android SDK**: SDK Manager で Platform-Tools をインストール済みか確認

#### プラットフォーム固有のトラブル

**Windows固有**
- **長いパス名エラー**: Windows の260文字パス制限に注意
  - プロジェクトをCドライブ直下など短いパスに配置
  - または長いパス名を有効化: `gpedit.msc` → コンピューターの構成 → 管理用テンプレート → システム → ファイルシステム
- **ウイルス対策ソフト**: Gradleビルドが遅い場合
  - `%USERPROFILE%\.gradle` をスキャン除外に追加
  - `%USERPROFILE%\.android` をスキャン除外に追加
- **PowerShell実行ポリシー**: スクリプト実行が拒否される場合
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```

**Linux固有**
- **KVM未対応**: エミュレーターが非常に遅い場合
  ```bash
  # CPU仮想化サポートの確認
  egrep -c '(vmx|svm)' /proc/cpuinfo
  
  # KVMインストール（Ubuntu/Debian）
  sudo apt install qemu-kvm libvirt-daemon-system
  sudo usermod -a -G kvm $USER
  # 再ログインまたは再起動が必要
  ```
- **32bit ライブラリ**: Android SDKツールに必要（64bit Linux）
  ```bash
  # Ubuntu/Debian
  sudo apt install libc6:i386 libncurses5:i386 libstdc++6:i386 lib32z1
  
  # CentOS/RHEL/Fedora
  sudo dnf install glibc.i686 ncurses-libs.i686 libstdc++.i686
  ```
- **権限エラー**: `/dev/kvm` へのアクセス拒否
  ```bash
  # ユーザーをkvmグループに追加
  sudo usermod -a -G kvm $USER
  # 再ログインが必要
  ```

**macOS固有**
- **Rosetta 2**: Apple Silicon Mac で Intel バイナリを実行する場合
  ```bash
  /usr/sbin/softwareupdate --install-rosetta --agree-to-license
  ```
- **Gatekeeper**: 未署名のアプリケーション実行時
  - システム環境設定 → セキュリティとプライバシー → 一般 → 「このまま開く」

### 依存関係エラー
- **ネットワーク**: インターネット接続とプロキシ設定を確認
- **バージョン整合性**: `gradle.properties` の各バージョン値を確認
  - `ktor.version=2.3.12`
  - `coroutines.version=1.8.1`
  - `sqldelight.version=2.0.2`

### エミュレーター関連
- **デバイス未接続**: `adb devices` で接続を確認
- **AVD起動失敗**: Android Studio の Device Manager で別のAVDを試す
- **アプリが見つからない**: エミュレーターのアプリ一覧で「ImageFlow KMP」または「AndroidApp」を探す

### ビルド関連
- **クリーンビルド**: `./gradlew clean` 後に再ビルド
- **Gradle Daemon**: `./gradlew --stop` でDaemonを停止後に再実行
- **キャッシュクリア**: Android Studio で `File` > `Invalidate Caches / Restart`

## 今後の拡張（TODO）
- gRPC/REST/WS クライアントの実装（現在は IF のみ）
- CocoaPods/SwiftPM 統合の公式化
- Desktop 実行用 Gradle タスク（`compose.desktop.application`）の追加
- DB スキーマとマイグレーション定義

本モジュールは ImageFlowCanvas 全体の「端末/エッジ側」コンポーネントです。Web/Backend とあわせて利用することで、高速な画像処理パイプラインやリアルタイム監視を端末側で活用できます。
