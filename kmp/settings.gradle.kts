import org.gradle.api.credentials.HttpHeaderCredentials
import org.gradle.authentication.http.HttpHeaderAuthentication

pluginManagement {
    repositories {
        gradlePluginPortal()
        google()
        mavenCentral()
        maven("https://maven.pkg.jetbrains.space/public/p/compose/dev")
    }
    plugins {
        id("com.android.application") version "8.12.0"
        id("com.android.library") version "8.12.0"
        kotlin("android") version "2.0.21"
        kotlin("multiplatform") version "2.0.21"
        kotlin("plugin.serialization") version "2.0.21"
        id("org.jetbrains.kotlin.plugin.compose") version "2.0.21"
        id("org.jetbrains.compose") version "1.8.2"
        id("app.cash.sqldelight") version "2.0.2"
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven("https://maven.pkg.jetbrains.space/public/p/compose/dev")
        maven("https://jitpack.io") {
            // Optional: use GitHub token for JitPack to avoid 401/rate-limit
            val token = System.getenv("JITPACK_GH_TOKEN") ?: System.getenv("GITHUB_TOKEN")
            if (!token.isNullOrBlank()) {
                credentials(HttpHeaderCredentials::class) {
                    name = "Authorization"
                    value = "Bearer $token"
                }
                authentication {
                    create<HttpHeaderAuthentication>("header")
                }
            }
        }
    }
}

rootProject.name = "imageflow-kmp"

include(":shared")
include(":androidApp")
include(":desktopApp")
include(":thinkletApp")
