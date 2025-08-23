import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Tabs,
  Tab,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Box,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import {
  Dashboard as DashboardIcon,
  Build as BuildIcon,
  Timeline as TimelineIcon,
  Settings as StorageIcon,
  Camera as VideocamIcon,
  Assignment as InspectionIcon,
  Assessment as ResultsIcon,
  Menu as MenuIcon,
} from "@mui/icons-material";

export const Navigation: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();
  const [drawerOpen, setDrawerOpen] = useState(false);

  // 画面幅によってレスポンシブ対応を判定
  const isMobile = useMediaQuery(theme.breakpoints.down("md")); // 768px以下
  const isTablet = useMediaQuery(theme.breakpoints.down("lg")); // 1024px以下

  const navigationItems = [
    { icon: <DashboardIcon />, label: "ダッシュボード", path: "/" },
    {
      icon: <BuildIcon />,
      label: "パイプラインビルダー",
      path: "/pipeline-builder",
    },
    { icon: <TimelineIcon />, label: "実行監視", path: "/executions" },
    {
      icon: <VideocamIcon />,
      label: "リアルタイム処理",
      path: "/camera-stream",
    },
    {
      icon: <InspectionIcon />,
      label: "検査マスタ",
      path: "/inspection-masters",
    },
    { icon: <InspectionIcon />, label: "順序情報", path: "/order-info" },
    { icon: <ResultsIcon />, label: "検査結果", path: "/inspection-results" },
    { icon: <StorageIcon />, label: "gRPCサービス", path: "/grpc-services" },
  ];

  const getTabValue = () => {
    const pathMap: { [key: string]: number } = {
      "/": 0,
      "/pipeline-builder": 1,
      "/executions": 2,
      "/camera-stream": 3,
      "/inspection-masters": 4,
      "/order-info": 5,
      "/inspection-results": 6,
      "/grpc-services": 7,
    };

    if (location.pathname.startsWith("/execution")) return 2;
    return pathMap[location.pathname] || 0;
  };

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    if (newValue < navigationItems.length) {
      navigate(navigationItems[newValue].path);
    }
  };

  const handleDrawerToggle = () => {
    setDrawerOpen(!drawerOpen);
  };

  const handleDrawerItemClick = (path: string) => {
    navigate(path);
    setDrawerOpen(false);
  };

  // モバイル表示（ハンバーガーメニュー）
  if (isMobile) {
    return (
      <>
        <IconButton
          color="inherit"
          aria-label="open drawer"
          onClick={handleDrawerToggle}
          sx={{ mr: 2 }}
        >
          <MenuIcon />
        </IconButton>
        <Drawer
          anchor="left"
          open={drawerOpen}
          onClose={handleDrawerToggle}
          sx={{
            "& .MuiDrawer-paper": {
              width: 280,
              backgroundColor: "primary.main",
              color: "white",
            },
          }}
        >
          <List>
            {navigationItems.map((item, index) => (
              <ListItem
                key={index}
                onClick={() => handleDrawerItemClick(item.path)}
                sx={{
                  cursor: "pointer",
                  backgroundColor:
                    getTabValue() === index
                      ? "rgba(255, 255, 255, 0.1)"
                      : "transparent",
                  "&:hover": {
                    backgroundColor: "rgba(255, 255, 255, 0.05)",
                  },
                }}
              >
                <ListItemIcon sx={{ color: "white", minWidth: 40 }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItem>
            ))}
          </List>
        </Drawer>
      </>
    );
  }

  // タブレット・デスクトップ表示（スクロール可能なタブ）
  return (
    <Box sx={{ flexGrow: 1, overflow: "hidden" }}>
      <Tabs
        value={getTabValue()}
        onChange={handleTabChange}
        variant={isTablet ? "scrollable" : "standard"}
        scrollButtons={isTablet ? "auto" : false}
        allowScrollButtonsMobile={isTablet}
        sx={{
          flexGrow: 1,
          "& .MuiTab-root": {
            color: "rgba(255, 255, 255, 0.7)",
            minWidth: isTablet ? 120 : "auto",
            "&.Mui-selected": {
              color: "white",
            },
          },
          "& .MuiTabs-indicator": {
            backgroundColor: "white",
          },
          "& .MuiTabs-scrollButtons": {
            color: "rgba(255, 255, 255, 0.7)",
            "&.Mui-disabled": {
              opacity: 0.3,
            },
          },
        }}
      >
        {navigationItems.map((item, index) => (
          <Tab
            key={index}
            icon={item.icon}
            label={item.label}
            iconPosition="start"
          />
        ))}
      </Tabs>
    </Box>
  );
};
