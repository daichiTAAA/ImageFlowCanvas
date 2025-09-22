# BLEビーコン連携

| 項目       | 内容                                  |
| ---------- | ------------------------------------- |
| 文書名     | BLEビーコン連携                       |
| バージョン | 1.0                                   |
| 作成日     | 2025-09-06                            |
| 対象       | THINKLET（Fairy OS, Android互換）     |

---

## 1. 概要
本書は、プライバシー保護（トイレ・更衣室等のPrivacy Zone）や自動停止制御を目的として、THINKLETでBLEビーコンを利用する際の基本知識、接続可否、採用理由、利用・実装方法を整理するものです。

関連: `docs/0300_設計_アプローチ1/0300_システム基本設計.md`、`docs/0300_設計_アプローチ1/0304_API設計.md`、`docs/9000_調査/0010_THINKLET/THINKLET資料.md`

---

## 2. BLEビーコンとは？
- BLE（Bluetooth Low Energy）の広告パケット（Advertising）を周期送信する発信機。
- 代表規格: iBeacon（Appleフォーマット）、Eddystone-UID/EID/URL（Google系）。
- 特徴:
  - 非接続型（通常はGATT接続不要）。受信側はスキャンして識別子（UUID/Namespace/Instance等）とRSSIを読む。
  - 低消費電力でボタン/電源不要。電池駆動で年単位運用が可能。
  - 電波強度（RSSI）から概位置や近接状態を推定できる（しきい値＋ヒステリシスで安定化）。

プライバシー用途では「ゾーン入口でビーコンを検出→入室中は録画・配信を停止」という近接トリガーとして用います。

---

## 3. THINKLETとは接続できるか？（可否）
- 可。`THINKLET資料.md`に記載のとおり、THINKLETは Bluetooth 4.2/BLE を搭載し、Android SDK互換アプリが動作します。
- 目的は「接続」よりも「受信（スキャン）」で十分です。一般的なビーコンは接続不要で、`BluetoothLeScanner` による広告受信のみで判定可能です。
- 必要権限（Android 12+の例）: `BLUETOOTH_SCAN`、`BLUETOOTH_CONNECT`、位置情報（スキャン用途）。フォアグラウンドサービスでの常時スキャンを推奨。

---

## 4. なぜBLEビーコンを使用するのか？（採用理由）
- 自動性: 視認・操作不要で入室直後に録画停止できる（QRは「見る/かざす」行為が必要）。
- 取りこぼし低減: 入り口で必ず電波を跨ぐため、見落としによる撮りこぼし（停止し忘れ）を抑制。
- 運用容易: 印刷メディアより初期費用はかかるが、年1回程度の電池交換で安定運用可能。
- 偽造耐性: Eddystone-EID等の時変IDやサーバ側照合で偽装を検知しやすい。署名付きQRは冗長・手動バックアップとして併用。

補完関係: 「BLE（主）＋ 署名付きQR（副）」とし、BLE検知で自動停止、QRで手動停止/退出復帰を提供します。

---

## 5. どのようにTHINKLETで使用するのか？（利用方法）

### 5.1 動作概念
1) THINKLET側フォアグラウンドサービスがビーコンをスキャン。
2) 指定ゾーンのビーコン識別子（例: Eddystone-UID/EID, iBeacon UUID/Major/Minor）を検出したら、RSSIと時間ヒステリシスで入室判定。
3) 入室確定時:
   - 端末は即時に録画・配信・音声を停止（ローカル制御）。
   - Backendに`privacy_suspend`（`/api/v1/uplink/control`）とテレメトリ（`/api/v1/uplink/sessions/{id}/telemetry`）を送信。
   - サーバはセッション状態を`SUSPENDED(privacy)`へ遷移し、Ingest/Recorder/配信は保存・配信をブロック（監査ログのみ記録）。
4) 退出判定（RSSIが下がる等）＋明示操作（ボタン/退出QR）で復帰二重確認→`privacy_resume`。

### 5.2 判定ロジック例（推奨）
- 入室: RSSI > −70 dBm が連続2秒（例: サンプリング4回, 500ms間隔）。
- 退出: RSSI < −80 dBm が連続5秒 ＋ 操作/退出QRのどちらか。
- 多ビーコン環境: 最強RSSIを採用。フェンス外ビーコンは無視（ホワイトリスト）。

### 5.3 セキュリティ設計
- 識別子の検証: サーバ側で`zone_id ↔ beacon_id`を管理し、受信イベントと時刻・装置IDを照合。
- 偽装耐性: 可能ならEddystone-EID（時変ID）を採用。難しければUID/iBeacon＋TLSでサーバ照合、物理封印で盗難・持出し防止。
- 環境シグナル併用: 近傍Wi‑Fi BSSIDホワイトリスト一致や設置位置のQRとのAND条件で信用度を加点。
- サーバ強制ガード: ゾーン有効時は原本/加工いずれも保存拒否（API設計 3.4.3 の再生制御と整合）。

### 5.4 バッテリー・省電力
- スキャン間隔: 通常時は低Duty（例: 300–500ms interval/2–5秒スリープのデューティ制御）。検知直後は間欠化して消費を抑制。
- フォアグラウンドサービス＋通知でOSに最適化対象とされないようにする。移動が少ない環境ではモーション連動でスキャン開始/停止。

### 5.5 フォールバック
- 署名付き「プライバシーQR」を入口に掲示。スキャン失敗やBLE障害時でも手動で即停止可能。
- サーバ側はゾーンフラグが立っている間、フレーム受信を破棄し保存拒否（終端での強制）。

---

## 6. 実装ガイド（Kotlin/Android想定）

### 6.1 KMPインターフェース設計
- 共有コードに `interface BeaconWatcher { fun start(); fun stop(); }` を定義。
- Androidターゲットで `actual` 実装として BLE スキャンを実装。他プラットフォームはスタブ。

### 6.2 BLEスキャン実装の要点（Android）
- 権限: Android 12+ は `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT`、位置情報（正確なスキャン用）。
- サービス: フォアグラウンドサービスで `BluetoothLeScanner` を起動、`ScanFilter` に iBeacon/Eddystone シグネチャを設定。
- 判定: RSSI の移動平均＋ヒステリシスで入退室を安定化。
- 通知: 入室時にローカル処理停止→`/api/v1/uplink/control`へ`privacy_suspend`、退出時に`privacy_resume`。テレメトリで監査記録。

擬似コード（概略）:
```kotlin
class PrivacyZoneService : Service() {
  private val scanner = BluetoothAdapter.getDefaultAdapter().bluetoothLeScanner
  private val filters = listOf(iBeaconFilter(), eddystoneUidFilter())
  private val settings = ScanSettings.Builder()
    .setScanMode(ScanSettings.SCAN_MODE_LOW_POWER)
    .build()

  override fun onStartCommand(i: Intent?, flags: Int, startId: Int): Int {
    startForeground(/* notification */)
    scanner.startScan(filters, settings, callback)
    return START_STICKY
  }

  private val callback = object : ScanCallback() {
    override fun onScanResult(callbackType: Int, result: ScanResult) {
      val id = parseBeaconId(result) ?: return
      if (isWhitelisted(id) && enterDetected(result.rssi)) {
        localPrivacySuspend()               // 録画/配信/音声を即時停止
        postControl("privacy_suspend")     // /api/v1/uplink/control
        postTelemetry(/* zone, rssi */)
      }
      if (exitDetected(result.rssi) && confirmUserOrExitQR()) {
        postControl("privacy_resume")
        localPrivacyResumeSafely()
      }
    }
  }
}
```

---

## 7. 設置ガイド（現場）
- 設置位置: トイレ/更衣室の「入口外側」天井/鴨居付近（室外で検知＝入室前に停止）。
- 電波設定: TX出力は低め、Adv interval 200–500ms。メジャードパワーを現場でキャリブレーション。
- しきい値調整: 金属反射や遮蔽を考慮し、−70/−80 dBmを基準に現場実測で微調整。
- 物理対策: 取り外し防止の封印・ビス止め。IDラベルは外観非表示（管理台帳で紐づけ）。

---

## 8. 運用・保守
- 電池交換: 年1回点検（電圧/送信強度の簡易測定）。
- 識別子運用: EID推奨／UID/iBeaconの場合は識別子のローテーション（月次）。
- インシデント対応: スキャン不可時はQRで手動停止。端末/サーバの監査ログを確認し是正。
- 定期検証: 月次で「停止→復帰」の自動テストを実施（RSSIシナリオ・API到達・保存拒否の確認）。

---

## 9. リスクと対策
- なりすまし電波: Eddystone-EIDなど時変IDの採用、サーバ照合、環境シグナル（BSSID）併用。
- 誤検知/未検知: ヒステリシス、複数ビーコン、退出時の二重確認（操作/退出QR）。
- 省電力: スキャンDuty制御、検知後の間欠化、モーション連動開始/停止。
- ネットワーク断: 端末はローカルで確実に停止。サーバ復帰後にテレメトリ/制御を同期。

---

## 11. 故障・電池交換忘れ対策（フェイルセーフ運用）

目的: Privacy Zoneの「取りこぼし」をゼロに近づけ、電池切れ・故障時も安全側（録画しない）に倒す。

### 11.1 設計・設置の冗長化
- N+1冗長: ゾーン入口に物理的に離して2台以上を設置（異常時はどちらか1台の受信で停止）。
- フェイルクローズ: いったん停止したら最小滞在時間（例: 2分）を下回る復帰を無効化。ビーコンが消えても直ぐには再開しない。
- 退出二重確認: 退出はRSSI低下＋ユーザー操作（ボタン/退出QR）のAND条件にする。

### 11.2 監視・アラート（サーバ側）
- Beacon Registry: `beacon_id, zone_id, install_date, expected_replace_by` をDB管理。
- Last Seen監視: 定点スキャナ（小型BLEゲートウェイやRaspberry Pi等）を各ゾーン近傍に1台設置し、
  - 直近`last_seen_at`のしきい値超過（例: 24時間）で「未検知」警告
  - Eddystone‑TLM対応機は電圧`vbatt`がしきい値（例: <2.7V）で「電池低下」警告
- アラート配信: 週次サマリー＋しきい値到達で即時通知（Email/Slack）。

### 11.3 点検・交換プロセス（運用）
- 計画交換: 電池寿命の70–80%時点で前倒し交換（年1回など固定スケジュール）。
- 台帳管理: 設置ID/設置日/電池種/交換予定日/交換実績を管理。設置個体には屋内側に小ラベル。
- 現場セルフチェック: KMPアプリに「ビーコン診断」画面を用意し、保全担当が巡回時にRSSI/IDをスキャン→サーバへ点検記録をPOST。
- 予備在庫: 予備ビーコンを各拠点に常備（初期設定済み・ID発行済み）。故障時は即日交換。

### 11.4 THINKLET側フェイルセーフ
- 検知失敗時の手順提示: ビーコンが見つからない状態でトイレ付近の既知BSSIDやジオフェンスに入ると、端末が音声で「プライバシーQRをスキャンしてください」と案内し、手動停止を促す。
- ステータス可視化: 端末LED/音/振動で「プライバシーモード中」を明示。未検知のまま入室方向に移動した場合は警告フィードバック。
- ログと監査: 「予定ゾーンでビーコン未検知」のイベントをtelemetryに記録し、月次に拾い上げて是正。

### 11.5 ハードウェア選定のポイント
- TLM（Telemetry）対応モデルを優先（電圧・温度・カウンタ配信）。
- 電池は大容量（CR2477等）・交換容易な筐体。防滴カバーと盗難防止固定具を利用。
- 広告間隔は200–500ms、送信出力は最小限で安定RSSIが得られるよう現場チューニング。

### 11.6 想定故障モードと対応
- 完全沈黙（電池切れ/故障）: 冗長機が稼働→定点スキャナで未検知警告→交換。
- 出力低下/不安定: RSSIの分散が急増→運用アラート→現場診断→交換。
- 設置位置変更/落下: RSSIプロファイルの急変→異常通知→現地是正。

---

## 10. 参考・関連ドキュメント
- THINKLET仕様: `docs/9000_調査/0010_THINKLET/THINKLET資料.md`（Bluetooth 4.2/BLE 搭載）
- API: `docs/0300_設計_アプローチ1/0304_API設計.md`（/api/v1/uplink/control, /telemetry, VMS再生制御）
- システム方針: `docs/0300_設計_アプローチ1/0300_システム基本設計.md`（WHEP単一路インジェスト、RBAC、監査）
