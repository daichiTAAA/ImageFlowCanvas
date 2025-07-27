import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Tabs, Tab } from "@mui/material";
import {
  Dashboard as DashboardIcon,
  Build as BuildIcon,
  Timeline as TimelineIcon,
  Settings as StorageIcon,
  Camera as VideocamIcon,
  Assignment as InspectionIcon,
  Assessment as ResultsIcon,
} from "@mui/icons-material";

export const Navigation: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  const getTabValue = () => {
    if (location.pathname === "/") return 0;
    if (location.pathname === "/pipeline-builder") return 1;
    if (
      location.pathname === "/executions" ||
      location.pathname.startsWith("/execution")
    )
      return 2;
    if (location.pathname === "/camera-stream") return 3;
    if (location.pathname === "/inspection-masters") return 4;
    if (location.pathname === "/inspection-results") return 5;
    if (location.pathname === "/grpc-services") return 6;
    return 0;
  };

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    switch (newValue) {
      case 0:
        navigate("/");
        break;
      case 1:
        navigate("/pipeline-builder");
        break;
      case 2:
        navigate("/executions");
        break;
      case 3:
        navigate("/camera-stream");
        break;
      case 4:
        navigate("/inspection-masters");
        break;
      case 5:
        navigate("/inspection-results");
        break;
      case 6:
        navigate("/grpc-services");
        break;
    }
  };

  return (
    <Tabs
      value={getTabValue()}
      onChange={handleTabChange}
      sx={{
        flexGrow: 1,
        "& .MuiTab-root": {
          color: "rgba(255, 255, 255, 0.7)",
          "&.Mui-selected": {
            color: "white",
          },
        },
        "& .MuiTabs-indicator": {
          backgroundColor: "white",
        },
      }}
    >
      <Tab
        icon={<DashboardIcon />}
        label="ダッシュボード"
        iconPosition="start"
      />
      <Tab
        icon={<BuildIcon />}
        label="パイプラインビルダー"
        iconPosition="start"
      />
      <Tab icon={<TimelineIcon />} label="実行監視" iconPosition="start" />
      <Tab icon={<VideocamIcon />} label="リアルタイム処理" iconPosition="start" />
      <Tab icon={<InspectionIcon />} label="検査マスタ" iconPosition="start" />
      <Tab icon={<ResultsIcon />} label="検査結果" iconPosition="start" />
      <Tab icon={<StorageIcon />} label="gRPCサービス" iconPosition="start" />
    </Tabs>
  );
};
