# THINKLET App (Android)

THINKLET（Androidベース）にインストールして使う簡易配信アプリ。WHIP/RTMP の配信 URL を入力し、配信操作の UI を提供します（配信ロジックは未実装のスタブ）。

## 機能
- WHIP/RTMP の送信先 URL 入力
- 配信開始/停止の UI（ログ表示）
- カメラ/マイク権限の要求

## ビルド/インストール

### ビルド（Debug APK 作成）
```bash
# ビルド
cd kmp && ./gradlew :thinkletApp:assembleDebug
# インストール
cd kmp && ./gradlew :thinkletApp:installDebug
```

生成物: `kmp/thinkletApp/build/outputs/apk/debug/thinkletApp-debug.apk`

### インストール（権限を事前付与してインストール）

THINKLET は画面が無いため、インストール時に権限を付与しておくことを推奨します。

```bash
APK=kmp/thinkletApp/build/outputs/apk/debug/thinkletApp-debug.apk
adb install -g -r "$APK"
```
または、
```bash
adb install -r kmp/thinkletApp/build/outputs/apk/debug/thinkletApp-debug.apk
```

すでにインストール済みの場合は、権限のみ付与できます。

```bash
adb shell pm grant com.imageflow.thinklet.app android.permission.CAMERA
adb shell pm grant com.imageflow.thinklet.app android.permission.RECORD_AUDIO
adb shell pm grant com.imageflow.thinklet.app android.permission.ACCESS_FINE_LOCATION
```

- 端末の「位置情報」をON
  - Android 6–11系ではBLEスキャンに「位置情報の権限」＋「位置情報スイッチON」が必須です。
  - 確認: adb shell settings get secure location_mode の結果が 0 ならOFFです（3が高精度ON）。
  - 対処: 端末の設定で位置情報をONにして、アプリを再起動。

- BluetoothをONにする
  - 端末で設定 > Bluetooth を開きONにする
  - もしくはコマンドで設定画面を開く: adb shell am start -a android.settings.BLUETOOTH_SETTINGS

### 起動
```bash
adb shell am start -n com.imageflow.thinklet.app/.MainActivity
```

### ログの確認
```bash
adb shell logcat | grep -i BlePrivacy # BlePrivacyの箇所は任意のタグに置換
adb logcat -v time -s BlePrivacy:D 'ActivityManager:I' 'AndroidRuntime:E' # 期待: “BLE scanning started (type=any)” もしくは “(fallback)”
adb logcat -v time -s BlePrivacy:D # 期待ログ: BLE service created または BLE scanning started (type=any) または ensure: ... starting scan
```

## 使い方

THINKLET はディスプレイ非搭載想定のため、配信先や権限は「事前設定」で行います。アプリは起動後、自動で WHIP 配信を開始します（UI からの手動入力は不要）。

1) 権限を事前付与（必須）

```bash
adb shell pm grant com.imageflow.thinklet.app android.permission.CAMERA
adb shell pm grant com.imageflow.thinklet.app android.permission.RECORD_AUDIO
adb shell pm grant com.imageflow.thinklet.app android.permission.ACCESS_FINE_LOCATION
```

2) WHIP URL と自動起動の設定（ブロードキャスト）

```bash
# 例: サーバは 192.168.1.10、デバイスIDは任意
adb shell am broadcast \
  -a com.imageflow.thinklet.SET_CONFIG \
  --es url http://192.168.1.10:8889/whip/thinklet/<deviceId> \
  --ez autoStart true
```

- `url`: WHIP エンドポイント（MediaMTX の WHIP パス）。
- `autoStart`: true で起動時に自動配信開始（省略時は true）。
- URL 未設定時は既定で `http://<server>:8889/whip/thinklet/<androidId>` フォーマットを使用します（`<server>` は任意に置換が必要）。

3) アプリ起動（自動で配信開始）

```bash
adb shell am start -n com.imageflow.thinklet.app/.MainActivity
```

4) 停止/再開（暫定）

- 暫定: 強制停止で配信終了

```bash
adb shell am force-stop com.imageflow.thinklet.app
```

備考
- 画面なし運用のため、プレビューは行いません。
- 権限未付与のまま起動した場合は内部ログに警告を出して待機します。付与後に再起動してください。

## 今後の拡張
- RTMP 実装: `com.github.pedroSG94.rtmp-rtsp-stream-client-java`
- WHIP 実装: libwebrtc + WHIP API（MediaMTX 互換）
- THINKLET SDK 利用: `thinklet.app.sdk` を導入してマイク制御や CameraX 最適化
- H.264 固定 / 端末特性最適化 / 音声多ch 対応

## 注意
- `android:usesCleartextTraffic="true"` を有効化（開発時 http 接続許可）。本番は TLS 利用を推奨。
- MediaMTX は `deploy/compose` で `8888(HLS)/8889(WHIP)/1935(RTMP)` を公開しています。

## WebRTC 依存（JitPack を使わない構成）

本アプリは WebRTC を使って WHIP 配信を行います。JitPack を使わずにビルドするため、以下のどちらかの方法を選べます。

1) ローカル AAR を同梱（確実）
- `kmp/thinkletApp/libs/google-webrtc.aar` を配置します（ファイル名固定）。
- 取得元の例（環境により異なるため、利用可能な版を選択してください）:
  - MavenCentral/Google Maven の `org.webrtc:google-webrtc` の AAR をダウンロード
  - 例: `https://repo1.maven.org/maven2/org/webrtc/google-webrtc/` から `google-webrtc-<version>.aar` を取得
- 置いた場合はビルド時にローカル AAR が優先されます。

2) 公式 Maven から取得
- `thinkletApp/build.gradle.kts` は `org.webrtc:google-webrtc:1.0.+` を指定しています。
- ネットワーク・プロキシにより `maven.google.com` へアクセスできる必要があります。
- もし `1.0.+` が解決できない場合は、ブラウザで利用可能な版を確認し、固定版に差し替えてください。
