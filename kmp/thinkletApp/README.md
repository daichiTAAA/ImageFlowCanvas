# THINKLET App (Android)

ヘッドレス環境の THINKLET 端末向け WHIP 配信アプリです。BLE ビーコンやプライバシー制御は実装していません。起動後すぐに指定 URL へ WHIP 配信を開始することだけに特化しています。

## 機能
- WHIP 送信先 URL の保存
- アプリ起動時の自動配信開始
- WHIP エンドポイント疎通テスト（`/whip/test/`）
- カメラ/マイク権限の事前付与前提運用（UI はデバッグ用の状態表示のみ）

## ビルド/インストール

```bash
# ビルド
cd kmp && ./gradlew :thinkletApp:assembleDebug

# インストール（USB 接続端末へ）
cd kmp && ./gradlew :thinkletApp:installDebug
```

生成物: `kmp/thinkletApp/build/outputs/apk/debug/thinkletApp-debug.apk`

### 権限の付与

THINKLET は画面を持たないため、ADB で権限を付与してから起動します。

```bash
adb shell pm grant com.imageflow.thinklet.app android.permission.CAMERA
adb shell pm grant com.imageflow.thinklet.app android.permission.RECORD_AUDIO
```

## 設定

配信 URL や自動開始の設定はブロードキャストで更新できます。

```bash
adb shell am broadcast   -a com.imageflow.thinklet.SET_CONFIG   --es url http://192.168.1.10:8889/uplink/<deviceId>/whip   --ez autoStart true   --ez autoResume true
```

- `url`: WHIP エンドポイント。省略時は `http://192.168.0.5:8889/uplink/<androidId>/whip` が使用されます。
- `autoStart`: true の場合、アプリ起動時に自動配信を開始します。
- `autoResume`: true の場合、内部ロジック（今後拡張予定）で停止後に再開を試みます。

## THINKLET起動時の自動立ち上げ

THINKLET Launcher が読み込む `key_config.json` に `launch-app` アクションを設定すると、端末起動直後にキーイベントが入ったタイミングで `thinkletApp` を自動起動できます。以下の手順で設定します。

1. `key_config.json` を作成

   ```json
   {
     "key-config": [
       {
         "key-name": "center",
         "key-event": "single-released",
         "key-action": {
           "action-type": "launch-app",
           "action-param": {
             "package-name": "com.imageflow.thinklet.app",
             "class-name": "com.imageflow.thinklet.app.MainActivity",
             "action-name": "android.intent.action.MAIN",
             "flags": [
               "FLAG_ACTIVITY_NEW_TASK",
               "FLAG_ACTIVITY_RESET_TASK_IF_NEEDED"
             ]
           }
         }
       }
     ]
   }
   ```

   - `key-name` はアーム中央ボタン（`KEYCODE_CAMERA`）に対応します。
   - `single-released` を使うと、短押し時のリリースでアプリが立ち上がります（`first-pressed` では `launch-app` が使えないため非推奨）。
   - テンプレートは `kmp/thinkletApp/provisioning/key_config_autostart.json` に保存しています。

2. THINKLET に反映

   ```bash
   adb push kmp/thinkletApp/provisioning/key_config_autostart.json /sdcard/Android/data/ai.fd.thinklet.app.launcher/files/key_config.json
   adb shell input keyevent KEYCODE_APP_SWITCH
   adb shell input keyevent HOME
   ```

- `KEYCODE_APP_SWITCH` → `HOME` を送ることで Launcher に設定を再読込させます。
- `kmp/thinkletApp/scripts/setup-thinklet-autostart.sh` を使うと JSON の配置と Launcher リロードを一括で実行できます。

3. 起動直後の自動実行

   THINKLET の電源投入後、端末が起動完了したタイミングで中央ボタン（`KEYCODE_CAMERA`）の短押しを一度送ると、上記設定により `thinkletApp` が即時起動します。PC から制御する場合は、プロビジョニングスクリプトなどで次のコマンドを発行してください。

   ```bash
   adb wait-for-device
   adb shell input keyevent KEYCODE_CAMERA
   ```

- 物理ボタンを手動で押す場合でも同等に動作します。`thinkletApp` 側で `autoStart` を `true` に設定しておけば、起動直後に WHIP 配信が開始されます。
- スクリプトから自動トリガーする場合は `./kmp/thinkletApp/scripts/setup-thinklet-autostart.sh --trigger-start` を利用してください。

```bash
# リポジトリルートで実行
./kmp/thinkletApp/scripts/setup-thinklet-autostart.sh
# 電源投入直後の起動まで自動化したい場合
./kmp/thinkletApp/scripts/setup-thinklet-autostart.sh --trigger-start
```

## 起動

```bash
adb shell am start -n com.imageflow.thinklet.app/.MainActivity
```

## 動作概要
- アプリが起動し、必要権限が付与されていれば即座に WHIP 配信を開始します。
- 内蔵 UI はデバッグ用に現在の URL・ログ・テスト結果を表示するのみです。
- BLE ビーコンやプライバシーゾーンの検知処理は含みません。

## 今後の TODO
- 配信停止/再開操作 API の追加
- RTMP 対応や WHIP シグナリングのリトライ強化
- THINKLET SDK との連携
