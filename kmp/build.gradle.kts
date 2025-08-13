// Root build configuration for the KMP project
// Declare plugin coordinates centrally (versions come from settings.gradle.kts pluginManagement)
plugins {
    kotlin("multiplatform") apply false
    kotlin("android") apply false
    id("com.android.application") apply false
    id("com.android.library") apply false
    id("org.jetbrains.kotlin.plugin.compose") apply false
    id("org.jetbrains.compose") apply false
    id("app.cash.sqldelight") apply false
    kotlin("plugin.serialization") apply false
}

// (Optional) common repositories for all subprojects if needed
// subprojects {
//     repositories {
//         google()
//         mavenCentral()
//         maven("https://maven.pkg.jetbrains.space/public/p/compose/dev")
//     }
// }
