# ImageFlowCanvas Inspection App

Cross-platform inspection application built with Tauri, React, and TypeScript. This application provides a comprehensive inspection workflow with AI-powered pipeline processing, QR code scanning, camera integration, and offline capabilities.

## Architecture

- **Frontend**: React 18 + TypeScript + Material UI + Vite
- **Backend**: Rust + Tauri 2.0
- **Database**: SQLite with offline support
- **Features**: Camera capture, QR code scanning, AI pipeline integration, authentication

## Prerequisites

### General Requirements

- **Node.js** (v18 or higher) - [Download](https://nodejs.org/)
- **Rust** (latest stable) - [Install via rustup](https://rustup.rs/)
- **Tauri CLI** (will be installed automatically)

### Platform-Specific Dependencies

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y \
    libgtk-3-dev \
    libwebkit2gtk-4.0-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev \
    pkg-config \
    build-essential \
    curl \
    wget \
    libssl-dev \
    libsqlite3-dev
```

#### macOS
```bash
# Install Xcode command line tools
xcode-select --install

# For iOS development (optional)
# Install Xcode from App Store
```

#### Windows
- Visual Studio Build Tools or Visual Studio Community
- WebView2 (usually pre-installed on Windows 10/11)

#### Mobile Development (Optional)

**iOS** (macOS only):
- Xcode and iOS SDK
- iOS Simulator or physical device

**Android**:
- Android Studio
- Android SDK (API level 24 or higher)
- Android NDK

## Development Setup

### 1. Clone and Install Dependencies

```bash
# Navigate to the app directory
cd ImageFlowCanvas/app

# Install Node.js dependencies
npm install

# Install Rust dependencies
cd src-tauri
cargo fetch
cd ..
```

### 2. Environment Setup

Create a `.env` file in the app root (optional):
```env
# Development environment variables
VITE_API_BASE_URL=http://localhost:8080
VITE_DEBUG_MODE=true
```

### 3. Database Setup

The SQLite database will be automatically initialized on first run. Migration files are located in `src-tauri/migrations/`.

## Development Commands

### Start Development Server

```bash
# Start both frontend and backend in development mode
npm run tauri dev

# Or start frontend only (for web development)
npm run dev
```

This will:
- Start the Vite dev server for hot-reloading
- Launch the Tauri application window
- Enable hot-reload for both frontend and backend changes

### Frontend Development

```bash
# Start Vite dev server only
npm run dev

# Build frontend for production
npm run build

# Preview production build
npm run preview
```

### Backend Development

```bash
cd src-tauri

# Check Rust code
cargo check

# Run tests
cargo test

# Format code
cargo fmt

# Lint code
cargo clippy
```

## Build Instructions

### Using the Build Script (Recommended)

The project includes a comprehensive build script that handles platform-specific dependencies:

```bash
# Make the script executable
chmod +x build.sh

# Build for desktop (default)
./build.sh

# Build for specific platforms
./build.sh web      # Web version
./build.sh desktop  # Desktop application
./build.sh ios      # iOS (macOS only)
./build.sh android  # Android
./build.sh all      # All supported platforms
```

### Manual Build Commands

#### Desktop Application

```bash
# Development build
npm run tauri build

# Release build with optimizations
npm run tauri build -- --release
```

#### Web Application

```bash
# Build web version
npm run build
```

#### Mobile Applications

```bash
# iOS (macOS only)
npm run tauri ios build

# Android
npm run tauri android build
```

## Build Outputs

After successful builds, you'll find the artifacts in:

- **Web**: `dist/` directory
- **Desktop**: `src-tauri/target/release/` directory
- **Mobile**: `src-tauri/gen/` directory

### Desktop Binaries

- **Linux**: `src-tauri/target/release/imageflowcanvas-inspection-app`
- **macOS**: `src-tauri/target/release/bundle/macos/ImageFlowCanvas Inspection.app`
- **Windows**: `src-tauri/target/release/imageflowcanvas-inspection-app.exe`

## Testing

### Frontend Tests

```bash
# Run frontend tests (if configured)
npm test
```

### Backend Tests

```bash
cd src-tauri

# Run Rust unit tests
cargo test

# Run with output
cargo test -- --nocapture
```

### Integration Testing

Test the application manually by:

1. Starting the development server: `npm run tauri dev`
2. Testing QR code scanning functionality
3. Testing camera capture
4. Testing AI pipeline integration
5. Testing offline database operations

## Debugging

### Development Tools

- **Frontend**: Use browser dev tools (F12 in the Tauri window)
- **Backend**: Use `println!` statements or `log` crate
- **Database**: Use SQLite browser tools to inspect `app.db`

### Logging

Backend logs are available in:
- **Linux**: `~/.local/share/com.imageflowcanvas.inspection/logs/`
- **macOS**: `~/Library/Application Support/com.imageflowcanvas.inspection/logs/`
- **Windows**: `%APPDATA%\com.imageflowcanvas.inspection\logs\`

### Common Issues

1. **Camera not working**: Ensure camera permissions are granted
2. **QR scanning fails**: Check lighting conditions and QR code quality
3. **Database errors**: Check SQLite file permissions
4. **Build failures**: Ensure all platform dependencies are installed

## Deployment

### Desktop Application

1. Build the application: `./build.sh desktop`
2. Distribute the generated binary or installer
3. For auto-updates, configure Tauri updater in `tauri.conf.json`

### Web Application

1. Build: `npm run build`
2. Deploy the `dist/` folder to your web server
3. Configure HTTPS for camera access

### Mobile Applications

1. Build for target platform: `./build.sh ios` or `./build.sh android`
2. Follow platform-specific deployment guides
3. Submit to App Store/Play Store as needed

## Configuration

### Application Configuration

Main configuration is in `src-tauri/tauri.conf.json`:

- App metadata and versioning
- Window settings and permissions
- Plugin configurations
- Build targets and bundling options

### Database Configuration

SQLite settings are configured in `src-tauri/src/database.rs`. Migration files in `src-tauri/migrations/` handle schema updates.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly on target platforms
5. Submit a pull request

## IDE Setup

### Recommended Setup

- **VS Code** with extensions:
  - [Tauri](https://marketplace.visualstudio.com/items?itemName=tauri-apps.tauri-vscode)
  - [rust-analyzer](https://marketplace.visualstudio.com/items?itemName=rust-lang.rust-analyzer)
  - [ES7+ React/Redux/React-Native snippets](https://marketplace.visualstudio.com/items?itemName=dsznajder.es7-react-js-snippets)
  - [TypeScript Importer](https://marketplace.visualstudio.com/items?itemName=pmneo.tsimporter)

### Alternative IDEs

- **IntelliJ IDEA** with Rust and TypeScript plugins
- **Vim/Neovim** with appropriate LSP configurations
- **Sublime Text** with LSP and syntax packages

## License

[LICENSE](../LICENSE) - See the project license file for details.
