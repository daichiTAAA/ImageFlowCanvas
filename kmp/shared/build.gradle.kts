// Kotlin Multiplatform shared module (scaffold wired with targets and deps)
plugins {
    kotlin("multiplatform")
    id("com.android.library")
    id("org.jetbrains.kotlin.plugin.compose")
    id("org.jetbrains.compose")
    id("app.cash.sqldelight")
}

// Resolve versions from gradle.properties
val coroutinesVersion = findProperty("coroutines.version") as String
val ktorVersion = findProperty("ktor.version") as String
val sqldelightVersion = findProperty("sqldelight.version") as String
val androidCompileSdk = (findProperty("android.compileSdk") as String).toInt()
val androidMinSdk = (findProperty("android.minSdk") as String).toInt()

kotlin {
    // Targets
    jvm("desktop")
    androidTarget()

    iosX64()
    iosArm64()
    iosSimulatorArm64()

    // Use JDK 17 toolchain to match Android's Java target
    jvmToolchain(17)

    sourceSets {
        val commonMain by getting {
            dependencies {
                // Compose core (runtime/foundation)
                implementation(compose.runtime)
                implementation(compose.foundation)

                // Coroutines
                implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:$coroutinesVersion")

                // Ktor client
                implementation("io.ktor:ktor-client-core:$ktorVersion")
                implementation("io.ktor:ktor-client-websockets:$ktorVersion")
                implementation("io.ktor:ktor-client-content-negotiation:$ktorVersion")
                implementation("io.ktor:ktor-serialization-kotlinx-json:$ktorVersion")
                implementation("io.ktor:ktor-client-logging:$ktorVersion")

                // SQLDelight runtime (optional to wire driver per platform)
                implementation("app.cash.sqldelight:runtime:$sqldelightVersion")
                implementation("app.cash.sqldelight:coroutines-extensions:$sqldelightVersion")

                // Kotlin test API for common tests
                implementation(kotlin("test"))
            }
        }

        val commonTest by getting {
            dependencies {
                implementation(kotlin("test"))
                implementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:$coroutinesVersion")
            }
        }

        val androidMain by getting {
            dependencies {
                implementation("io.ktor:ktor-client-okhttp:$ktorVersion")
                // SQLDelight Android driver
                implementation("app.cash.sqldelight:android-driver:$sqldelightVersion")
            }
        }
        val androidUnitTest by getting {
            dependencies {
                implementation(kotlin("test"))
            }
        }

        val desktopMain by getting {
            dependencies {
                implementation("io.ktor:ktor-client-java:$ktorVersion")
                // SQLDelight JDBC driver example
                // implementation("app.cash.sqldelight:sqlite-driver:$sqldelightVersion")
                implementation(compose.desktop.currentOs)
                implementation(compose.ui)
                implementation("app.cash.sqldelight:sqlite-driver:$sqldelightVersion")
            }
        }

        val iosX64Main by getting
        val iosArm64Main by getting
        val iosSimulatorArm64Main by getting

        val iosMain by creating {
            dependsOn(commonMain)
            iosX64Main.dependsOn(this)
            iosArm64Main.dependsOn(this)
            iosSimulatorArm64Main.dependsOn(this)
            dependencies {
                implementation("io.ktor:ktor-client-darwin:$ktorVersion")
                implementation("app.cash.sqldelight:native-driver:$sqldelightVersion")
            }
        }

        val iosX64Test by getting
        val iosArm64Test by getting
        val iosSimulatorArm64Test by getting
        val iosTest by creating {
            dependsOn(commonTest)
            iosX64Test.dependsOn(this)
            iosArm64Test.dependsOn(this)
            iosSimulatorArm64Test.dependsOn(this)
        }

        // Non-standard source sets (organizational): thinkletMain, handheldMain
        // These can be wired to appropriate targets later if needed.
    }
}

android {
    namespace = "com.imageflow.kmp"
    compileSdk = androidCompileSdk
    defaultConfig {
        minSdk = androidMinSdk
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

sqldelight {
    databases {
        create("AppDatabase") {
            packageName.set("com.imageflow.kmp.db")
            // schemaOutputDirectory and migrationOutputDirectory can be configured as needed
        }
    }
}
