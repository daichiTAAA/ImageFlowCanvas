# ImageFlowCanvas - Android Mobile Inspection Application

Android mobile inspection application implemented using Kotlin Multiplatform (KMP) architecture based on the requirements in `docs/0100_要件定義/0100_要件定義書.md` and design specifications in `docs/0300_設計_アプローチ1/0307_KotlinMultiplatformアプリ設計.md`.

## Overview

This implementation provides a comprehensive mobile inspection application that enables quality control inspectors to:

- **Scan QR codes** to identify products for inspection (F-021-1)
- **Search for products** via server integration (F-021-2)  
- **Perform AI-powered inspections** using captured images/video (F-022)
- **Verify and annotate AI results** through human review (F-023)
- **Manage inspection results** with full traceability (F-024)
- **Work offline** with automatic synchronization when connected

## Architecture

### Kotlin Multiplatform Structure

```
shared/
├── commonMain/          # Shared business logic across platforms
│   ├── kotlin/
│   │   └── com/imageflow/kmp/
│   │       ├── models/          # Data models (ProductInfo, Inspection, etc.)
│   │       ├── repository/      # Repository interfaces and implementations
│   │       ├── network/         # API service interfaces
│   │       ├── usecase/         # Business logic use cases
│   │       ├── workflow/        # Inspection workflow management
│   │       ├── state/           # State management
│   │       ├── qr/              # QR code processing
│   │       ├── ui/              # Shared UI components
│   │       └── di/              # Dependency injection
│   └── sqldelight/             # Database schema definitions
├── androidMain/         # Android-specific implementations
├── iosMain/             # iOS-specific implementations (placeholder)
├── desktopMain/         # Desktop-specific implementations (placeholder)
├── handheldMain/        # Handheld terminal optimizations
└── thinkletMain/        # THINKLET wearable device support
```

### Clean Architecture Layers

1. **Presentation Layer**: Jetpack Compose UI with reactive ViewModels
2. **Domain Layer**: Use cases encapsulating business logic
3. **Data Layer**: Repositories with offline-first design
4. **Platform Layer**: expect/actual implementations for platform-specific features

## Key Features Implemented

### 1. Product Identification (F-021-1, F-021-2)

- **QR Code Scanning**: Camera-based QR code recognition with validation
- **Product Search**: Server-based product lookup with local caching
- **Smart Caching**: Frequently used products cached for offline access
- **Validation**: Comprehensive product data validation with error handling

### 2. Inspection Workflow (F-022, F-023, F-024)

- **State Machine**: Complete inspection state management
- **AI Integration**: Automated inspection processing with confidence scoring
- **Human Verification**: Manual review and annotation of AI results
- **Progress Tracking**: Real-time inspection progress with completion indicators
- **Result Management**: Comprehensive inspection result storage and retrieval

### 3. Mobile-Optimized UI

- **Material Design 3**: Modern Android UI components
- **Reactive State Management**: StateFlow-based UI updates
- **Responsive Design**: Optimized for various screen sizes
- **Accessibility**: Support for accessibility features

### 4. Offline Support

- **Local Database**: SQLDelight-based offline storage
- **Sync Management**: Automatic background synchronization
- **Conflict Resolution**: Intelligent handling of data conflicts
- **Queue Management**: Offline operation queueing

## Technical Implementation

### Core Models

#### ProductInfo
```kotlin
@Serializable
data class ProductInfo(
    val id: String,
    val workOrderId: String,      // 指図番号
    val instructionId: String,    // 指示番号
    val productType: String,      // 型式
    val machineNumber: String,    // 機番
    val productionDate: String,   // 生産年月日
    val monthlySequence: Int,     // 月連番
    val qrRawData: String? = null,
    val status: ProductStatus = ProductStatus.ACTIVE,
    // ... additional fields for caching and sync
)
```

#### Inspection
```kotlin
@Serializable
data class Inspection(
    val id: String,
    val productId: String,
    val inspectionType: InspectionType,
    val inspectionState: InspectionState,
    val aiResult: AiInspectionResult? = null,
    val humanResult: HumanResult? = null,
    val imagePaths: List<String> = emptyList(),
    // ... additional fields for workflow management
)
```

### Key Use Cases

- **ScanProductUseCase**: QR code scanning and product identification
- **SearchProductUseCase**: Server-based product search with caching
- **InspectionWorkflowUseCase**: Complete inspection workflow management
- **SyncUseCase**: Data synchronization and offline support

### Database Schema

- **Products table**: Enhanced product information with access tracking
- **Inspections table**: Comprehensive inspection data with state management
- **Sync queues**: Priority-based synchronization management

## Android-Specific Features

### Camera Integration
- **CameraX**: Modern camera API with lifecycle awareness
- **QR Scanning**: Real-time QR code detection and processing
- **Image Capture**: High-quality image capture with metadata
- **Video Recording**: Video capture for detailed inspections

### UI Components
- **MobileInspectionScreen**: Main inspection interface
- **QrScanningScreen**: Real-time QR scanning interface
- **State-driven UI**: Reactive UI updates based on inspection workflow

## Getting Started

### Prerequisites
- Android Studio Arctic Fox or later
- Kotlin 1.9.0 or later
- Android SDK 24 or later
- **JDK 17** (required for SQLDelight)

## リポジトリ内の実体
本プロジェクトは 3 モジュール構成（`:shared`, `:androidApp`, `:desktopApp`）です。

### モジュール構成の詳細

#### `:shared` - Kotlin Multiplatform ライブラリ（本体）
- **役割**: 複数プラットフォームで再利用可能な共通ライブラリ
- **出力**: JAR/AAR/Framework（各プラットフォーム用のライブラリファイル）
- **内容**: 
  - **commonMain**: 全プラットフォーム共通のビジネスロジック、UI、データ層
  - **androidMain**: Android固有実装（カメラ、センサー、SQLiteドライバー）
  - **iosMain**: iOS固有実装（Native SQLiteドライバー）
  - **desktopMain**: Desktop固有実装（プレビューアプリ）

#### `:androidApp` - Android実行可能アプリ
- **役割**: `:shared`を使用するAndroid専用アプリケーション
- **出力**: APK（インストール可能なAndroidアプリ）
- **内容**:
  - `MainActivity`: アプリのエントリーポイント
  - `AndroidManifest.xml`: アプリの権限・設定
  - `:shared`への依存関係

#### `:desktopApp` - Desktop実行可能アプリ（Compose Desktop）
- **役割**: `:shared`を使用するWindows/macOS/Linux向けデスクトップアプリ
- **出力**: 実行可能アプリ（開発時は `run`、配布時は DMG/MSI/DEB）
- **内容**:
  - `Main.kt`: アプリのエントリーポイント（Compose Desktop）
  - `:shared`への依存関係（UI/ロジック共通化）

### 依存関係の流れ
```
:androidApp ─depends on─> :shared
                         ↓
                    commonMain (共通ロジック)
                    androidMain (Android実装)
```

```
kmp/
├─ settings.gradle.kts         # `:shared`, `:androidApp`, `:desktopApp` を含む
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
├─ desktopApp/                 # Desktop 実行アプリ（Compose Desktop）
│  ├─ build.gradle.kts
│  └─ src/jvmMain/kotlin/com/imageflow/kmp/desktop/Main.kt
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

## Desktop アプリ（Compose Multiplatform）

### 特長（Android版との共通化）
- **UI/ロジック共通**: `:shared` の `MobileInspectionScreen` / `ProductSearchScreen` / `SettingsScreen` と各種 ViewModel/UseCase をそのまま利用
- **画面構成**: Android版と同一。トップ、QRスキャン、順序情報検索、設定など
- **QRスキャン（実装済み）**: USB/Continuity Camera 映像を表示し、ZXing でQR/DataMatrix/Aztec/PDF417をデコード。指定形式と一致しない場合は、生データ／期待フォーマット／解析結果／差分を表示

### 事前準備
- JDK 17 必須（`java -version` が 17.x であること）
- 初回は依存取得のためインターネット接続が必要

### 起動（開発）
```bash
cd kmp
./gradlew :desktopApp:run
```

### パッケージ作成（配布物）
```bash
cd kmp
./gradlew :desktopApp:packageAdHocSigned
./gradlew :desktopApp:packageDistributionForCurrentOS
# 出力先: kmp/desktopApp/build/compose/binaries/main/{dmg,msi,deb}/
# 実行方法（macOSは .app を Finder から開くか、下記コマンド推奨）
open desktopApp/build/compose/binaries/main/app/ImageFlowDesktop.app
# ログの確認方法
log stream --predicate 'process == "ImageFlowDesktop"' --info
# または直接実行
./desktopApp/build/compose/binaries/main/app/ImageFlowDesktop.app/Contents/MacOS/ImageFlowDesktop
```

#### 開発向け Ad-hoc 署名（macOS）
- 目的: Gatekeeper/TCC（権限管理）で `.app` を安定的に扱わせ、Finder 起動時の初回カメラ許可ダイアログを確実に表示させるため、ビルド済み `.app` にアドホック署名を付与します（配布向けの正式署名ではありません）。
- 使い方:
  ```bash
  cd kmp
  ./gradlew :desktopApp:packageAdHocSigned
  # 生成先: kmp/desktopApp/build/compose/binaries/main/app/ImageFlowDesktop.app （ad-hoc署名済み）
  #        kmp/desktopApp/build/compose/binaries/main/dmg/ImageFlowDesktop-1.0.0.dmg
  ```
- 推奨起動フロー:
  1) 生成された `.app` を `/Applications` に移動
  2) Finder から起動し、初回のカメラ権限ダイアログで「OK」を選択
- 初回ダイアログが出ない/一度拒否してしまった場合（開発時の再プロンプト）:
  - 一時的にバンドルIDを変更して再パッケージすると別アプリ扱いとなり、再び初回プロンプトが表示されます。
    ```bash
    cd kmp
    ./gradlew :desktopApp:packageAdHocSigned -PbundleIdOverride=com.imageflow.kmp.desktop.dev
    ```
  - 既存バンドルIDで続ける場合は、システム設定で手動許可するか、開発時のみ `tccutil reset Camera com.imageflow.kmp.desktop` 実行後に Finder から起動してください。

### カメラが映らない/権限が表示されない場合の対処
- `.app` を `open` で起動しているか確認（`.app/Contents/MacOS/...` を直接実行しない）。
- 初回ダイアログで「許可」したか確認。拒否した場合は「システム設定 > プライバシーとセキュリティ > カメラ」で ImageFlowDesktop を有効化。
- それでも表示されない場合は `.app` を一度削除し、再度 `:desktopApp:packageDistributionForCurrentOS` で作成し直して `.app` から起動。
- もし項目が表示されない/うまく切り替わらない場合は、以下でカメラ権限をリセット
    - `tccutil reset Camera com.imageflow.kmp.desktop`

#### TCCにアプリが登録されない場合の推奨手順（macOS）
- 最も安定するのは、以下の順で固定パス配置＋隔離解除＋アドホック署名を行い、Finderから起動して権限ダイアログで「許可」する方法です。
  1) アプリを /Applications へ配置
     - `mv kmp/desktopApp/build/compose/binaries/main/app/ImageFlowDesktop.app /Applications/`
  2) 隔離属性を解除（Gatekeeperの隔離を外す）
     - `xattr -dr com.apple.quarantine /Applications/ImageFlowDesktop.app`
  3) 可能ならアドホック署名（バンドル内のネイティブを含めて深い署名）
     - `codesign --force --deep -s - "/Applications/ImageFlowDesktop.app"`
  4) カメラ権限をリセット（必要な場合のみ）
     - `tccutil reset Camera com.imageflow.kmp.desktop`
  5) Finderから `/Applications/ImageFlowDesktop.app` を開く → カメラ権限ダイアログで「OK」を選択

配布（ユーザー端末への配布）を想定する場合は、Developer ID 署名＋公証（notarization）の導入をご検討ください。Compose の `nativeDistributions { macOS { signing { … } notarization { … } } }` で設定可能です（本リポジトリの標準ビルドは開発用途の ad-hoc 署名のみを同梱）。

### ビルドが遅い場合の対処（3分以上かかるなど）
- 依存のネイティブダウンロード: `org.bytedeco:javacv-platform` は複数OS/CPUのFFmpeg/OpenCVネイティブを含むため、初回取得に時間がかかります。
- パッケージ（DMG/MSI/DEB）生成: `packageDistributionForCurrentOS` は jlink/jpackage によるランタイム画像・インストーラ作成を行うため時間がかかります。
- 開発中は以下が高速です。
  - アプリバンドルのみ作成: `./gradlew :desktopApp:createDistributable`（数十秒程度）
  - 直接起動: `./gradlew :desktopApp:run`
- macOS専用に軽量化する場合は依存をプラットフォーム個別指定に変更してください（ダウンロード容量・時間を削減）。
  ```kotlin
  // kmp/desktopApp/build.gradle.kts の依存
  dependencies {
      implementation("org.bytedeco:javacv:1.5.10")
      implementation("org.bytedeco:ffmpeg:6.1.1-1.5.10:macosx-arm64")
      // ZXing などはそのまま
  }
  ```
- 追加のビルド高速化: `kmp/gradle.properties` に `org.gradle.configuration-cache=true` と `org.gradle.parallel=true` を設定。

### 設定（API ベースURL）
- アプリ右上の「設定」から API ベースURLを入力・保存
- 例:
  - ローカルPCでバックエンドが `8000` で起動: `http://127.0.0.1:8000/v1`
  - 別端末へ接続: `http://<サーバーIP>:8000/v1`
- Android向けの `10.0.2.2` はエミュレーター専用のため、デスクトップでは使用しません

### よくあるエラー
- 依存解決エラー: ネットワーク/プロキシ設定を確認（初回は依存取得が走ります）
- Javaバージョン不一致: `JAVA_HOME` が 17 になっているか確認
- API接続失敗: 設定画面の「接続テスト」/「詳細診断」で原因を確認し、`docs/NETWORK_TROUBLESHOOTING.md` を参照

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

#### 永続的な設定（推奨）
毎回環境変数を設定するのを避けるため、シェル設定ファイルに追加します：

```bash
# .zshrcファイルにJava 17の設定を追加
echo '
# Java 17 for ImageFlowCanvas KMP development
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"' >> ~/.zshrc

# 設定を現在のセッションに適用
source ~/.zshrc

# 設定確認
java -version  # "17.0.x" が表示されることを確認
echo $JAVA_HOME  # "/opt/homebrew/opt/openjdk@17" が表示されることを確認
```

#### 一時的な設定（セッションのみ）
現在のターミナルセッションでのみJava 17を使用する場合：
```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@17
export PATH="$JAVA_HOME/bin:$PATH"
```

**注意**: bashを使用している場合は `.zshrc` の代わりに `.bashrc` または `.bash_profile` を使用してください。

#### Windows
1. **手動インストール（推奨）**
   - [Eclipse Temurin](https://adoptium.net/temurin/releases/?version=17) からJDK 17をダウンロード
   - インストーラーを実行し、「Set JAVA_HOME environment variable」をチェック
   - 環境変数PATHにJavaのbinディレクトリを追加
   - **この方法では永続的にJAVA_HOMEが設定されます**

2. **PowerShellで永続的な環境変数設定**
   ```powershell
   # システム環境変数としてJAVA_HOMEを設定（管理者権限が必要）
   [Environment]::SetEnvironmentVariable("JAVA_HOME", "C:\Program Files\Eclipse Adoptium\jdk-17.0.xx-hotspot", "Machine")
   
   # ユーザー環境変数として設定（管理者権限不要）
   [Environment]::SetEnvironmentVariable("JAVA_HOME", "C:\Program Files\Eclipse Adoptium\jdk-17.0.xx-hotspot", "User")
   
   # PATHに追加
   $currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
   [Environment]::SetEnvironmentVariable("PATH", "$currentPath;$env:JAVA_HOME\bin", "User")
   
   # 新しいPowerShellセッションで確認
   java -version
   ```

3. **Chocolateyを使用**
   ```powershell
   # Chocolateyでインストール（自動的に環境変数も設定される）
   choco install openjdk17

   # インストール確認
   java -version
   ```

4. **Scoopを使用**
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

# 永続的な環境変数設定
echo '# Java 17 for development
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export PATH="$JAVA_HOME/bin:$PATH"' >> ~/.bashrc

# 設定を現在のセッションに適用
source ~/.bashrc

# 設定確認
echo $JAVA_HOME
java -version
```

**注意**: zshを使用している場合は `.bashrc` の代わりに `.zshrc` を使用してください。
JAVA_HOMEのパスは `sudo update-alternatives --config java` で確認できます。

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

# 永続的な環境変数設定
echo '# Java 17 for development
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk
export PATH="$JAVA_HOME/bin:$PATH"' >> ~/.bashrc

# 設定を現在のセッションに適用
source ~/.bashrc

# 設定確認
echo $JAVA_HOME
java -version
```

**注意**: zshを使用している場合は `.bashrc` の代わりに `.zshrc` を使用してください。
JAVA_HOMEのパスは `sudo alternatives --config java` で確認できます。

#### SDKMAN（全プラットフォーム共通）
```bash
# SDKMANをインストール
curl -s "https://get.sdkman.io" | bash
source "$HOME/.sdkman/bin/sdkman-init.sh"

# Java 17をインストール
sdk list java                    # 利用可能なJavaバージョンを確認
sdk install java 17.0.16-tem    # Eclipse Temurin 17をインストール
sdk use java 17.0.16-tem        # Java 17を使用

# Java 17をデフォルトに設定（永続的な設定）
sdk default java 17.0.16-tem

# インストール確認
java -version
echo $JAVA_HOME
```

**SDKMANの利点**: 
- 複数のJavaバージョンを簡単に管理できる
- `sdk default` で永続的なデフォルト設定が可能
- プロジェクトごとに異なるJavaバージョンを使用できる

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

### モジュール別のビルドプロセス

#### `:shared` ライブラリのビルド
- **目的**: KMPライブラリ（共通コード）をプラットフォーム別にコンパイル
- **コマンド**: `./gradlew :shared:build`
- **生成物**: 
  - `shared/build/libs/` - JVM用JAR
  - `shared/build/outputs/aar/` - Android用AAR
  - `shared/build/bin/` - iOS用Framework、Native用KLIB
- **備考**: Androidアプリをビルドするときは、Gradleが依存として自動ビルドするため通常は省略可

#### `:androidApp` アプリのビルド
- **目的**: `:shared`を使用してAndroid APKを生成
- **コマンド**: `./gradlew :androidApp:assembleDebug`
- **プロセス**:
  1. `:shared`の`androidMain`と`commonMain`をコンパイル
  2. `:androidApp`のAndroid固有コードをコンパイル
  3. すべてを統合してAPKを生成
- **生成物**: `androidApp/build/outputs/apk/debug/androidApp-debug.apk`

#### 依存関係の自動解決
```
./gradlew :androidApp:assembleDebug
    ↓
:shared:compileDebugKotlinAndroid (自動実行)
    ↓
:androidApp:assembleDebug
```

### テスト実行

#### 共通テスト（ライブラリのテスト）
- **コマンド**: `./gradlew :shared:check`
- **実行されるもの**: `shared/src/commonTest` 等のユニットテスト（現状はプレースホルダ）
- **成果物**: テストレポート（`shared/build/reports/tests` など）

#### プラットフォーム固有テスト
- **Android**: `./gradlew :shared:testDebugUnitTest`
- **JVM**: `./gradlew :shared:jvmTest`
- **iOS**: `./gradlew :shared:iosSimulatorArm64Test`（要：Xcode）

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

#### 主な変更箇所と開発時の使い分け

#### `:shared`での開発（ライブラリ側）
- **共有ロジック/UI**: `shared/src/commonMain/...`
  - 例: `ui/placeholder/RootUI.kt` - 全プラットフォーム共通のUI
  - 例: `network/ApiClient.kt` - ネットワーク通信の抽象化
  - 例: `data/repository/` - データアクセス層
- **Android固有実装**: `shared/src/androidMain/...`
  - 例: `platform/AndroidCameraController.kt` - Androidカメラ実装
  - 例: `database/DriverFactory.android.kt` - Android SQLiteドライバー
- **SQLスキーマ**: `shared/src/commonMain/sqldelight/com/imageflow/kmp/db/`
  - 例: `Inspection.sq`, `Product.sq` - データベーススキーマ定義

#### `:androidApp`での開発（アプリ側）
- **アプリ設定**: `androidApp/src/main/AndroidManifest.xml`
  - 権限設定、アクティビティ定義
- **エントリーポイント**: `androidApp/src/main/kotlin/.../MainActivity.kt`
  - アプリ起動時の初期化処理
  - `:shared`ライブラリの初期化（例：`AndroidDbContextHolder.context`の設定）

#### 開発フローの違い

**ライブラリ開発（`:shared`）**
```bash
# ライブラリのビルド・テスト
./gradlew :shared:build
./gradlew :shared:check

# 他のプラットフォーム用の出力生成
./gradlew :shared:assembleRelease  # Android AAR
./gradlew :shared:linkDebugFrameworkIosArm64  # iOS Framework
```

**アプリ開発（`:androidApp`）**
```bash
# アプリのビルド・インストール（ライブラリも自動ビルド）
./gradlew :androidApp:assembleDebug
./gradlew :androidApp:installDebug
```

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
- Desktop: `./gradlew :desktopApp:run` で実行、または IDE で `PreviewApp.main()` を実行して開発中 UI を確認。

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
- Desktop カメラ連携（USB/Network）実装
- DB スキーマとマイグレーション定義

本モジュールは ImageFlowCanvas 全体の「端末/エッジ側」コンポーネントです。Web/Backend とあわせて利用することで、高速な画像処理パイプラインやリアルタイム監視を端末側で活用できます。
