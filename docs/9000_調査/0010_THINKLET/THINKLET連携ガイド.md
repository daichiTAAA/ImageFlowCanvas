# THINKLET 一人称映像 連携ガイド（MediaMTX + Web + Backend + KMP）

本ガイドは、THINKLET からの一人称映像を MediaMTX に取り込み（WHIP/RTMP）、HLS で表示・録画し、Web UI で視聴・録画一覧を行うまでの最小構成を説明します。

## 構成

- MediaMTX（`deploy/compose` で起動）
  - HLS: `:8888`
  - WebRTC/WHIP/WHEP: `:8889`
  - RTMP: `:1935`
  - Control API: `:9997`
- Backend（FastAPI）
  - MediaMTX API をプロキシ/整形するエンドポイント
  - `GET /v1/uplink/streams`、`GET /v1/uplink/recordings/{path}`
- Web UI（React）
  - `http://localhost:3000/thinklet` で HLS 再生（hls.js）
  - Online Streams 一覧から選択 or HLS URL 手入力で再生
- KMP（Android/THINKLET）
  - `ThinkletStreamingScreen` のスタブを追加（WHIP/RTMP の URL 入力 UI）。
  - 実配信は RTMP または WHIP クライアント実装の追加が必要です。

## 起動

1) 事前ビルド（オプション）

```
./scripts/build_services.sh
```

2) Compose 起動

```
./scripts/run-compose.sh up
# 開発（Web のホットリロード）：
./scripts/run-compose.sh dev
```

アクセス:
- Web UI: http://localhost:3000
- MediaMTX HLS: http://localhost:8888/{path}/index.m3u8
- MediaMTX API: http://localhost:9997/v3/paths/list

## パス命名と録画

- THINKLET 配信用のストリームパスは `uplink/{deviceId}` とします。
- `mediamtx/mediamtx.yml` で `~^uplink/.+$` を録画有効に設定済み。
  - 録画先: コンテナ内 `/recordings/%path/%Y-%m-%d_%H-%M-%S-%f`
  - Compose ボリューム `mediamtx_recordings` で永続化

## THINKLET からの配信（2 つの選択肢）

1) WHIP（推奨・低遅延）
- 送信先: `http://<サーバ>:8889/whip/uplink/<deviceId>`
- Android の WebRTC/WHIP クライアント実装が必要（libwebrtc + WHIP シグナリング）

2) RTMP（簡便・ライブラリ豊富）
- 送信先: `rtmp://<サーバ>:1935/uplink/<deviceId>`
- 例ライブラリ: `com.github.pedroSG94.rtmp-rtsp-stream-client-java`

KMP Android のスタブ（`ThinkletStreamingScreen`）に URL 入力/開始/停止 UI を追加済み。ライブラリ導入後に実処理を実装してください。

## Web での視聴・録画

- Live 再生: Web UI の「カメラ 映像」ページ（/thinklet）で deviceId を選択し再生
- 録画一覧: Backend の `GET /api/uplink/recordings/{path}` を利用（UI への組み込みは最小）

## Backend API まとめ

- `GET /api/uplink/streams` → MediaMTX `/v3/paths/list` の整形（`uplink/*` のみ）
- `GET /api/uplink/recordings/{path}` → MediaMTX `/v3/recordings/get/{name}`

## 注意

- 本構成は最小機能実装です。認証・認可、保存ポリシー、録画管理 UI、WHIP 実装は段階的に拡張してください。
- 既存のリアルタイム AI パイプライン（WebSocket→gRPC）は従来どおり利用可。THINKLET の配信は MediaMTX 経由で視聴/録画を担い、推論連携は別途計画に沿って拡張してください。

