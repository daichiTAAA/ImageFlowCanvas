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
    // Compose Compiler は Kotlin 2.0 の compose plugin により管理されます

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    implementation(project(":shared"))

    // Compose（JetBrains Composeを利用）
    implementation(compose.ui)
    implementation(compose.foundation)

    // Android 用セットアップ
    implementation("androidx.activity:activity-compose:1.9.1")
}
