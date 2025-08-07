#!/bin/bash

# Platform-specific build script for ImageFlowCanvas Inspection App

set -e

echo "Building ImageFlowCanvas Inspection App for multiple platforms..."

# Check for required dependencies
check_dependencies() {
    echo "Checking build dependencies..."
    
    # Check Rust
    if ! command -v cargo &> /dev/null; then
        echo "Error: Rust/Cargo not found. Please install Rust: https://rustup.rs/"
        exit 1
    fi
    
    # Check Node.js
    if ! command -v npm &> /dev/null; then
        echo "Error: Node.js/npm not found. Please install Node.js: https://nodejs.org/"
        exit 1
    fi
    
    # Check Tauri CLI
    if ! command -v tauri &> /dev/null; then
        echo "Installing Tauri CLI..."
        npm install -g @tauri-apps/cli
    fi
    
    echo "✓ All dependencies found"
}

# Platform-specific dependency checks
check_platform_deps() {
    case "$(uname -s)" in
        Linux*)
            echo "Checking Linux dependencies..."
            if ! dpkg -l | grep -q libgtk-3-dev; then
                echo "Installing Linux dependencies..."
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
            fi
            echo "✓ Linux dependencies ready"
            ;;
        Darwin*)
            echo "Checking macOS dependencies..."
            if ! command -v xcode-select &> /dev/null; then
                echo "Error: Xcode command line tools not found. Please install:"
                echo "xcode-select --install"
                exit 1
            fi
            echo "✓ macOS dependencies ready"
            ;;
        MINGW*|CYGWIN*|MSYS*)
            echo "Checking Windows dependencies..."
            echo "✓ Windows dependencies ready"
            ;;
        *)
            echo "Unknown platform: $(uname -s)"
            exit 1
            ;;
    esac
}

# Install project dependencies
install_deps() {
    echo "Installing project dependencies..."
    
    # Install npm dependencies
    npm install
    
    # Update Cargo dependencies
    cd src-tauri
    cargo fetch
    cd ..
    
    echo "✓ Dependencies installed"
}

# Build for specific target
build_target() {
    local target=$1
    echo "Building for target: $target"
    
    case $target in
        web)
            echo "Building web version..."
            npm run build
            ;;
        desktop)
            echo "Building desktop version..."
            tauri build
            ;;
        ios)
            echo "Building iOS version..."
            if [[ "$(uname -s)" != "Darwin" ]]; then
                echo "Error: iOS builds require macOS"
                exit 1
            fi
            tauri ios build
            ;;
        android)
            echo "Building Android version..."
            if ! command -v android &> /dev/null; then
                echo "Error: Android SDK not found. Please install Android Studio and SDK"
                exit 1
            fi
            tauri android build
            ;;
        all)
            echo "Building all supported targets..."
            build_target web
            build_target desktop
            if [[ "$(uname -s)" == "Darwin" ]]; then
                build_target ios
            fi
            build_target android
            ;;
        *)
            echo "Unknown target: $target"
            echo "Available targets: web, desktop, ios, android, all"
            exit 1
            ;;
    esac
    
    echo "✓ Build completed for $target"
}

# Main execution
main() {
    local target=${1:-desktop}
    
    echo "ImageFlowCanvas Inspection App Build Script"
    echo "=========================================="
    
    check_dependencies
    check_platform_deps
    install_deps
    build_target "$target"
    
    echo ""
    echo "✅ Build process completed successfully!"
    echo "Build artifacts are available in:"
    echo "  - Web: dist/"
    echo "  - Desktop: src-tauri/target/release/"
    echo "  - Mobile: src-tauri/gen/"
}

# Run main function with all arguments
main "$@"