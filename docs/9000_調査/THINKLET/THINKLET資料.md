# THINKLET®︎ デバイス情報

> **公式サイト**: https://mimi.fairydevices.jp/technology/device/thinklet/

## 製品概要

THINKLET®︎は、LTE / Wi-Fi 搭載のウェアラブルデバイスです。mimi® の開発で培った AI 技術・ソフトウェア技術を最大限活かすことができるように独自に設計、人間の肩に乗って人間を助けてくれる「妖精（フェアリー）」のような AI を生み出したいという当社名に込められた想いを体現するデバイスとして開発されました。

### 主な特徴

- **受賞歴**: THINKLET デバイスを利用した LINKLET サービスは、CES イノベーションアワード三冠を始め、各賞を受賞
- **高性能マイク**: ５つのマイクを搭載し、XFE が動作。建設・保守現場やプラント等の高騒音環境下でもクリアな集音を実現
- **広角カメラ**: １つの広角カメラを搭載し、装着者の視野全体を撮影してリアルタイムに遠隔地に送信
- **安定性**: 肩掛けの位置に装着されるため、視線カメラと比較して大幅に動画像が安定
- **ハンズフリー**: 装着者の「体験」を遠隔地と共有することが可能

### OS・開発環境

- **OS**: AOSP（Android Open Source Project）ベースの独自OS「Fairy OS」
- **SDK**: ハードウェア機能を制御するためのソフトウェアをSDKとして提供
- **互換性**: 一般の Android 向けアプリケーションが動作可能（一部技術的制約あり）

> **事業**: THINKLET®︎ は、当社のコネクテッドワーカー事業で取り扱っています。

## THINKLET®︎ の音声機能

THINKLET®︎ は他のウェアラブルデバイスにはない特徴的な音声機能を備えています。

> ⚠️ **注意**: 一部の機能はオプション機能となり別途ライセンスが必要となります。

### 1. ワイドダイナミックレンジマイク

#### 背景課題
プラントや高騒音な現場環境では、環境騒音 80db 以上の現場が数多くあります。このような現場で装着者が発話する場合、周りが煩いため自分の声も大きくなるという傾向があります。この傾向は学術的には**「ロンバード効果」**として知られている現象です。

#### 技術的解決策
このとき、マイクで観測される音量は 100db を超える場合があり、通常のマイク系では、入力が飽和してしまい音が割れてしまいます。音が割れてしまうと一切の信号処理ができなくなるだけでなく、音声認識性能が極端に悪化します。

**THINKLET®︎ の優位性**:
- マイク系が **24bit 相当のワイドレンジ** を持つ
- 大音量からささやき声のような小さな音量まで適切に集音可能
- 現場環境で利用する音声デバイスの大前提となるハードウェア機能

### 2. マイクアレイ

- **5ch マイクアレイ** を内蔵
- **世界初**: 5ch 以上のマイク素子を装備するウェアラブルデバイス（※2022年現在、当社調べ）
- **XFE 技術** をマイクアレイ上に適用することで、あらゆる環境で最適な録音を実現

> ⚠️ **注意**: XFE ライブラリは開発機には搭載されていません。別途ライセンスが必要です。

### 3. 装着者の声のみを集音する機能

#### ハードウェア設計
THINKLET に搭載されているマイクは、マイク単体でも装着者の音声をより拾いやすくなるように作られています。

#### XFE ライブラリの機能
- 周辺の環境騒音を大幅に低減
- 装着者の声をクリアに集音
- **実測データ**: THINKLET®︎ の周囲360度から音声を出している状態で、XFE 技術により装着者の方向以外の音声を波形上はほぼ見えないレベルまで抑制

### 4. 対面話者の声のみを集音する機能

#### 指向性制御
XFE 技術では、指向性をソフトウェア的に制御することが可能です。

**可能な指向性パターン**:
- 装着者の方向のみ
- 装着者の真正面（対面話者の方向）
- **同時形成**: ２つの指向性を同時に形成し、装着者の音声と対面話者の音声を独立に分離して集音

**活用例**: 対面接客業務の DX などに応用可能

### 5. 風切り音抑制機能

#### 課題
THINKLET®︎ は屋外で使われることも多く、強風が吹いている環境においては、ハードウェア的に防ぎきることができない風切り音が入ってしまう場合があります。このような風切り音は音量が大きいため、ウェブ会議等で送られる場合、極めて耳障りです。

#### 解決策
- **ハードウェア**: マイク配置の工夫によって風切り音が入りにくい設計
- **ソフトウェア**: XFE 技術によって風切り音を検出し、聞こえないレベルまで強力に抑制

#### 制限事項
副作用として、発話と風切り音が同時に重なってしまった場合には音声側も多少欠損する場合がありますが、全体として風切り音が抑制できることによって、会話品質を大きく向上させることにつながります。

### 6. スピーカー・音声出力

#### 内蔵スピーカー
- **1ch スピーカー** を背面に搭載
- **ハンズフリー通話** が可能
- 人間の声が聞き取りやすいように調整されて出力

#### 外部音声出力
以下の環境では外部デバイスを利用可能:
- 外部に音声が漏れられない環境
- 周辺騒音が大きすぎる環境

**対応デバイス**:
- Bluetooth イヤホン
- 有線イヤホン（オーディオミニジャック 4極対応）

---

## ハードウェア仕様

### システム
| 項目           | 仕様                            |
| -------------- | ------------------------------- |
| **OS**         | Fairy OS（AOSP ベースの独自OS） |
| **CPU**        | クアルコム Snapdragon シリーズ  |
| **RAM**        | 4GB                             |
| **ストレージ** | 64GB+128GB（オンボードSDXC）    |

### カメラ
| 項目                   | 仕様               |
| ---------------------- | ------------------ |
| **解像度**             | 8MP                |
| **視野角（横広角機）** | 水平120度×垂直90度 |
| **視野角（縦広角機）** | 水平90度×垂直120度 |

### 音声
| 項目         | 仕様                                          |
| ------------ | --------------------------------------------- |
| **音声入力** | 48kHz/24bit相当、5ch                          |
| **音声出力** | 内蔵スピーカー、オーディオミニジャック（4極） |

### 通信
| 項目          | 仕様                  |
| ------------- | --------------------- |
| **4G/LTE**    | Band 1/3/8/9/18/19/41 |
| **WCDMA**     | Band 1/3/8/9/19       |
| **Wi-Fi**     | 2.4GHz/5GHz           |
| **Bluetooth** | Bluetooth 4.2, BLE    |
| **SIM**       | ナノSIM × 1           |

### センサー・その他
| 項目         | 仕様                                                                                |
| ------------ | ----------------------------------------------------------------------------------- |
| **GNSS**     | GPS、GLONASS、QZSS 他                                                               |
| **センサー** | 9軸モーションセンサー（地磁気、加速度、角速度）、近接センサー、ジェスチャーセンサー |
| **ボタン**   | 電源ボタン、ファンクションボタン×3                                                  |

### 物理仕様・環境性能
| 項目               | 仕様                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------- |
| **重量**           | 約170g                                                                                       |
| **防塵性能**       | IP5X相当（粉塵が内部に侵入することを防止。若干の粉塵の侵入があっても正常な運転を阻害しない） |
| **防水性能**       | IPX4（飛沫に対する保護。いかなる方向からの水の飛沫によっても有害な影響をうけない）           |
| **バッテリー容量** | 1350 mAh                                                                                     |
| **満充電完了時間** | 約90分                                                                                       |

---

## 価格情報

| 製品                                       | 価格（税抜） | 価格（税込） |
| ------------------------------------------ | ------------ | ------------ |
| **THINKLET開発機本体**                     | ￥198,000     | ￥217,800     |
| **THINKLET開発機本体（研究教育機関向け）** | ￥99,800      | ￥109,780     |

---

## カメラタイプについて

### 横広角機・縦広角機の違い

THINKLETは、身につけた状態でカメラが横広角になるように内蔵されたタイプと、縦広角になるように内蔵されたタイプがあります。

| タイプ       | 撮影映像   | 視野角             |
| ------------ | ---------- | ------------------ |
| **横広角機** | 横長の映像 | 水平120度×垂直90度 |
| **縦広角機** | 縦長の映像 | 水平90度×垂直120度 |

> ⚠️ **重要**: ご購入時にどちらのタイプをご希望かをお選びいただく必要があります。**ご購入後の交換はできません**のでご注意ください。

### 開発機について

THINKLET開発機は、お客様がAndroid SDKを利用したソフトウェアを開発しTHINKLETに搭載して利用することを想定した開発者向けの製品です。

#### 注意事項
- **画面なし**: THINKLETには画面がないため、一般のスマートフォンのように画面をタッチ操作することはできません
- **技術的知識が必要**: 開発機の利用には技術的な知識が必要となります
- **事前確認推奨**: [THINKLET開発者ポータル](https://fairydevicesrd.github.io/thinklet.app.developer/) では、開発機の利用方法や開発方法をご紹介していますので、ご購入前にご確認ください

---

## 開発者向けリソース

### THINKLET開発者ポータル 

| リソース              | URL                                                                                                                  |
| --------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **開発者ポータル**    | [https://fairydevicesrd.github.io/thinklet.app.developer/](https://fairydevicesrd.github.io/thinklet.app.developer/) |
| **GitHub Repository** | [https://github.com/FairyDevicesRD](https://github.com/FairyDevicesRD)                                               |

### 開発環境・互換性

#### Androidとの互換性
THINKLETは、Android SDKと互換性があります。Androidアプリの開発資産をTHINKLETのアプリ開発に利用することができます。

#### THINKLET独自機能を提供するSDK
THINKLET固有の機能を利用できる専用SDKを提供しています。

**利用可能な機能例**:
- 5つのマイクを使った録音機能
- シャットダウン・再起動機能

#### 単体で通信
THINKLETは、Wi-Fiはもちろん、nanoSIM を使ったLTE通信が可能なセルラーモデルです。
- 他のデバイスや専用アプリ経由を使ったネットワーク接続は不要
- THINKLET単体で通信します

---

## THINKLETアプリケーション一覧

### オープンソースアプリケーション

THINKLETならではのアプリケーションをオープンソースとして公開しています。

| 説明                                                                                                   | リポジトリURL                                                                                                     | 最終更新   | ライセンス         |
| ------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | ---------- | ------------------ |
| **SDK for THINKLET application**                                                                       | [FairyDevicesRD/thinklet.app.sdk](https://github.com/FairyDevicesRD/thinklet.app.sdk)                             | 2024/12/9  | See Repository     |
| **THINKLETから直接 Youtube Live にストリーミング配信をする**                                           | [FairyDevicesRD/thinklet.squid.run](https://github.com/FairyDevicesRD/thinklet.squid.run)                         | 2024/12/10 | MIT License        |
| **THINKLET開発者向けのAdbを起動時に自動有効化するサンプル実装**                                        | [FairyDevicesRD/thinklet.app.adbRecovery](https://github.com/FairyDevicesRD/thinklet.app.adbRecovery)             | 2025/2/19  | MIT License        |
| **THINKLET/Androidのカメラを別デバイスのブラウザから視るサンプルアプリ**                               | [FairyDevicesRD/thinklet.camerax.vision](https://github.com/FairyDevicesRD/thinklet.camerax.vision)               | 2024/12/9  | MIT License        |
| **THINKLET向けCameraXフォーク**                                                                        | [FairyDevicesRD/thinklet.camerax](https://github.com/FairyDevicesRD/thinklet.camerax)                             | 2024/12/9  | Apache License 2.0 |
| **THINKLET向けCameraX のマイクプラグイン**                                                             | [FairyDevicesRD/thinklet.camerax.mic](https://github.com/FairyDevicesRD/thinklet.camerax.mic)                     | 2024/12/9  | Apache License 2.0 |
| **マルチマイク録画 + THINKLET Vision アプリ**                                                          | [FairyDevicesRD/thinklet.video.recorder](https://github.com/FairyDevicesRD/thinklet.video.recorder)               | 2025/2/25  | MIT License        |
| **THINKLET ライフログアプリ**                                                                          | [FairyDevicesRD/thinklet.app.lifelog](https://github.com/FairyDevicesRD/thinklet.app.lifelog)                     | 2025/2/25  | MIT License        |
| **近接センサーの反応有無をチェックするアプリ**                                                         | [FairyDevicesRD/thinklet.app.proximity-checker](https://github.com/FairyDevicesRD/thinklet.app.proximity-checker) | 2025/8/1   | MIT License        |
| **mimi(R) API Client for Kotlin**                                                                      | [FairyDevicesRD/mimi.client.kotlin](https://github.com/FairyDevicesRD/mimi.client.kotlin)                         | 2025/8/2   | MIT License        |
| **バーコードスキャンサンプルアプリ**                                                                   | [FairyDevicesRD/thinklet.barcode.reader.sample](https://github.com/FairyDevicesRD/thinklet.barcode.reader.sample) | 2025/7/28  | MIT License        |
| **THINKLET/Androidのカメラを別デバイスのブラウザから視るサンプルアプリの拡張（静止画撮影、写真一覧）** | [FairyDevicesRD/thinklet.app.photoviewer](https://github.com/FairyDevicesRD/thinklet.app.photoviewer)             | 2025/8/5   | MIT License        |

---

## サポート・ドキュメント

### THINKLET取扱説明書
> **URL**: [https://static-connected-worker.thinklet.fd.ai/support/ja/index.html](https://static-connected-worker.thinklet.fd.ai/support/ja/index.html)

---

## 脚注

※ 2022年現在、当社調べ  
※ The CES Innovation Awards are based upon descriptive materials submitted to the judges. CTA did not verify the accuracy of any submission or of any claims made and did not test the item to which the award was given.