# Android Stream App

./kmp/thinkletApp を元に、Android のスマートフォンで操作できる UI を備え、WebRTC ストリームと BLE ビーコンによる配信オン/オフ制御を実装したアプリケーションです。

THINKLET のヘッドレス版とは異なり、端末上で配信先 URL の入力や BLE 閾値の調整、配信開始/停止が行えます。BLE ビーコンがプライバシーゾーンを検知すると配信を停止し、解除された際は自動再開（設定可）します。

## 機能
- WHIP (WebRTC-HTTP Ingestion Protocol) による映像・音声配信
- 配信先 URL の保存／読み出し、手動での配信開始・停止
- BLE ビーコン (Eddystone UID / iBeacon / 任意ビーコン) を用いたプライバシー制御
- RSSI 閾値、判定秒数、保持時間などの BLE パラメーター調整
- アプリ内からカメラ・マイク・BLE 関連権限のリクエスト
- WHIP エンドポイント疎通テストの実行と結果表示

## ビルド/インストール

### ビルド（Debug APK 作成）
```bash
# ビルド
cd kmp && ./gradlew :androidStreamApp:assembleDebug
# インストール（USB 接続端末へ）
cd kmp && ./gradlew :androidStreamApp:installDebug
```

生成物: `kmp/androidStreamApp/build/outputs/apk/debug/androidStreamApp-debug.apk`

### 手動インストール（権限付与つき）
```bash
APK=kmp/androidStreamApp/build/outputs/apk/debug/androidStreamApp-debug.apk
adb install -g -r "$APK"
```
または、
```bash
adb install -r kmp/androidStreamApp/build/outputs/apk/debug/androidStreamApp-debug.apk
```

### 権限の手動付与
```bash
adb shell pm grant com.imageflow.androidstream.app android.permission.CAMERA
adb shell pm grant com.imageflow.androidstream.app android.permission.RECORD_AUDIO
adb shell pm grant com.imageflow.androidstream.app android.permission.ACCESS_FINE_LOCATION
```

- 端末の「位置情報」を ON にしてください（Android 6–11 系で BLE スキャンに必須）。
- Bluetooth を ON にしてください（設定アプリから、または `adb shell am start -a android.settings.BLUETOOTH_SETTINGS` で設定画面を開けます）。

### BLE ビーコン設定（例）
- iBeacon の場合
```bash
adb shell am broadcast -a com.imageflow.androidstream.SET_CONFIG \\
  --es beacon.type ibeacon \\
  --es ibeacon.uuid "12345678-ABCD-4ABC-8DEF-123456789ABC" \\
  --ei ibeacon.major 1000 \\
  --ei ibeacon.minor 2000 \\
  --ez privacy.match.strict true
```
- Eddystone UID の場合
```bash
adb shell am broadcast -a com.imageflow.androidstream.SET_CONFIG \\
  --es beacon.type eddystone_uid \\
  --es eddystone.namespace 00112233445566778899 \\
  --es eddystone.instance a1b2c3d4e5f6 \\
  --ez privacy.match.strict true
```

## 起動
```bash
adb shell am start -n com.imageflow.androidstream.app/.MainActivity
```

## ログの確認
```bash
adb logcat -v time -s AndroidStreamBle:D AndroidStreamCfg:I
adb logcat | grep -i AndroidStreamBle
```

## 使い方
1. アプリ起動後、「権限をリクエスト」で必要な権限を付与します。
2. 「WHIP URL」にエンドポイントを入力し「URLを保存」。必要に応じて「配信開始」で配信を開始します。
3. 「アプリ起動時に自動開始」「プライバシー解除時に再開」を切り替えて運用方針に合わせます。
4. BLE ビーコン条件を入力し「BLE設定を保存」。既定では Eddystone UID (namespace=00112233445566778899、instance=a1b2c3d4e5f6) を使用し、入域判定 0 秒／離域判定 1 秒で即座にプライバシーモードへ切り替わります。
5. 「WHIP エンドポイントをテスト」で疎通確認ができます。

## 注意
- `android:usesCleartextTraffic="true"` を有効化しています。運用時は HTTPS/TLS を推奨します。
- BLE スキャンは端末や OS バージョンによって追加権限（`BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT` など）が必要です。Android 12 以降は必ず許可してください。
- MediaMTX など WHIP 対応サーバーと接続する場合は `deploy/compose` の構成を参照してください。

## 追加設定（ブロードキャスト）
UI 以外にも、以下のように設定ブロードキャストで各種値を更新できます。

```bash
adb shell am broadcast -a com.imageflow.androidstream.SET_CONFIG \\
  --es url http://192.168.1.10:8889/whip/uplink/<deviceId> \\
  --ez autoStart true \\
  --ez autoResume true \\
  --es beacon.type eddystone_uid \\
  --es eddystone.namespace 00112233445566778899 \\
  --es eddystone.instance a1b2c3d4e5f6 \\
  --ei privacy.enter.rssi -70 \\
  --ei privacy.exit.rssi -80 \\
  --ei privacy.enter.seconds 0 \\
  --ei privacy.exit.seconds 1 \\
  --ei privacy.hold.seconds 30
```

キー項目や詳細な引数は `ConfigReceiver` を参照してください。
