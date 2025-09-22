import React, { useMemo, useState } from "react";
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
  Menu,
  MenuItem,
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
  MoreHoriz as MoreIcon,
} from "@mui/icons-material";

export const Navigation: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [moreAnchorEl, setMoreAnchorEl] = useState<null | HTMLElement>(null);

  // 画面幅によってレスポンシブ対応を判定
  const isMobile = useMediaQuery(theme.breakpoints.down("md")); // 768px以下
  const isTablet = useMediaQuery(theme.breakpoints.down("lg")); // 1024px以下

  const maxPrimary = useMemo(() => (isTablet ? 4 : 6), [isTablet]);
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
      icon: <VideocamIcon />,
      label: "カメラ映像",
      path: "/uplink",
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
  const primaryItems = navigationItems.slice(
    0,
    Math.min(maxPrimary, navigationItems.length)
  );
  const overflowItems = navigationItems.slice(primaryItems.length);

  const currentPath = location.pathname;
  const activeIndexInPrimary = primaryItems.findIndex((i) => {
    if (i.path === "/executions" && currentPath.startsWith("/execution"))
      return true;
    return i.path === currentPath;
  });
  const isActiveInOverflow = overflowItems.some(
    (i) =>
      i.path === currentPath ||
      (i.path === "/executions" && currentPath.startsWith("/execution"))
  );
  const tabValue =
    activeIndexInPrimary >= 0
      ? activeIndexInPrimary
      : isActiveInOverflow && overflowItems.length > 0
      ? primaryItems.length
      : 0;

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    if (newValue < primaryItems.length) {
      navigate(primaryItems[newValue].path);
      return;
    }
    // More tab clicked -> open menu (handled by onClick of the Tab)
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
                    item.path === currentPath ||
                    (item.path === "/executions" &&
                      currentPath.startsWith("/execution"))
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
        value={tabValue}
        onChange={handleTabChange}
        variant="scrollable"
        scrollButtons="auto"
        allowScrollButtonsMobile
        sx={{
          flexGrow: 1,
          "& .MuiTab-root": {
            color: "rgba(255, 255, 255, 0.7)",
            minWidth: 120,
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
        {primaryItems.map((item, index) => (
          <Tab
            key={index}
            icon={item.icon}
            label={item.label}
            iconPosition="start"
          />
        ))}
        {overflowItems.length > 0 && (
          <Tab
            key="more"
            icon={<MoreIcon />}
            label="その他"
            iconPosition="start"
            onClick={(e: any) => setMoreAnchorEl(e.currentTarget)}
          />
        )}
      </Tabs>
      <Menu
        anchorEl={moreAnchorEl}
        open={Boolean(moreAnchorEl)}
        onClose={() => setMoreAnchorEl(null)}
        keepMounted
      >
        {overflowItems.map((item, idx) => (
          <MenuItem
            key={idx}
            onClick={() => {
              setMoreAnchorEl(null);
              navigate(item.path);
            }}
          >
            <ListItemIcon sx={{ minWidth: 32 }}>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
};
