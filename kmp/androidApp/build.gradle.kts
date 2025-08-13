plugins {
    id("com.android.application")
    kotlin("android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.compose")
}

android {
    namespace = "com.imageflow.kmp.app"
    compileSdk = (property("android.compileSdk") as String).toInt()

    defaultConfig {
        applicationId = "com.imageflow.kmp.app"
        minSdk = (property("android.minSdk") as String).toInt()
        targetSdk = (property("android.compileSdk") as String).toInt()
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
