pluginManagement {
    repositories {
        gradlePluginPortal()
        google()
        mavenCentral()
        maven("https://maven.pkg.jetbrains.space/public/p/compose/dev")
    }
    plugins {
        id("com.android.application") version "8.5.1"
        id("com.android.library") version "8.5.1"
        kotlin("android") version "2.0.21"
        kotlin("multiplatform") version "2.0.21"
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
    }
}

rootProject.name = "imageflow-kmp"

include(":shared")
include(":androidApp")
