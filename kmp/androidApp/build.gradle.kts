plugins {
    id("com.android.application")
    kotlin("android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.compose")
}

// Resolve Android SDK levels from gradle.properties
val androidCompileSdk = (findProperty("android.compileSdk") as String).toInt()
val androidMinSdk = (findProperty("android.minSdk") as String).toInt()

android {
    namespace = "com.imageflow.kmp.app"
    compileSdk = androidCompileSdk

    defaultConfig {
        applicationId = "com.imageflow.kmp.app"
        minSdk = androidMinSdk
        targetSdk = androidCompileSdk
        versionCode = 1
        versionName = "0.1.0"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }

    buildFeatures {
        compose = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    jvmToolchain(17)
}

// Kotlin toolchain: use JDK 17 to match shared module

dependencies {
    implementation(project(":shared"))

    // Compose（JetBrains Composeを利用）
    implementation(compose.ui)
    implementation(compose.foundation)
    implementation(compose.material3)
    implementation(compose.materialIconsExtended)

    // Android 用セットアップ
    implementation("androidx.activity:activity-compose:1.9.1")

    // CameraX
    implementation("androidx.camera:camera-core:1.3.4")
    implementation("androidx.camera:camera-camera2:1.3.4")
    implementation("androidx.camera:camera-lifecycle:1.3.4")
    implementation("androidx.camera:camera-view:1.3.4")

    // ML Kit Barcode Scanning
    implementation("com.google.mlkit:barcode-scanning:17.2.0")
}
