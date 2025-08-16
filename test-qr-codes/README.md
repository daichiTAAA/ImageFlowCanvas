# ImageFlowCanvas QRコードテストデータ

このディレクトリには、ImageFlowCanvas AndroidアプリのQRスキャン機能をテストするためのQRコード画像が含まれています。

```bash
conda create -n qr python=3.12
conda activate qr
cd test-qr-codes
pip install -r requirements.txt
python test-qr-generator.py
```