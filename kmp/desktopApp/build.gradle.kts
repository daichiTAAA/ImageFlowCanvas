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
}

compose.desktop {
    application {
        mainClass = "com.imageflow.kmp.desktop.MainKt"
        
        // JVMの引数を明示的に設定
        jvmArgs += listOf(
            "-Dfile.encoding=UTF-8",
            "--add-opens", "java.base/java.net=ALL-UNNAMED",
            "--add-opens", "java.base/java.net.http=ALL-UNNAMED"
        )

        nativeDistributions {
            targetFormats(TargetFormat.Dmg, TargetFormat.Msi, TargetFormat.Deb)
            packageName = "ImageFlowDesktop"
            packageVersion = "1.0.0"
            // Ensure required JDK modules are present in runtime image
            modules("java.sql", "java.net.http")
        }

        // Ensure modules are enabled at runtime as well
        jvmArgs += listOf("--add-modules", "java.sql,java.net.http")
    }
}
