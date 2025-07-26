import React, { useState, useRef } from 'react';
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
} from '@mui/material';
import {
  QrCodeScanner as QrIcon,
  ExpandMore,
  KeyboardArrowRight,
} from '@mui/icons-material';
import { invoke } from '@tauri-apps/api/core';
import Webcam from 'react-webcam';
import jsQR from 'jsqr';

interface QRCodeScannerProps {
  onNext: (data: any) => void;
}

export const QRCodeScanner: React.FC<QRCodeScannerProps> = ({ onNext }) => {
  const [scanning, setScanning] = useState(false);
  const [qrValue, setQrValue] = useState('');
  const [manualInput, setManualInput] = useState('');
  const [error, setError] = useState('');
  const [useCamera, setUseCamera] = useState(false);
  const webcamRef = useRef<Webcam>(null);
  const scanIntervalRef = useRef<number | null>(null);

  const handleScanCamera = async () => {
    setScanning(true);
    setError('');
    setUseCamera(true);

    // Start continuous scanning
    scanIntervalRef.current = setInterval(() => {
      const imageSrc = webcamRef.current?.getScreenshot();
      if (imageSrc) {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        img.onload = () => {
          canvas.width = img.width;
          canvas.height = img.height;
          ctx?.drawImage(img, 0, 0);
          
          const imageData = ctx?.getImageData(0, 0, canvas.width, canvas.height);
          if (imageData) {
            const code = jsQR(imageData.data, imageData.width, imageData.height);
            if (code) {
              handleQRCodeDetected(code.data);
            }
          }
        };
        img.src = imageSrc;
      }
    }, 500);
  };

  const handleScanTauri = async () => {
    setScanning(true);
    setError('');
    
    try {
      // Use Tauri barcode scanner plugin
      const result = await invoke('scan_qr_code_camera') as { data: string; format: string; confidence: number };
      handleQRCodeDetected(result.data);
    } catch (err) {
      setError('QRコードの読み取りに失敗しました: ' + (err as Error).message);
      setScanning(false);
    }
  };

  const handleQRCodeDetected = async (qrData: string) => {
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
    }
    setUseCamera(false);
    setScanning(false);
    setQrValue(qrData);

    try {
      // Parse QR data using Tauri backend
      const target = await invoke('parse_qr_data', { qrData }) as any;
      onNext(target);
    } catch (err) {
      setError('QRコードの解析に失敗しました: ' + (err as Error).message);
    }
  };

  const handleManualSubmit = async () => {
    if (!manualInput.trim()) {
      setError('製品IDを入力してください');
      return;
    }
    
    setError('');
    
    try {
      const target = await invoke('parse_qr_data', { qrData: manualInput }) as any;
      onNext(target);
    } catch (err) {
      setError('製品IDの解析に失敗しました: ' + (err as Error).message);
    }
  };

  const stopScanning = () => {
    if (scanIntervalRef.current) {
      clearInterval(scanIntervalRef.current);
    }
    setUseCamera(false);
    setScanning(false);
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          QRコードスキャン機能
        </Typography>
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {!useCamera ? (
            <>
              <Button
                variant="contained"
                size="large"
                startIcon={scanning ? <CircularProgress size={20} color="inherit" /> : <QrIcon />}
                onClick={handleScanTauri}
                disabled={scanning}
                sx={{ py: 2 }}
              >
                {scanning ? 'スキャン中...' : 'QRコードをスキャン (Tauri)'}
              </Button>

              <Button
                variant="outlined"
                size="large"
                startIcon={<QrIcon />}
                onClick={handleScanCamera}
                disabled={scanning}
                sx={{ py: 2 }}
              >
                カメラでスキャン
              </Button>
            </>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Typography variant="body1">
                QRコードをカメラに向けてください
              </Typography>
              <Box sx={{ position: 'relative', width: '100%', maxWidth: 400 }}>
                <Webcam
                  ref={webcamRef}
                  audio={false}
                  width="100%"
                  screenshotFormat="image/jpeg"
                  videoConstraints={{ facingMode: 'environment' }}
                />
                <Box
                  sx={{
                    position: 'absolute',
                    top: '25%',
                    left: '25%',
                    width: '50%',
                    height: '50%',
                    border: '2px solid #1976d2',
                    borderRadius: 2,
                    pointerEvents: 'none',
                  }}
                />
              </Box>
              <Button
                variant="outlined"
                onClick={stopScanning}
              >
                スキャンを停止
              </Button>
            </Box>
          )}

          {qrValue && (
            <Alert severity="success">
              QRコード読み取り成功: {qrValue}
            </Alert>
          )}

          {error && (
            <Alert severity="error">
              {error}
            </Alert>
          )}
        </Box>
      </Paper>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Typography>手動入力オプション</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="製品ID"
              value={manualInput}
              onChange={(e) => setManualInput(e.target.value)}
              placeholder="例: PRODUCT_001_BATCH_20240126"
              fullWidth
            />
            <Button
              variant="outlined"
              onClick={handleManualSubmit}
              endIcon={<KeyboardArrowRight />}
            >
              手動入力で進む
            </Button>
          </Box>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};