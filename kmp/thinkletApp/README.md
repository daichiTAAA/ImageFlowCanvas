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
adb shell am broadcast   -a com.imageflow.thinklet.SET_CONFIG   --es url http://192.168.1.10:8889/whip/thinklet/<deviceId>   --ez autoStart true   --ez autoResume true
```

- `url`: WHIP エンドポイント。省略時は `http://192.168.0.5:8889/whip/thinklet/<androidId>` が使用されます。
- `autoStart`: true の場合、アプリ起動時に自動配信を開始します。
- `autoResume`: true の場合、内部ロジック（今後拡張予定）で停止後に再開を試みます。

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
