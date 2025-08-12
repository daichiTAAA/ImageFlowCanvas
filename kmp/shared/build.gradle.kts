// Kotlin Multiplatform shared module (scaffold wired with targets and deps)
plugins {
    kotlin("multiplatform")
    id("com.android.library")
    id("org.jetbrains.compose")
    id("app.cash.sqldelight")
}

kotlin {
    // Targets
    jvm("desktop")
    androidTarget()

    iosX64()
    iosArm64()
    iosSimulatorArm64()

    sourceSets {
        val commonMain by getting {
            dependencies {
                // Compose core (runtime/foundation)
                implementation(compose.runtime)
                implementation(compose.foundation)

                // Coroutines
                implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:${'$'}{property("coroutines.version")}")

                // Ktor client
                implementation("io.ktor:ktor-client-core:${'$'}{property("ktor.version")}")
                implementation("io.ktor:ktor-client-websockets:${'$'}{property("ktor.version")}")
                implementation("io.ktor:ktor-client-content-negotiation:${'$'}{property("ktor.version")}")
                implementation("io.ktor:ktor-serialization-kotlinx-json:${'$'}{property("ktor.version")}")

                // SQLDelight runtime (optional to wire driver per platform)
                implementation("app.cash.sqldelight:runtime:${'$'}{property("sqldelight.version")}")
                implementation("app.cash.sqldelight:coroutines-extensions:${'$'}{property("sqldelight.version")}")

                // Kotlin test API for common tests
                implementation(kotlin("test"))
            }
        }

        val commonTest by getting {
            dependencies {
                implementation(kotlin("test"))
                implementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:${'$'}{property("coroutines.version")}")
            }
        }

        val androidMain by getting {
            dependencies {
                implementation("io.ktor:ktor-client-okhttp:${'$'}{property("ktor.version")}")
                // SQLDelight Android driver can be added when DB schema is defined
                // implementation("app.cash.sqldelight:android-driver:${'$'}{property("sqldelight.version")}")
            }
        }
        val androidUnitTest by getting {
            dependencies {
                implementation(kotlin("test"))
            }
        }

        val desktopMain by getting {
            dependencies {
                implementation("io.ktor:ktor-client-java:${'$'}{property("ktor.version")}")
                // SQLDelight JDBC driver example
                // implementation("app.cash.sqldelight:sqlite-driver:${'$'}{property("sqldelight.version")}")
                implementation(compose.desktop.currentOs)
                implementation(compose.ui)
                implementation("app.cash.sqldelight:sqlite-driver:${'$'}{property("sqldelight.version")}")
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
                implementation("io.ktor:ktor-client-darwin:${'$'}{property("ktor.version")}")
                implementation("app.cash.sqldelight:native-driver:${'$'}{property("sqldelight.version")}")
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
    compileSdk = (property("android.compileSdk") as String).toInt()
    defaultConfig {
        minSdk = (property("android.minSdk") as String).toInt()
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
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
