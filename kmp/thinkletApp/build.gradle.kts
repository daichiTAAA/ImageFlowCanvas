plugins {
    id("com.android.application")
    kotlin("android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.compose")
}

val androidCompileSdk = (findProperty("android.compileSdk") as String).toInt()
val androidMinSdk = (findProperty("android.minSdk") as String).toInt()

android {
    namespace = "com.imageflow.thinklet.app"
    compileSdk = androidCompileSdk

    defaultConfig {
        applicationId = "com.imageflow.thinklet.app"
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

    buildFeatures { compose = true }

    packaging { resources { excludes += "/META-INF/{AL2.0,LGPL2.1}" } }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    // Single-variant app (no flavors). WHIP implementation is the default.

    sourceSets {
        getByName("main") {
            java.srcDirs("src/main/kotlin", "src/whip/kotlin")
            res.srcDirs("src/main/res")
            manifest.srcFile("src/main/AndroidManifest.xml")
        }
    }
}

kotlin { jvmToolchain(17) }

dependencies {
    // optional shared module (comment in if needed)
    // implementation(project(":shared"))

    // Compose (JetBrains Compose)
    implementation(compose.ui)
    implementation(compose.foundation)
    implementation(compose.material3)
    implementation(compose.materialIconsExtended)

    // Android glue
    implementation("androidx.activity:activity-compose:1.9.1")

    // CameraX (optional: used for camera control by rtmp lib under the hood)
    implementation("androidx.camera:camera-core:1.3.4")
    implementation("androidx.camera:camera-camera2:1.3.4")
    implementation("androidx.camera:camera-lifecycle:1.3.4")
    implementation("androidx.camera:camera-view:1.3.4")

    // Stream WebRTC SDK (brings org.webrtc transitively) + OkHttp for WHIP signaling
    implementation("io.getstream:stream-webrtc-android:1.3.8")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Coroutines & lifecycle helpers for async control/state flows
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")

    // JSON support for backend payloads
    implementation("com.google.code.gson:gson:2.10.1")

    // THINKLET audio SDKs (local AARs)
    implementation(files("libs/sdk-audio-0.1.6.aar"))
    implementation(files("libs/sdk-utils-1.0.1.aar"))
}
