import React, { useState, useRef, useCallback } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  Alert,
  CircularProgress,
  Card,
  CardMedia,
  CardActions,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
} from '@mui/material';
import Grid from '@mui/material/Grid2';
import {
  PhotoCamera,
  Refresh,
  KeyboardArrowLeft,
  KeyboardArrowRight,
  Cameraswitch,
} from '@mui/icons-material';
import { invoke } from '@tauri-apps/api/core';
import Webcam from 'react-webcam';

interface CameraCaptureProps {
  onNext: (data: any) => void;
  onBack: () => void;
}

interface CameraConfig {
  resolution: string;
  quality: number;
  flash_enabled: boolean;
}

export const CameraCapture: React.FC<CameraCaptureProps> = ({ onNext, onBack }) => {
  const [capturing, setCapturing] = useState(false);
  const [images, setImages] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [useWebcam, setUseWebcam] = useState(false);
  const [config, setConfig] = useState<CameraConfig>({
    resolution: '1920x1080',
    quality: 0.8,
    flash_enabled: false,
  });
  const [facingMode, setFacingMode] = useState<'user' | 'environment'>('environment');
  
  const webcamRef = useRef<Webcam>(null);

  const videoConstraints = {
    width: 1920,
    height: 1080,
    facingMode: facingMode,
  };

  const captureTauriCamera = async () => {
    setCapturing(true);
    setError('');
    
    try {
      // Use Tauri camera plugin for real camera capture
      const imageData = await invoke('capture_image_from_camera', { config }) as string;
      setImages(prev => [...prev, imageData]);
      setCapturing(false);
    } catch (err) {
      setError('画像の撮影に失敗しました: ' + (err as Error).message);
      setCapturing(false);
    }
  };

  const captureWebcam = useCallback(() => {
    setCapturing(true);
    setError('');
    
    try {
      const imageSrc = webcamRef.current?.getScreenshot();
      if (imageSrc) {
        setImages(prev => [...prev, imageSrc]);
      } else {
        setError('Webカメラからの画像取得に失敗しました');
      }
      setCapturing(false);
    } catch (err) {
      setError('画像の撮影に失敗しました: ' + (err as Error).message);
      setCapturing(false);
    }
  }, [webcamRef]);

  const handleCapture = () => {
    if (useWebcam) {
      captureWebcam();
    } else {
      captureTauriCamera();
    }
  };

  const handleRetake = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index));
  };

  const handleNext = async () => {
    if (images.length === 0) {
      setError('少なくとも1枚の画像を撮影してください');
      return;
    }
    
    try {
      // Save images using Tauri backend
      const sessionId = 'session_' + Date.now();
      const imagePaths = await invoke('save_inspection_images', {
        sessionId,
        images,
      }) as string[];
      
      onNext({
        images: images,
        imagePaths: imagePaths,
        imageCount: images.length,
        captureTimestamp: new Date().toISOString(),
        sessionId: sessionId,
      });
    } catch (err) {
      setError('画像の保存に失敗しました: ' + (err as Error).message);
    }
  };

  const switchCamera = () => {
    setFacingMode(prev => prev === 'user' ? 'environment' : 'user');
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          高品質画像撮影
        </Typography>

        {/* Camera Configuration */}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
          <FormControl size="small">
            <InputLabel>解像度</InputLabel>
            <Select
              value={config.resolution}
              label="解像度"
              onChange={(e) => setConfig(prev => ({ ...prev, resolution: e.target.value }))}
            >
              <MenuItem value="1920x1080">1920x1080 (Full HD)</MenuItem>
              <MenuItem value="1280x720">1280x720 (HD)</MenuItem>
              <MenuItem value="640x480">640x480 (SD)</MenuItem>
            </Select>
          </FormControl>

          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <FormControlLabel
              control={
                <Switch
                  checked={useWebcam}
                  onChange={(e) => setUseWebcam(e.target.checked)}
                />
              }
              label="Webカメラを使用"
            />
            
            <FormControlLabel
              control={
                <Switch
                  checked={config.flash_enabled}
                  onChange={(e) => setConfig(prev => ({ ...prev, flash_enabled: e.target.checked }))}
                />
              }
              label="フラッシュ"
            />

            {useWebcam && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<Cameraswitch />}
                onClick={switchCamera}
              >
                カメラ切替
              </Button>
            )}
          </Box>
        </Box>

        {/* Camera Preview */}
        {useWebcam && (
          <Box sx={{ mb: 3, display: 'flex', justifyContent: 'center' }}>
            <Box sx={{ position: 'relative', maxWidth: 400 }}>
              <Webcam
                ref={webcamRef}
                audio={false}
                screenshotFormat="image/jpeg"
                screenshotQuality={config.quality}
                videoConstraints={videoConstraints}
                style={{ width: '100%', borderRadius: 8 }}
              />
            </Box>
          </Box>
        )}
        
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
          <Button
            variant="contained"
            size="large"
            startIcon={capturing ? <CircularProgress size={20} color="inherit" /> : <PhotoCamera />}
            onClick={handleCapture}
            disabled={capturing}
            sx={{ py: 2 }}
          >
            {capturing ? '撮影中...' : '画像を撮影'}
          </Button>

          {error && (
            <Alert severity="error">
              {error}
            </Alert>
          )}

          {images.length > 0 && (
            <Alert severity="info">
              {images.length}枚の画像が撮影されました
            </Alert>
          )}
        </Box>

        {images.length > 0 && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle1" gutterBottom>
              撮影済み画像
            </Typography>
            <Grid container spacing={2}>
              {images.map((image, index) => (
                <Grid size={{ xs: 12, sm: 6, md: 4 }} key={index}>
                  <Card>
                    <CardMedia
                      component="img"
                      height="200"
                      image={image}
                      alt={`撮影画像 ${index + 1}`}
                    />
                    <CardActions sx={{ justifyContent: 'space-between' }}>
                      <Chip 
                        label={`画像 ${index + 1}`} 
                        size="small" 
                        color="primary" 
                      />
                      <Button
                        size="small"
                        startIcon={<Refresh />}
                        onClick={() => handleRetake(index)}
                      >
                        再撮影
                      </Button>
                    </CardActions>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        )}
      </Paper>

      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button
          variant="outlined"
          startIcon={<KeyboardArrowLeft />}
          onClick={onBack}
        >
          戻る
        </Button>
        <Button
          variant="contained"
          endIcon={<KeyboardArrowRight />}
          onClick={handleNext}
          disabled={images.length === 0}
        >
          次へ
        </Button>
      </Box>
    </Box>
  );
};