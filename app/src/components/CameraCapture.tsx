import React, { useState } from 'react';
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
} from '@mui/material';
import Grid from '@mui/material/Grid2';
import {
  PhotoCamera,
  Refresh,
  KeyboardArrowLeft,
  KeyboardArrowRight,
} from '@mui/icons-material';

interface CameraCaptureProps {
  onNext: (data: any) => void;
  onBack: () => void;
}

export const CameraCapture: React.FC<CameraCaptureProps> = ({ onNext, onBack }) => {
  const [capturing, setCapturing] = useState(false);
  const [images, setImages] = useState<string[]>([]);
  const [error, setError] = useState('');

  const handleCapture = async () => {
    setCapturing(true);
    setError('');
    
    try {
      // Simulate camera capture (in real implementation, this would use Tauri camera API)
      setTimeout(() => {
        const mockImageUrl = `data:image/svg+xml;base64,${btoa(`
          <svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
            <rect width="400" height="300" fill="#f0f0f0"/>
            <circle cx="200" cy="150" r="50" fill="#1976d2"/>
            <text x="200" y="250" text-anchor="middle" font-family="Arial" font-size="16" fill="#666">
              模擬撮影画像 ${images.length + 1}
            </text>
          </svg>
        `)}`;
        
        setImages(prev => [...prev, mockImageUrl]);
        setCapturing(false);
      }, 1500);
    } catch (err) {
      setError('画像の撮影に失敗しました');
      setCapturing(false);
    }
  };

  const handleRetake = (index: number) => {
    setImages(prev => prev.filter((_, i) => i !== index));
  };

  const handleNext = () => {
    if (images.length === 0) {
      setError('少なくとも1枚の画像を撮影してください');
      return;
    }
    
    onNext({
      images: images,
      imageCount: images.length,
      captureTimestamp: new Date().toISOString(),
    });
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          高品質画像撮影
        </Typography>
        
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