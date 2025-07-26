import React, { useState } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  Alert,
  Card,
  CardContent,
  Chip,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  TextField,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  Person,
  CheckCircle,
  Cancel,
  Warning,
  ExpandMore,
  KeyboardArrowLeft,
  KeyboardArrowRight,
  Comment,
} from '@mui/icons-material';

interface HumanVerificationProps {
  onNext: (data: any) => void;
  onBack: () => void;
  inspectionData: any;
}

export const HumanVerification: React.FC<HumanVerificationProps> = ({ 
  onNext, 
  onBack, 
  inspectionData 
}) => {
  const [finalJudgment, setFinalJudgment] = useState('');
  const [itemJudgments, setItemJudgments] = useState<Record<number, string>>({});
  const [comments, setComments] = useState('');
  const [inspectorNotes, setInspectorNotes] = useState('');
  const [error, setError] = useState('');

  const aiResults = inspectionData.aiResults;

  const handleItemJudgment = (index: number, judgment: string) => {
    setItemJudgments(prev => ({
      ...prev,
      [index]: judgment
    }));
  };

  const handleSubmit = () => {
    if (!finalJudgment) {
      setError('最終判定を選択してください');
      return;
    }

    // Check if all items have been reviewed
    const unreviewed = aiResults.detections.filter(
      (_: any, index: number) => !itemJudgments[index]
    );

    if (unreviewed.length > 0) {
      setError('すべての検査項目について判定を行ってください');
      return;
    }

    setError('');
    
    const humanVerificationData = {
      finalJudgment,
      itemJudgments,
      comments,
      inspectorNotes,
      timestamp: new Date().toISOString(),
      inspector: 'Inspector_001', // In real app, this would come from authentication
      verificationCompleted: true,
    };

    onNext(humanVerificationData);
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          <Person sx={{ mr: 1, verticalAlign: 'middle' }} />
          人による確認・最終判定
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* AI結果サマリー */}
        <Card sx={{ mb: 3, bgcolor: 'grey.50' }}>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              AI検査結果サマリー
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <Chip 
                label={`総合判定: ${aiResults.overallResult}`}
                color={aiResults.overallResult === 'PASS' ? 'success' : 'warning'}
              />
              <Chip 
                label={`信頼度: ${Math.round(aiResults.confidence * 100)}%`}
                variant="outlined"
              />
              <Chip 
                label={`処理時間: ${aiResults.processingTime}s`}
                variant="outlined"
              />
            </Box>
          </CardContent>
        </Card>

        {/* 項目別確認 */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            検査項目別確認
          </Typography>
          
          {aiResults.detections.map((detection: any, index: number) => (
            <Card key={index} sx={{ mb: 2 }}>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Box>
                    <Typography variant="subtitle2">
                      {detection.type}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {detection.details}
                    </Typography>
                    <Chip 
                      label={`AI判定: ${detection.result}`}
                      size="small"
                      color={detection.result === 'PASS' ? 'success' : 'warning'}
                      sx={{ mt: 1 }}
                    />
                  </Box>
                  
                  <FormControl>
                    <FormLabel component="legend" sx={{ fontSize: '0.875rem' }}>
                      人による判定
                    </FormLabel>
                    <RadioGroup
                      row
                      value={itemJudgments[index] || ''}
                      onChange={(e) => handleItemJudgment(index, e.target.value)}
                    >
                      <FormControlLabel 
                        value="OK" 
                        control={<Radio size="small" />} 
                        label="OK"
                      />
                      <FormControlLabel 
                        value="NG" 
                        control={<Radio size="small" />} 
                        label="NG"
                      />
                      <FormControlLabel 
                        value="PENDING" 
                        control={<Radio size="small" />} 
                        label="保留"
                      />
                    </RadioGroup>
                  </FormControl>
                </Box>
              </CardContent>
            </Card>
          ))}
        </Box>

        {/* 最終判定 */}
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <FormControl component="fieldset">
              <FormLabel component="legend">
                <Typography variant="subtitle1">最終判定</Typography>
              </FormLabel>
              <RadioGroup
                value={finalJudgment}
                onChange={(e) => setFinalJudgment(e.target.value)}
                sx={{ mt: 1 }}
              >
                <FormControlLabel 
                  value="OK" 
                  control={<Radio />} 
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CheckCircle color="success" />
                      <Typography>合格 (OK)</Typography>
                    </Box>
                  }
                />
                <FormControlLabel 
                  value="NG" 
                  control={<Radio />} 
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Cancel color="error" />
                      <Typography>不合格 (NG)</Typography>
                    </Box>
                  }
                />
                <FormControlLabel 
                  value="PENDING" 
                  control={<Radio />} 
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Warning color="warning" />
                      <Typography>保留 (要再検査)</Typography>
                    </Box>
                  }
                />
              </RadioGroup>
            </FormControl>
          </CardContent>
        </Card>

        {/* コメント入力 */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Comment sx={{ mr: 1 }} />
            <Typography>コメント・備考 (任意)</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="検査コメント"
                multiline
                rows={3}
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="AI判定に対するコメントや気になった点を記入してください"
                fullWidth
              />
              <TextField
                label="検査員備考"
                multiline
                rows={2}
                value={inspectorNotes}
                onChange={(e) => setInspectorNotes(e.target.value)}
                placeholder="その他の特記事項があれば記入してください"
                fullWidth
              />
            </Box>
          </AccordionDetails>
        </Accordion>
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
          onClick={handleSubmit}
          color={finalJudgment === 'NG' ? 'error' : 'primary'}
        >
          検査完了
        </Button>
      </Box>
    </Box>
  );
};