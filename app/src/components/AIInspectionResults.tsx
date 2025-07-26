import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  LinearProgress,
  Alert,
  Card,
  CardContent,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import Grid from '@mui/material/Grid2';
import {
  SmartToy,
  CheckCircle,
  Warning,
  Error,
  ExpandMore,
  KeyboardArrowLeft,
  KeyboardArrowRight,
  Visibility,
  Timer,
  Assessment,
} from '@mui/icons-material';

interface AIInspectionResultsProps {
  onNext: (data: any) => void;
  onBack: () => void;
  inspectionData: any;
}

export const AIInspectionResults: React.FC<AIInspectionResultsProps> = ({ 
  onNext, 
  onBack, 
  inspectionData 
}) => {
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [completed, setCompleted] = useState(false);
  const [results, setResults] = useState<any>(null);

  const pipelineSteps = [
    { name: '画像前処理', duration: 1000 },
    { name: 'リサイズ処理', duration: 800 },
    { name: 'AI検知実行', duration: 2000 },
    { name: '判定分析', duration: 1200 },
    { name: '結果統合', duration: 500 },
  ];

  useEffect(() => {
    let stepIndex = 0;
    let totalProgress = 0;
    
    const runPipelineStep = () => {
      if (stepIndex < pipelineSteps.length) {
        const step = pipelineSteps[stepIndex];
        setCurrentStep(step.name);
        
        const stepProgress = 100 / pipelineSteps.length;
        const interval = setInterval(() => {
          totalProgress += stepProgress / (step.duration / 100);
          setProgress(Math.min(totalProgress, (stepIndex + 1) * stepProgress));
          
          if (totalProgress >= (stepIndex + 1) * stepProgress) {
            clearInterval(interval);
            stepIndex++;
            setTimeout(runPipelineStep, 200);
          }
        }, 100);
      } else {
        // Pipeline completed
        setCurrentStep('完了');
        setCompleted(true);
        setResults({
          overallResult: 'PASS',
          confidence: 0.87,
          processingTime: 5.5,
          detections: [
            {
              type: '外観検査',
              result: 'PASS',
              confidence: 0.92,
              details: '表面に異常は検出されませんでした',
            },
            {
              type: '寸法測定',
              result: 'PASS',
              confidence: 0.85,
              details: '測定値は許容範囲内です (±0.1mm)',
            },
            {
              type: '色彩検査',
              result: 'WARNING',
              confidence: 0.78,
              details: '軽微な色差が検出されました',
            }
          ],
          metadata: {
            pipelineId: 'INSPECTION_V2.1',
            executionId: `exec_${Date.now()}`,
            imageCount: inspectionData.imageCount || 1,
          }
        });
      }
    };
    
    runPipelineStep();
  }, []);

  const getResultColor = (result: string) => {
    switch (result) {
      case 'PASS': return 'success';
      case 'WARNING': return 'warning';
      case 'FAIL': return 'error';
      default: return 'default';
    }
  };

  const getResultIcon = (result: string) => {
    switch (result) {
      case 'PASS': return <CheckCircle />;
      case 'WARNING': return <Warning />;
      case 'FAIL': return <Error />;
      default: return <Assessment />;
    }
  };

  const handleNext = () => {
    onNext({
      aiResults: results,
      pipelineCompleted: true,
      processingTime: results.processingTime,
    });
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          AI検査実行中
        </Typography>
        
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
            <SmartToy sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="body2">
              {currentStep}
            </Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={progress} 
            sx={{ height: 8, borderRadius: 4 }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            {Math.round(progress)}% 完了
          </Typography>
        </Box>

        {completed && results && (
          <Box>
            <Alert 
              severity={results.overallResult === 'PASS' ? 'success' : 'warning'} 
              sx={{ mb: 2 }}
            >
              パイプライン実行完了 - 総合判定: {results.overallResult}
            </Alert>

            <Grid container spacing={2} sx={{ mb: 2 }}>
              <Grid size={4}>
                <Card>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Timer color="primary" sx={{ fontSize: 32, mb: 1 }} />
                    <Typography variant="h6">{results.processingTime}s</Typography>
                    <Typography variant="caption">処理時間</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={4}>
                <Card>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Assessment color="primary" sx={{ fontSize: 32, mb: 1 }} />
                    <Typography variant="h6">{Math.round(results.confidence * 100)}%</Typography>
                    <Typography variant="caption">信頼度</Typography>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={4}>
                <Card>
                  <CardContent sx={{ textAlign: 'center' }}>
                    <Visibility color="primary" sx={{ fontSize: 32, mb: 1 }} />
                    <Typography variant="h6">{results.detections.length}</Typography>
                    <Typography variant="caption">検査項目</Typography>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>

            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography>詳細結果</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <List>
                  {results.detections.map((detection: any, index: number) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        {getResultIcon(detection.result)}
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography>{detection.type}</Typography>
                            <Chip 
                              label={detection.result} 
                              size="small" 
                              color={getResultColor(detection.result)} 
                            />
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant="body2">
                              {detection.details}
                            </Typography>
                            <Typography variant="caption">
                              信頼度: {Math.round(detection.confidence * 100)}%
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          </Box>
        )}
      </Paper>

      <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
        <Button
          variant="outlined"
          startIcon={<KeyboardArrowLeft />}
          onClick={onBack}
          disabled={!completed}
        >
          戻る
        </Button>
        <Button
          variant="contained"
          endIcon={<KeyboardArrowRight />}
          onClick={handleNext}
          disabled={!completed}
        >
          人による確認へ
        </Button>
      </Box>
    </Box>
  );
};