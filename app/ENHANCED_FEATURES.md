# Enhanced ImageFlowCanvas Inspection Application

This document describes the enhanced features implemented in the Tauri-based cross-platform inspection application.

## New Features Implemented

### 1. Platform-Specific Build Support

The application now supports building on multiple platforms with proper dependency management:

- **Linux**: GTK development libraries, WebKit2GTK, AppIndicator support
- **macOS**: Xcode command line tools integration
- **Windows**: Native Windows API support
- **iOS**: AVFoundation and CoreImage frameworks integration
- **Android**: Camera permissions and Android SDK integration

**Build Script**: `build.sh`
```bash
# Build for all platforms
./build.sh all

# Build for specific platform
./build.sh desktop
./build.sh ios
./build.sh android
```

### 2. Real Camera Integration

Enhanced camera functionality using web APIs with fallback to Tauri native integration:

**Features**:
- Real camera preview using react-webcam
- Camera switching (front/back)
- Resolution configuration (Full HD, HD, SD)
- Flash control
- Image quality settings
- Real-time image capture

**Implementation**: `CameraCapture.tsx`
- Webcam preview with overlay targeting
- Tauri backend integration for image storage
- Platform-specific camera optimization

### 3. Actual QR Code Scanning

Implemented real QR code scanning with multiple options:

**Features**:
- Real-time camera-based QR scanning using jsQR library
- Continuous scanning with visual feedback
- Tauri plugin fallback for native QR scanning
- Manual input option for offline scenarios
- QR code validation and parsing

**Implementation**: `QRCodeScanner.tsx`
- Browser-based QR scanning using webcam
- QR code detection with visual targeting overlay
- Backend QR data parsing and validation

### 4. Backend API Integration

Complete integration with ImageFlowCanvas pipeline system:

**Features**:
- Real HTTP client for pipeline communication
- Configurable API endpoints
- Authentication with JWT tokens
- Request/response handling with error management
- Offline operation support

**Implementation**: `pipeline.rs`
- `PipelineClient` for API communication
- Real pipeline execution with progress tracking
- Result persistence and retrieval

### 5. SQLite Database Schema

Comprehensive offline storage implementation:

**Tables**:
- `users` - User authentication and profiles
- `inspection_targets` - QR code targets and product information
- `inspection_sessions` - Inspection workflow sessions
- `inspection_images` - Captured image metadata
- `ai_inspection_results` - AI pipeline results
- `human_verification_results` - Human review outcomes
- `system_config` - Application configuration

**Implementation**: `database.rs`
- SQLx integration with compile-time query validation
- Migration support for schema evolution
- Connection pooling and transaction management

### 6. Authentication System

Complete user authentication and authorization:

**Features**:
- JWT-based authentication
- User registration and login
- Password hashing with bcrypt
- Role-based access control
- Token expiration and refresh
- Persistent login sessions

**Implementation**:
- `auth.rs` - Backend authentication logic
- `AuthContext.tsx` - Frontend authentication state management
- `LoginComponent.tsx` - User interface for login/registration

## Technical Architecture

### Frontend Stack
- **React 18** with TypeScript
- **Material-UI 6** for consistent design
- **React Context** for state management
- **Webcam API** for camera integration
- **jsQR** for QR code processing

### Backend Stack
- **Rust** with Tauri 2.0
- **SQLx** for database operations
- **Tokio** for async runtime
- **JWT** for authentication
- **Reqwest** for HTTP client

### Platform Integration
- **Cross-platform** binary compilation
- **Native permissions** for camera and storage
- **Platform-specific** optimizations
- **Offline-first** design with sync capabilities

## Configuration

### Environment Variables
```bash
DATABASE_URL=sqlite:inspection.db
API_ENDPOINT=https://api.imageflowcanvas.com
JWT_SECRET=your-secret-key-here
```

### Tauri Configuration
Platform-specific settings in `tauri.conf.json`:
- Camera permissions for mobile platforms
- File system access for image storage
- Network access for API communication
- Database access for offline storage

## Usage

### Development
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Production Deployment
```bash
# Build platform-specific binaries
./build.sh all

# Artifacts location:
# - Desktop: src-tauri/target/release/
# - Mobile: src-tauri/gen/
```

## Security Considerations

- JWT tokens with expiration
- Password hashing with bcrypt
- HTTPS for API communication
- Secure local storage encryption
- Platform-specific permission requests

## Future Enhancements

- Offline sync queue implementation
- Advanced AI model integration
- Real-time collaboration features
- Enhanced reporting and analytics
- Multi-language support expansion