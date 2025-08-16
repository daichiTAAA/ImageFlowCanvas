import org.jetbrains.compose.desktop.application.dsl.TargetFormat

plugins {
    kotlin("jvm")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.compose")
}

kotlin {
    jvmToolchain(17)
}

sourceSets {
    val main by getting
    // Map Compose Desktop JVM sources to jvmMain for consistency with MPP style
    main.apply {
        kotlin.srcDir("src/jvmMain/kotlin")
        resources.srcDir("src/jvmMain/resources")
    }
}

dependencies {
    implementation(compose.desktop.currentOs)
    implementation(compose.material3)
    implementation(compose.materialIconsExtended)
    implementation(project(":shared"))
    // JavaCV (OpenCV/FFmpeg) for cross-platform camera capture (supports macOS arm64)
    implementation("org.bytedeco:javacv-platform:1.5.10")
    // ZXing for QR decoding on desktop
    implementation("com.google.zxing:core:3.5.3")
    implementation("com.google.zxing:javase:3.5.3")
    // SLF4J simple backend to avoid NOP logger warnings
    implementation("org.slf4j:slf4j-simple:2.0.13")
}

compose.desktop {
    application {
        mainClass = "com.imageflow.kmp.desktop.MainKt"
        
        // JVM args
        jvmArgs += listOf(
            "-Dfile.encoding=UTF-8"
        )
        // Note: Compose's macOS launcher already manages main-thread startup.
        // Do not add -XstartOnFirstThread here to avoid startup conflicts.

        nativeDistributions {
            targetFormats(TargetFormat.Dmg, TargetFormat.Msi, TargetFormat.Deb)
            packageName = "ImageFlowDesktop"
            packageVersion = "1.0.0"
            // Ensure required JDK modules are present in runtime image
            modules("java.sql", "java.net.http")

            macOS {
                // Note: Compose signing with identity "-" may not be supported in all environments.
                // We wire a post-packaging ad-hoc codesign task below as a reliable fallback.
                // Allow overriding bundle ID to retrigger macOS TCC prompts in development builds
                val overrideBundleId = providers.gradleProperty("bundleIdOverride").orNull
                if (overrideBundleId != null) {
                    bundleID = overrideBundleId
                } else {
                    bundleID = "com.imageflow.kmp.desktop"
                }
                // Add camera usage description and enable Continuity Camera device type
                infoPlist {
                    // Inject raw XML keys compatible with Apple's Info.plist
                    extraKeysRawXml = """
                        <key>NSCameraUsageDescription</key>
                        <string>QRコードの読み取りのためにカメラを使用します。</string>
                        <key>NSMicrophoneUsageDescription</key>
                        <string>一部のカメラ入力で音声入力が必要な場合があります。</string>
                        <key>NSCameraUseContinuityCameraDeviceType</key>
                        <true/>
                    """.trimIndent()
        }

        // On macOS, perform ad-hoc codesign after the .app is created to improve Gatekeeper/TCC behavior
        if (org.gradle.internal.os.OperatingSystem.current().isMacOsX) {
            val appBundle = layout.buildDirectory.dir("compose/binaries/main/app/ImageFlowDesktop.app")
            tasks.register("packageAdHocSigned") {
                dependsOn("packageDistributionForCurrentOS")
                doLast {
                    exec {
                        commandLine(
                            "/usr/bin/codesign",
                            "--force",
                            "--deep",
                            "-s", "-",
                            appBundle.get().asFile.absolutePath
                        )
                    }
                }
            }
        }
    }
}

        // Ensure modules are enabled at runtime as well
        jvmArgs += listOf("--add-modules", "java.sql,java.net.http")
    }
}
