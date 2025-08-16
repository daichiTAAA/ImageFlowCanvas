import org.jetbrains.compose.desktop.application.dsl.TargetFormat
import com.google.protobuf.gradle.*

plugins {
    kotlin("jvm")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.compose")
    id("com.google.protobuf") version "0.9.4"
}

kotlin { jvmToolchain(17) }

sourceSets {
    val main by getting
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

    implementation("org.bytedeco:javacv-platform:1.5.10")
    implementation("com.google.zxing:core:3.5.3")
    implementation("com.google.zxing:javase:3.5.3")
    implementation("org.slf4j:slf4j-simple:2.0.13")

    val grpcVersion = "1.65.1"
    val protobufVersion = "3.25.3"
    val grpcKotlinVersion = "1.4.1"
    implementation("io.grpc:grpc-netty-shaded:$grpcVersion")
    implementation("io.grpc:grpc-protobuf:$grpcVersion")
    implementation("io.grpc:grpc-stub:$grpcVersion")
    implementation("com.google.protobuf:protobuf-kotlin:$protobufVersion")
    implementation("io.grpc:grpc-kotlin-stub:$grpcKotlinVersion")
}

compose.desktop {
    application {
        mainClass = "com.imageflow.kmp.desktop.MainKt"
        jvmArgs += listOf("-Dfile.encoding=UTF-8")

        nativeDistributions {
            targetFormats(TargetFormat.Dmg, TargetFormat.Msi, TargetFormat.Deb)
            packageName = "ImageFlowDesktop"
            packageVersion = "1.0.0"
            modules("java.sql", "java.net.http")
            macOS {
                val overrideBundleId = providers.gradleProperty("bundleIdOverride").orNull
                bundleID = overrideBundleId ?: "com.imageflow.kmp.desktop"
                infoPlist {
                    extraKeysRawXml = """
                        <key>NSCameraUsageDescription</key>
                        <string>QRコードの読み取りのためにカメラを使用します。</string>
                        <key>NSMicrophoneUsageDescription</key>
                        <string>一部のカメラ入力で音声入力が必要な場合があります。</string>
                        <key>NSCameraUseContinuityCameraDeviceType</key>
                        <true/>
                    """.trimIndent()
                }
            }
        }

        // Ensure modules are enabled at runtime as well
        jvmArgs += listOf("--add-modules", "java.sql,java.net.http")
    }
}

// Place .proto files under src/main/proto for this module (created below)
protobuf {
    protoc { artifact = "com.google.protobuf:protoc:3.25.3" }
    plugins {
        create("grpc") { artifact = "io.grpc:protoc-gen-grpc-java:1.65.1" }
        create("grpckt") { artifact = "io.grpc:protoc-gen-grpc-kotlin:1.4.1:jdk8@jar" }
    }
    generateProtoTasks {
        all().forEach { task ->
            task.plugins.apply {
                create("grpc")
                create("grpckt")
            }
            task.builtins {
                register("kotlin") {}
            }
        }
    }
}

// Ad-hoc signing helper (optional)
if (org.gradle.internal.os.OperatingSystem.current().isMacOsX) {
    val appBundle = layout.buildDirectory.dir("compose/binaries/main/app/ImageFlowDesktop.app")
    tasks.register("packageAdHocSigned") {
        dependsOn(":desktopApp:packageDistributionForCurrentOS")
        doLast {
            exec {
                commandLine("/usr/bin/codesign", "--force", "--deep", "-s", "-", appBundle.get().asFile.absolutePath)
            }
        }
    }
}
