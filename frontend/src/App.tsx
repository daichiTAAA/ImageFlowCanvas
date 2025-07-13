import { Routes, Route } from 'react-router-dom'
import { AppBar, Toolbar, Typography, Container, Box } from '@mui/material'
import { Dashboard } from './pages/Dashboard'
import { PipelineBuilder } from './pages/PipelineBuilder'
import { ExecutionMonitor } from './pages/ExecutionMonitor'
import { Login } from './pages/Login'
import { AuthProvider } from './services/AuthContext'

function App() {
  return (
    <AuthProvider>
      <Box sx={{ flexGrow: 1 }}>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              ImageFlowCanvas
            </Typography>
          </Toolbar>
        </AppBar>
        
        <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Dashboard />} />
            <Route path="/pipeline-builder" element={<PipelineBuilder />} />
            <Route path="/execution/:id" element={<ExecutionMonitor />} />
          </Routes>
        </Container>
      </Box>
    </AuthProvider>
  )
}

export default App