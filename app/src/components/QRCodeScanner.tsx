import React, { useState } from 'react';
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

interface QRCodeScannerProps {
  onNext: (data: any) => void;
}

export const QRCodeScanner: React.FC<QRCodeScannerProps> = ({ onNext }) => {
  const [scanning, setScanning] = useState(false);
  const [qrValue, setQrValue] = useState('');
  const [manualInput, setManualInput] = useState('');
  const [error, setError] = useState('');

  const handleScan = async () => {
    setScanning(true);
    setError('');
    
    try {
      // Simulate QR code scanning (in real implementation, this would use camera)
      setTimeout(() => {
        const mockQRData = 'PRODUCT_001_BATCH_20240126';
        setQrValue(mockQRData);
        setScanning(false);
        
        // Parse QR data and proceed
        onNext({
          qrCode: mockQRData,
          productId: 'PRODUCT_001',
          batchId: 'BATCH_20240126',
          timestamp: new Date().toISOString(),
        });
      }, 2000);
    } catch (err) {
      setError('QRコードの読み取りに失敗しました');
      setScanning(false);
    }
  };

  const handleManualSubmit = () => {
    if (!manualInput.trim()) {
      setError('製品IDを入力してください');
      return;
    }
    
    setError('');
    onNext({
      qrCode: manualInput,
      productId: manualInput,
      batchId: 'MANUAL_ENTRY',
      timestamp: new Date().toISOString(),
    });
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          QRコードスキャン機能
        </Typography>
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Button
            variant="contained"
            size="large"
            startIcon={scanning ? <CircularProgress size={20} color="inherit" /> : <QrIcon />}
            onClick={handleScan}
            disabled={scanning}
            sx={{ py: 2 }}
          >
            {scanning ? 'スキャン中...' : 'QRコードをスキャン'}
          </Button>

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
              placeholder="例: PRODUCT_001"
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