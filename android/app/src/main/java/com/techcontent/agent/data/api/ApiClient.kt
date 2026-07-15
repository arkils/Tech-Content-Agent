package com.techcontent.agent.data.api

import com.techcontent.agent.BuildConfig
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Singleton Retrofit client for the Approval API Lambda Function URL.
 *
 * The base URL and shared secret are injected from [BuildConfig], which
 * reads them from `local.properties` at compile time (never from source control).
 *
 * Every request automatically includes the `x-hitl-secret` header required
 * by the Approval API Lambda for authentication.
 */
object ApiClient {

    val approvalApiService: ApprovalApiService by lazy { buildService() }

    private fun buildService(): ApprovalApiService {
        val loggingInterceptor = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }

        val client = OkHttpClient.Builder()
            .addInterceptor { chain ->
                val request = chain.request().newBuilder()
                    .addHeader("x-hitl-secret", BuildConfig.HITL_SECRET)
                    .addHeader("Content-Type", "application/json")
                    .build()
                chain.proceed(request)
            }
            .addInterceptor(loggingInterceptor)
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()

        return Retrofit.Builder()
            .baseUrl(BuildConfig.LAMBDA_BASE_URL.trimEnd('/') + "/")
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApprovalApiService::class.java)
    }
}
