#!/usr/bin/env python3
"""
ImageFlowCanvas QRコードテストデータ生成スクリプト
アプリのQRスキャン機能をテストするためのQRコード画像を生成します。
"""

import qrcode
import json
from PIL import Image, ImageDraw, ImageFont
import os


def create_qr_code(data, filename, title=""):
    """QRコードを生成して画像ファイルとして保存"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    # QRコード画像を作成
    qr_img = qr.make_image(fill_color="black", back_color="white")

    # タイトルがない場合は単純に保存
    if not title:
        qr_img.save(filename)
        print(f"QRコード画像を保存しました: {filename}")
        print(f"データ: {data}")
        print()
        return

    # 一時的にQRコードを保存してからPILで読み込み
    temp_filename = filename.replace(".png", "_temp.png")
    qr_img.save(temp_filename)

    # PILで読み込み
    qr_pil = Image.open(temp_filename)

    img_width = qr_pil.size[0]
    img_height = qr_pil.size[1] + 60  # タイトル用のスペース

    # 新しい画像を作成
    final_img = Image.new("RGB", (img_width, img_height), "white")

    # QRコードを貼り付け
    final_img.paste(qr_pil, (0, 0))

    # タイトルを追加
    draw = ImageDraw.Draw(final_img)
    try:
        # システムフォントを使用
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except:
        # フォントが見つからない場合はデフォルトを使用
        font = ImageFont.load_default()

    # テキストのサイズを取得
    text_bbox = draw.textbbox((0, 0), title, font=font)
    text_width = text_bbox[2] - text_bbox[0]

    # テキストを中央に配置
    text_x = (img_width - text_width) // 2
    text_y = qr_pil.size[1] + 10

    draw.text((text_x, text_y), title, fill="black", font=font)

    final_img.save(filename)

    # 一時ファイルを削除
    os.remove(temp_filename)

    print(f"QRコード画像を保存しました: {filename}")
    print(f"データ: {data}")
    print()


def main():
    # テスト用QRコードデータを準備
    test_data = [
        {
            "title": "JSON形式 - 成功パターン1",
            "data": json.dumps(
                {
                    "workOrderId": "WORK001",
                    "instructionId": "INST001",
                    "productType": "TYPE-A",
                    "machineNumber": "MACHINE-123",
                    "productionDate": "2024-01-15",
                    "monthlySequence": 1,
                }
            ),
            "filename": "qr_test_json_success_1.png",
        },
        {
            "title": "JSON形式 - 成功パターン2",
            "data": json.dumps(
                {
                    "workOrderId": "WORK002",
                    "instructionId": "INST002",
                    "productType": "TYPE-B",
                    "machineNumber": "MACHINE-456",
                    "productionDate": "2024-02-20",
                    "monthlySequence": 5,
                }
            ),
            "filename": "qr_test_json_success_2.png",
        },
        {
            "title": "CSV形式 - 成功パターン1",
            "data": "WORK001,INST001,TYPE-A,MACHINE-123,2024-01-15,1",
            "filename": "qr_test_csv_success_1.png",
        },
        {
            "title": "CSV形式 - 成功パターン2",
            "data": "WORK003,INST003,TYPE-C,MACHINE-789,2024-03-10,12",
            "filename": "qr_test_csv_success_2.png",
        },
        {
            "title": "エラーパターン - 必須項目不足",
            "data": json.dumps(
                {
                    "workOrderId": "",
                    "instructionId": "INST004",
                    "productType": "TYPE-D",
                    "machineNumber": "",
                    "productionDate": "2024-04-01",
                    "monthlySequence": 3,
                }
            ),
            "filename": "qr_test_error_missing_fields.png",
        },
        {
            "title": "エラーパターン - 不正な日付形式",
            "data": json.dumps(
                {
                    "workOrderId": "WORK005",
                    "instructionId": "INST005",
                    "productType": "TYPE-E",
                    "machineNumber": "MACHINE-999",
                    "productionDate": "24/05/15",  # 不正な日付形式
                    "monthlySequence": 7,
                }
            ),
            "filename": "qr_test_error_invalid_date.png",
        },
        {
            "title": "エラーパターン - 完全に不正なデータ",
            "data": "this is not valid qr data format",
            "filename": "qr_test_error_invalid_format.png",
        },
        {
            "title": "現在の日付での製品情報",
            "data": json.dumps(
                {
                    "workOrderId": "WORK2025001",
                    "instructionId": "INST2025001",
                    "productType": "TYPE-CURRENT",
                    "machineNumber": "MACHINE-2025",
                    "productionDate": "2025-08-13",
                    "monthlySequence": 13,
                }
            ),
            "filename": "qr_test_current_date.png",
        },
    ]

    # 出力ディレクトリを作成
    output_dir = "test-qr-codes"
    os.makedirs(output_dir, exist_ok=True)

    print("ImageFlowCanvas QRコードテストデータ生成中...")
    print("=" * 60)

    # 各テストデータのQRコードを生成
    for item in test_data:
        filepath = os.path.join(output_dir, item["filename"])
        create_qr_code(item["data"], filepath, item["title"])

    print("=" * 60)
    print(f"すべてのQRコード画像が {output_dir}/ ディレクトリに保存されました。")
    print("\n使用方法:")
    print("1. Androidデバイスでアプリを起動")
    print("2. QRスキャン画面を開く")
    print("3. 生成されたQRコード画像をスキャンしてテスト")
    print("\n成功パターン: 製品情報が正しく表示される")
    print("エラーパターン: エラーメッセージが表示される")


if __name__ == "__main__":
    main()
