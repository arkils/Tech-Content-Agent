import java.util.Properties

// Load local.properties for LAMBDA_BASE_URL and HITL_SECRET.
// These values are injected into BuildConfig at compile time and are never
// committed to source control. Copy local.properties.example and fill in the values.
val localProps = Properties().also { props ->
    val f = rootProject.file("local.properties")
    if (f.exists()) props.load(f.inputStream())
}

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.google.services)
}

android {
    namespace = "com.techcontent.agent"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.techcontent.agent"
        minSdk = 26
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"

        // Injected from local.properties — never hard-code here.
        buildConfigField(
            "String",
            "LAMBDA_BASE_URL",
            "\"${localProps.getProperty("LAMBDA_BASE_URL", "https://REPLACE_ME.lambda-url.us-east-1.on.aws")}\""
        )
        buildConfigField(
            "String",
            "HITL_SECRET",
            "\"${localProps.getProperty("HITL_SECRET", "")}\""
        )
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    buildFeatures {
        buildConfig = true
        viewBinding = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.constraintlayout)

    // Jetpack Lifecycle
    implementation(libs.lifecycle.viewmodel.ktx)
    implementation(libs.lifecycle.livedata.ktx)

    // Navigation
    implementation(libs.navigation.fragment.ktx)
    implementation(libs.navigation.ui.ktx)

    // Coroutines
    implementation(libs.kotlinx.coroutines.android)

    // Networking
    implementation(libs.retrofit)
    implementation(libs.retrofit.converter.gson)
    implementation(libs.okhttp)
    implementation(libs.okhttp.logging)
    implementation(libs.gson)

    // Firebase (BOM manages versions)
    implementation(platform(libs.firebase.bom))
    implementation(libs.firebase.messaging.ktx)
}
