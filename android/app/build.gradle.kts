plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// Server manzili: -PbaseUrl=... bilan o'zgartirish mumkin
val baseUrl: String = (project.findProperty("baseUrl") as String?) ?: "https://mmebel-bot.onrender.com/panel/"
val ciVersionCode: Int = (System.getenv("VERSION_CODE") ?: "1").toInt()

android {
    namespace = "uz.mmebel.sklad"
    compileSdk = 35

    defaultConfig {
        applicationId = "uz.mmebel.sklad"
        minSdk = 24
        targetSdk = 35
        versionCode = ciVersionCode
        versionName = "1.0.$ciVersionCode"
        buildConfigField("String", "BASE_URL", "\"$baseUrl\"")
    }

    signingConfigs {
        create("release") {
            val ks = System.getenv("ANDROID_KEYSTORE_PATH")
            if (ks != null && file(ks).exists()) {
                storeFile = file(ks)
                storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
                keyAlias = System.getenv("ANDROID_KEY_ALIAS")
                keyPassword = System.getenv("ANDROID_KEY_PASSWORD")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            val rel = signingConfigs.getByName("release")
            signingConfig = if (rel.storeFile != null) rel else signingConfigs.getByName("debug")
        }
    }

    buildFeatures { buildConfig = true }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("androidx.webkit:webkit:1.12.1")
}
