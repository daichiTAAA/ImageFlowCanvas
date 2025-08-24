import { Routes, Route, useLocation } from "react-router-dom";
import { AppBar, Toolbar, Typography, Container, Box } from "@mui/material";
import { Dashboard } from "./pages/Dashboard";
import { PipelineBuilder } from "./pages/PipelineBuilder";
import { ExecutionMonitor } from "./pages/ExecutionMonitor";
import { ExecutionList } from "./pages/ExecutionList";
import { Login } from "./pages/Login";
import { GrpcServicesStatus } from "./pages/GrpcServicesStatus";
import { CameraStream } from "./pages/CameraStream";
import ThinkletViewer from "./pages/ThinkletViewer";
import { InspectionMasters } from "./pages/InspectionMasters";
import { InspectionResults } from "./pages/InspectionResults";
import { OrderInfo } from "./pages/OrderInfo";
import { AuthProvider, useAuth } from "./services/AuthContext";
import { Navigation } from "./components/Navigation";

function AppContent() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  const showNavigation = isAuthenticated && location.pathname !== "/login";

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ mr: 4 }}>
            ImageFlowCanvas
          </Typography>
          {showNavigation && <Navigation />}
        </Toolbar>
      </AppBar>

      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Dashboard />} />
          <Route path="/pipeline-builder" element={<PipelineBuilder />} />
          <Route path="/executions" element={<ExecutionList />} />
          <Route path="/execution/:id" element={<ExecutionMonitor />} />
          <Route path="/grpc-services" element={<GrpcServicesStatus />} />
          <Route path="/camera-stream" element={<CameraStream />} />
          <Route path="/thinklet" element={<ThinkletViewer />} />
          <Route path="/inspection-masters" element={<InspectionMasters />} />
          <Route path="/inspection-results" element={<InspectionResults />} />
          <Route path="/order-info" element={<OrderInfo />} />
        </Routes>
      </Container>
    </Box>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
