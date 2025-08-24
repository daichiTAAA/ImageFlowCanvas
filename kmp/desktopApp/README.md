## Desktop アプリ（Compose Multiplatform）

### 特長（Android版との共通化）
- **UI/ロジック共通**: `:shared` の `MobileInspectionScreen` / `ProductSearchScreen` / `SettingsScreen` と各種 ViewModel/UseCase をそのまま利用
- **画面構成**: Android版と同一。トップ、QRスキャン、順序情報検索、設定など
- **QRスキャン（実装済み）**: USB/Continuity Camera 映像を表示し、ZXing でQR/DataMatrix/Aztec/PDF417をデコード。指定形式と一致しない場合は、生データ／期待フォーマット／解析結果／差分を表示

### 事前準備
- JDK 17 必須（`java -version` が 17.x であること）
- 初回は依存取得のためインターネット接続が必要

### ビルド（開発）
```bash
cd kmp && ./gradlew :desktopApp:build
```

### ビルド＋起動（開発）
```bash
cd kmp && ./gradlew :desktopApp:run
```

### パッケージ作成（配布物）
```bash
cd kmp
./gradlew :desktopApp:packageAdHocSigned # MacOS用。開発向けの ad-hoc 署名付きパッケージを生成
./gradlew :desktopApp:packageDistributionForCurrentOS # 配布用パッケージを生成(署名なし)
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