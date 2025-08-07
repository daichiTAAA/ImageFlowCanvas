import React, { useState, useRef } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  Paper,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import {
  QrCodeScanner as QrIcon,
  ExpandMore,
  KeyboardArrowRight,
} from "@mui/icons-material";
import { invoke } from "@tauri-apps/api/core";
import Webcam from "react-webcam";
import jsQR from "jsqr";

interface QRCodeScannerProps {
  onNext: (data: any) => void;
}

export const QRCodeScanner: React.FC<QRCodeScannerProps> = ({ onNext }) => {
  const [scanning, setScanning] = useState(false);
  const [qrValue, setQrValue] = useState("");
  const [manualInput, setManualInput] = useState("");
  const [error, setError] = useState("");
  const [useCamera, setUseCamera] = useState(false);
  const [inputError, setInputError] = useState(""); // 入力検証用のエラー
  const [isManualInput, setIsManualInput] = useState(false); // 手動入力かどうかを追跡
  const webcamRef = useRef<Webcam>(null);
  const scanIntervalRef = useRef<number | null>(null);

  // 入力内容の検証
  const validateInput = (value: string): string => {
    if (!value.trim()) {
      return "";
    }

    if (value.length < 3) {
      return "製品IDは3文字以上で入力してください";
    }

    if (value.length > 100) {
      return "製品IDは100文字以内で入力してください";
    }

    const validPattern = /^[A-Za-z0-9_-]+$/;
    if (!validPattern.test(value)) {
      return "英数字、アンダースコア(_)、ハイフン(-)のみ使用できます";
    }

    // バックエンドが期待する形式をチェック
    if (!value.startsWith("{")) {
      // JSON形式でない場合
      const parts = value.split("_");
      if (parts.length < 2) {
        return "製品IDは 'PRODUCT_BATCH' の形式で入力してください（例: PRODUCT_001_BATCH_001）";
      }
    }

    return "";
  };

  // 入力変更時の処理
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setManualInput(value);
    setInputError(validateInput(value));
  };

  const handleScanCamera = async () => {
    setScanning(true);
    setError("");
    setQrValue(""); // 既存の成功メッセージをクリア
    setIsManualInput(false); // QRコードスキャンモードに設定
    setUseCamera(true);

    // Start continuous scanning
    scanIntervalRef.current = setInterval(() => {
      const imageSrc = webcamRef.current?.getScreenshot();
      if (imageSrc) {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        const img = new Image();

        img.onload = () => {
          canvas.width = img.width;
          canvas.height = img.height;
          ctx?.drawImage(img, 0, 0);

          const imageData = ctx?.getImageData(
            0,
            0,
            canvas.width,
            canvas.height
          );
          if (imageData) {
            const code = jsQR(
              imageData.data,
              imageData.width,
              imageData.height
            );
            if (code) {
              handleQRCodeDetected(code.data);
            }
          }
        };
        img.src = imageSrc;
      }
    }, 500);
  };

  const handleQRCodeDetected = async (qrData: string) => {
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
    }
    setUseCamera(false);
    setScanning(false);

    // QRコードとして読み取った値は常に表示
    setQrValue(qrData);
    setIsManualInput(false); // QRコードスキャンによる入力
    console.log("QRコード検出:", qrData);

    try {
      // Parse QR data using Tauri backend
      const target = (await invoke("parse_qr_data", { qrData })) as any;
      setError(""); // エラーをクリア
      onNext(target);
    } catch (err) {
      const errorMessage =
        (err as Error).message || String(err) || "不明なエラー";
      console.error("QRコード解析エラー:", err);
      setError("QRコードの解析に失敗しました: " + errorMessage);
      // エラー時でもqrValueは保持（読み取った値を表示）
    }
  };

  const handleManualSubmit = async () => {
    const trimmedInput = manualInput.trim();

    if (!trimmedInput) {
      setError("製品IDを入力してください");
      return;
    }

    // リアルタイム検証でチェック済みなので、追加チェックは不要
    const validationError = validateInput(trimmedInput);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError("");
    // 入力された値は常に表示
    setQrValue(trimmedInput);
    setIsManualInput(true); // 手動入力による入力

    try {
      const target = (await invoke("parse_qr_data", {
        qrData: trimmedInput,
      })) as any;
      onNext(target);
    } catch (err) {
      const errorMessage =
        (err as Error).message || String(err) || "不明なエラー";
      console.error("製品ID解析エラー:", err);
      setError("製品IDの解析に失敗しました: " + errorMessage);
      // エラー時でもqrValueは保持（入力された値を表示）
    }
  };

  const stopScanning = () => {
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
    }
    setUseCamera(false);
    setScanning(false);
    setError(""); // エラーメッセージをクリア
    setQrValue(""); // 成功メッセージもクリア
    setIsManualInput(false); // フラグもリセット
  };

  return (
    <Box sx={{ width: "100%" }}>
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          QRコードスキャン機能
        </Typography>

        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {!useCamera ? (
            <>
              <Button
                variant="outlined"
                size="large"
                startIcon={<QrIcon />}
                onClick={handleScanCamera}
                disabled={scanning}
                sx={{ py: 2 }}
              >
                QRコードをスキャン
              </Button>
            </>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <Typography variant="body1">
                QRコードをカメラに向けてください
              </Typography>
              <Box sx={{ position: "relative", width: "100%", maxWidth: 400 }}>
                <Webcam
                  ref={webcamRef}
                  audio={false}
                  width="100%"
                  screenshotFormat="image/jpeg"
                  videoConstraints={{ facingMode: "environment" }}
                />
                <Box
                  sx={{
                    position: "absolute",
                    top: "25%",
                    left: "25%",
                    width: "50%",
                    height: "50%",
                    border: "2px solid #1976d2",
                    borderRadius: 2,
                    pointerEvents: "none",
                  }}
                />
              </Box>
              <Button variant="outlined" onClick={stopScanning}>
                スキャンを停止
              </Button>
            </Box>
          )}

          {qrValue && (
            <Alert severity="success">
              {isManualInput
                ? `製品ID入力完了: ${qrValue}`
                : `QRコード読み取り成功: ${qrValue}`}
            </Alert>
          )}

          {error && <Alert severity="error">{error}</Alert>}
        </Box>
      </Paper>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography>手動入力オプション</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <TextField
              label="製品ID"
              value={manualInput}
              onChange={handleInputChange}
              placeholder="例: PRODUCT_001_BATCH_20240126"
              fullWidth
              error={!!inputError}
              helperText={
                inputError ||
                "形式: PRODUCT_BATCH（アンダースコア区切り）または JSON形式"
              }
            />
            <Button
              variant="outlined"
              onClick={handleManualSubmit}
              endIcon={<KeyboardArrowRight />}
              disabled={!!inputError || !manualInput.trim()}
            >
              手動入力で進む
            </Button>
          </Box>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};
