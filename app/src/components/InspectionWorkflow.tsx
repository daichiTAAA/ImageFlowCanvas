import React, { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Stepper,
  Step,
  StepLabel,
  StepContent,
} from "@mui/material";
import {
  QrCodeScanner,
  PhotoCamera,
  SmartToy,
  Person,
  CheckCircle,
} from "@mui/icons-material";
import { QRCodeScanner } from "./QRCodeScanner";
import { CameraCapture } from "./CameraCapture";
import { AIInspectionResults } from "./AIInspectionResults";
import { HumanVerification } from "./HumanVerification";
import { InspectionComplete } from "./InspectionComplete";

const steps = [
  {
    label: "QRコードスキャン",
    description: "検査対象のQRコードをスキャンしてください",
    icon: <QrCodeScanner />,
  },
  {
    label: "画像撮影",
    description: "検査対象を撮影してください",
    icon: <PhotoCamera />,
  },
  {
    label: "AI検査実行",
    description: "AIパイプラインによる自動検査を実行中...",
    icon: <SmartToy />,
  },
  {
    label: "人による確認",
    description: "AI結果を確認し、最終判定を行ってください",
    icon: <Person />,
  },
  {
    label: "検査完了",
    description: "検査が完了しました",
    icon: <CheckCircle />,
  },
];

export const InspectionWorkflow: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [inspectionData, setInspectionData] = useState<Record<string, any>>({});

  const handleNext = (stepData?: Record<string, any>) => {
    if (stepData) {
      setInspectionData((prev) => ({ ...prev, ...stepData }));
    }
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleReset = () => {
    setActiveStep(0);
    setInspectionData({});
  };

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return <QRCodeScanner onNext={handleNext} />;
      case 1:
        return <CameraCapture onNext={handleNext} onBack={handleBack} />;
      case 2:
        return (
          <AIInspectionResults
            onNext={handleNext}
            onBack={handleBack}
            inspectionData={inspectionData}
          />
        );
      case 3:
        return (
          <HumanVerification
            onNext={handleNext}
            onBack={handleBack}
            inspectionData={inspectionData}
          />
        );
      case 4:
        return (
          <InspectionComplete
            onReset={handleReset}
            inspectionData={inspectionData}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Box sx={{ width: "100%" }}>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h5" component="h1" gutterBottom>
            検査ワークフロー
          </Typography>
          <Typography variant="body2" color="text.secondary">
            以下のステップに従って検査を実行してください
          </Typography>
        </CardContent>
      </Card>

      <Stepper activeStep={activeStep} orientation="vertical">
        {steps.map((step, index) => (
          <Step key={step.label}>
            <StepLabel
              optional={
                index === steps.length - 1 ? (
                  <Typography variant="caption">最終ステップ</Typography>
                ) : null
              }
              StepIconComponent={() => (
                <Box
                  sx={{
                    color: index <= activeStep ? "primary.main" : "grey.400",
                    display: "flex",
                    alignItems: "center",
                    "& svg": { fontSize: 20 },
                  }}
                >
                  {step.icon}
                </Box>
              )}
            >
              {step.label}
            </StepLabel>
            <StepContent>
              <Typography variant="body2" sx={{ mb: 2 }}>
                {step.description}
              </Typography>
              {renderStepContent(index)}
            </StepContent>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
};
