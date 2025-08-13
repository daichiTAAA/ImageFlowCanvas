# ImageFlowCanvas QRコードテストデータ

このディレクトリには、ImageFlowCanvas AndroidアプリのQRスキャン機能をテストするためのQRコード画像が含まれています。

## 生成日時
2025年8月13日

## テストパターン

### ✅ 成功パターン (正常に製品情報が表示される)

#### 1. JSON形式 - 成功パターン1
**ファイル**: `qr_test_json_success_1.png`
**データ**:
```json
{
  "workOrderId": "WORK001",
  "instructionId": "INST001", 
  "productType": "TYPE-A",
  "machineNumber": "MACHINE-123",
  "productionDate": "2024-01-15",
  "monthlySequence": 1
}
```
**期待される表示**:
- 製品タイプ: TYPE-A
- 機番: MACHINE-123
- 指図番号: WORK001
- 指示番号: INST001

#### 2. JSON形式 - 成功パターン2
**ファイル**: `qr_test_json_success_2.png`
**データ**:
```json
{
  "workOrderId": "WORK002",
  "instructionId": "INST002",
  "productType": "TYPE-B", 
  "machineNumber": "MACHINE-456",
  "productionDate": "2024-02-20",
  "monthlySequence": 5
}
```
**期待される表示**:
- 製品タイプ: TYPE-B
- 機番: MACHINE-456
- 指図番号: WORK002
- 指示番号: INST002

#### 3. CSV形式 - 成功パターン1
**ファイル**: `qr_test_csv_success_1.png`
**データ**: `WORK001,INST001,TYPE-A,MACHINE-123,2024-01-15,1`
**期待される表示**:
- 製品タイプ: TYPE-A
- 機番: MACHINE-123
- 指図番号: WORK001
- 指示番号: INST001

#### 4. CSV形式 - 成功パターン2
**ファイル**: `qr_test_csv_success_2.png`
**データ**: `WORK003,INST003,TYPE-C,MACHINE-789,2024-03-10,12`
**期待される表示**:
- 製品タイプ: TYPE-C
- 機番: MACHINE-789
- 指図番号: WORK003
- 指示番号: INST003

#### 5. 現在日付での製品情報
**ファイル**: `qr_test_current_date.png`
**データ**:
```json
{
  "workOrderId": "WORK2025001",
  "instructionId": "INST2025001",
  "productType": "TYPE-CURRENT",
  "machineNumber": "MACHINE-2025",
  "productionDate": "2025-08-13",
  "monthlySequence": 13
}
```
**期待される表示**:
- 製品タイプ: TYPE-CURRENT
- 機番: MACHINE-2025
- 指図番号: WORK2025001
- 指示番号: INST2025001

### ❌ エラーパターン (エラーメッセージが表示される)

#### 1. 必須項目不足エラー
**ファイル**: `qr_test_error_missing_fields.png`
**データ**:
```json
{
  "workOrderId": "",
  "instructionId": "INST004",
  "productType": "TYPE-D",
  "machineNumber": "",
  "productionDate": "2024-04-01",
  "monthlySequence": 3
}
```
**期待されるエラー**: "指図番号は必須です" または "機番は必須です"

#### 2. 不正な日付形式エラー
**ファイル**: `qr_test_error_invalid_date.png`
**データ**:
```json
{
  "workOrderId": "WORK005",
  "instructionId": "INST005",
  "productType": "TYPE-E", 
  "machineNumber": "MACHINE-999",
  "productionDate": "24/05/15",
  "monthlySequence": 7
}
```
**期待されるエラー**: "生産年月日の形式が正しくありません (YYYY-MM-DD)"

#### 3. 完全に不正なデータ形式
**ファイル**: `qr_test_error_invalid_format.png`
**データ**: `this is not valid qr data format`
**期待されるエラー**: "QRコードの形式が正しくありません" または類似のメッセージ

## 使用方法

1. **Androidデバイスでアプリを起動**
   ```bash
   # プロジェクトルートで実行
   cd kmp
   ./gradlew installDebug
   adb shell am start -n com.imageflow.kmp.app/.MainActivity
   ```

2. **QRスキャン画面を開く**
   - アプリ内のQRスキャン機能を起動

3. **QRコード画像をスキャン**
   - このディレクトリの画像ファイルをAndroidデバイスのカメラでスキャン
   - または画像を別のデバイスに表示してスキャン

4. **結果を確認**
   - 成功パターン: 製品情報が正しく表示される
   - エラーパターン: 適切なエラーメッセージが表示される

## 製品情報の表示フィールド

アプリで表示される項目:
- **製品タイプ** (`productType`)
- **機番** (`machineNumber`) 
- **指図番号** (`workOrderId`)
- **指示番号** (`instructionId`)

## テストのポイント

### 正常系テスト
- [ ] JSON形式のQRコードが正しく読み取れる
- [ ] CSV形式のQRコードが正しく読み取れる
- [ ] すべての必須フィールドが正しく表示される
- [ ] "この製品を選択"ボタンが機能する
- [ ] "再スキャン"ボタンが機能する

### 異常系テスト
- [ ] 必須項目が不足している場合にエラーが表示される
- [ ] 不正な日付形式でエラーが表示される
- [ ] 完全に不正なデータでエラーが表示される
- [ ] エラー時に"再試行"ボタンが機能する

### UI/UXテスト
- [ ] エラーメッセージが分かりやすく表示される
- [ ] 成功/エラー時のアイコンが適切に表示される
- [ ] ライト(トーチ)の切り替えが正常に動作する
- [ ] 手動入力ボタンが機能する

## トラブルシューティング

### QRコードが読み取れない場合
1. カメラの権限が許可されているか確認
2. 十分な明るさがあるか確認
3. QRコードがフレーム内に収まっているか確認
4. カメラのピントが合っているか確認

### アプリがクラッシュする場合
1. ログを確認: `adb logcat | grep ImageFlow`
2. デバッグビルドで詳細なエラー情報を確認
3. 必要に応じてアプリを再起動

## 参考情報

- QRコードデコーダー実装: `/kmp/shared/src/commonMain/kotlin/com/imageflow/kmp/qr/BarcodeDecoder.kt`
- Androidカメラ実装: `/kmp/androidApp/src/main/kotlin/com/imageflow/kmp/app/QrScanningAndroid.kt`
- 共通UI実装: `/kmp/shared/src/commonMain/kotlin/com/imageflow/kmp/ui/mobile/QrScanningScreen.kt`
