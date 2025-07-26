import React from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  Alert,
  Card,
  CardContent,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import Grid from '@mui/material/Grid2';
import {
  CheckCircle,
  Cancel,
  Warning,
  Refresh,
  Download,
  Print,
  Share,
  Timeline,
  Person,
  Schedule,
  QrCode,
  ExpandMore,
} from '@mui/icons-material';

interface InspectionCompleteProps {
  onReset: () => void;
  inspectionData: any;
}

export const InspectionComplete: React.FC<InspectionCompleteProps> = ({ 
  onReset, 
  inspectionData 
}) => {
  const finalJudgment = inspectionData.finalJudgment;
  const aiResults = inspectionData.aiResults;
  
  const getJudgmentDisplay = (judgment: string) => {
    switch (judgment) {
      case 'OK':
        return {
          color: 'success' as const,
          icon: <CheckCircle />,
          text: '合格',
          description: '検査に合格しました'
        };
      case 'NG':
        return {
          color: 'error' as const,
          icon: <Cancel />,
          text: '不合格',
          description: '検査で不合格となりました'
        };
      case 'PENDING':
        return {
          color: 'warning' as const,
          icon: <Warning />,
          text: '保留',
          description: '再検査が必要です'
        };
      default:
        return {
          color: 'default' as const,
          icon: null,
          text: '未判定',
          description: ''
        };
    }
  };

  const judgment = getJudgmentDisplay(finalJudgment);

  const handleExportReport = () => {
    // In real implementation, this would generate and download a report
    console.log('Exporting inspection report...', inspectionData);
    alert('検査レポートの出力機能は実装中です');
  };

  const handlePrintReport = () => {
    // In real implementation, this would print the report
    console.log('Printing inspection report...', inspectionData);
    alert('検査レポートの印刷機能は実装中です');
  };

  const handleShareReport = () => {
    // In real implementation, this would share the report
    console.log('Sharing inspection report...', inspectionData);
    alert('検査レポートの共有機能は実装中です');
  };

  return (
    <Box sx={{ width: '100%' }}>
      {/* 検査完了ヘッダー */}
      <Alert 
        severity={judgment.color === 'default' ? 'info' : judgment.color}
        sx={{ mb: 3 }}
        icon={judgment.icon}
      >
        <Typography variant="h6">
          検査完了 - {judgment.text}
        </Typography>
        <Typography variant="body2">
          {judgment.description}
        </Typography>
      </Alert>

      {/* 検査結果サマリー */}
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          検査結果サマリー
        </Typography>
        
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <QrCode color="primary" sx={{ fontSize: 32, mb: 1 }} />
                <Typography variant="subtitle2">製品ID</Typography>
                <Typography variant="body2">
                  {inspectionData.productId || 'N/A'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Schedule color="primary" sx={{ fontSize: 32, mb: 1 }} />
                <Typography variant="subtitle2">検査時間</Typography>
                <Typography variant="body2">
                  {aiResults?.processingTime || 0}秒
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Timeline color="primary" sx={{ fontSize: 32, mb: 1 }} />
                <Typography variant="subtitle2">AI信頼度</Typography>
                <Typography variant="body2">
                  {Math.round((aiResults?.confidence || 0) * 100)}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, sm: 6, md: 3 }}>
            <Card>
              <CardContent sx={{ textAlign: 'center' }}>
                <Person color="primary" sx={{ fontSize: 32, mb: 1 }} />
                <Typography variant="subtitle2">検査員</Typography>
                <Typography variant="body2">
                  {inspectionData.inspector || 'Inspector_001'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* 詳細結果 */}
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography variant="subtitle1">詳細検査結果</Typography>
          </AccordionSummary>
          <AccordionDetails>
            {aiResults?.detections && (
              <List>
                {aiResults.detections.map((detection: any, index: number) => {
                  const humanJudgment = inspectionData.itemJudgments?.[index];
                  return (
                    <React.Fragment key={index}>
                      <ListItem>
                        <ListItemIcon>
                          {humanJudgment === 'OK' ? (
                            <CheckCircle color="success" />
                          ) : humanJudgment === 'NG' ? (
                            <Cancel color="error" />
                          ) : (
                            <Warning color="warning" />
                          )}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                              <Typography variant="subtitle2">
                                {detection.type}
                              </Typography>
                              <Chip 
                                label={`AI: ${detection.result}`}
                                size="small"
                                variant="outlined"
                              />
                              <Chip 
                                label={`人: ${humanJudgment || '未判定'}`}
                                size="small"
                                color={
                                  humanJudgment === 'OK' ? 'success' :
                                  humanJudgment === 'NG' ? 'error' : 'warning'
                                }
                              />
                            </Box>
                          }
                          secondary={
                            <Typography variant="body2" color="text.secondary">
                              {detection.details}
                            </Typography>
                          }
                        />
                      </ListItem>
                      {index < aiResults.detections.length - 1 && <Divider />}
                    </React.Fragment>
                  );
                })}
              </List>
            )}
            
            {inspectionData.comments && (
              <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                <Typography variant="subtitle2" gutterBottom>
                  検査コメント
                </Typography>
                <Typography variant="body2">
                  {inspectionData.comments}
                </Typography>
              </Box>
            )}

            {inspectionData.inspectorNotes && (
              <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                <Typography variant="subtitle2" gutterBottom>
                  検査員備考
                </Typography>
                <Typography variant="body2">
                  {inspectionData.inspectorNotes}
                </Typography>
              </Box>
            )}
          </AccordionDetails>
        </Accordion>
      </Paper>

      {/* アクションボタン */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          レポート操作
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Button
            variant="outlined"
            startIcon={<Download />}
            onClick={handleExportReport}
          >
            レポート出力
          </Button>
          <Button
            variant="outlined"
            startIcon={<Print />}
            onClick={handlePrintReport}
          >
            印刷
          </Button>
          <Button
            variant="outlined"
            startIcon={<Share />}
            onClick={handleShareReport}
          >
            共有
          </Button>
        </Box>
      </Paper>

      {/* 新規検査開始 */}
      <Box sx={{ display: 'flex', justifyContent: 'center' }}>
        <Button
          variant="contained"
          size="large"
          startIcon={<Refresh />}
          onClick={onReset}
          sx={{ px: 4, py: 2 }}
        >
          新しい検査を開始
        </Button>
      </Box>
    </Box>
  );
};