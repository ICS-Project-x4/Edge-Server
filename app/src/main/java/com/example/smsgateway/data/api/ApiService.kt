package com.example.smsgateway.data.api

import com.example.smsgateway.data.models.*
import retrofit2.Response
import retrofit2.http.*

interface ApiService {
    @POST("api/auth")
    suspend fun login(
        @Body credentials: Map<String, String>
    ): Response<User>

    @GET("api/sim-cards")
    suspend fun getSimCards(
        @Header("X-API-Key") apiKey: String
    ): Response<List<SimCard>>

    @POST("api/sim-cards")
    suspend fun addSimCard(
        @Header("X-API-Key") apiKey: String,
        @Body simCard: Map<String, String>
    ): Response<SimCard>

    @PUT("api/sim-cards/{simId}")
    suspend fun updateSimCard(
        @Header("X-API-Key") apiKey: String,
        @Path("simId") simId: Int,
        @Body updates: Map<String, String>
    ): Response<SimCard>

    @DELETE("api/sim-cards/{simId}")
    suspend fun deleteSimCard(
        @Header("X-API-Key") apiKey: String,
        @Path("simId") simId: Int
    ): Response<Unit>

    @POST("api/sms")
    suspend fun sendSms(
        @Header("X-API-Key") apiKey: String,
        @Body message: Map<String, String>
    ): Response<Message>

    @GET("api/sms/inbox")
    suspend fun getInbox(
        @Header("X-API-Key") apiKey: String
    ): Response<List<Message>>

    @GET("api/sms/outbox")
    suspend fun getOutbox(
        @Header("X-API-Key") apiKey: String
    ): Response<List<Message>>

    @GET("api/statistics")
    suspend fun getStatistics(
        @Header("X-API-Key") apiKey: String
    ): Response<SystemStats>

    @GET("api/logs")
    suspend fun getLogs(
        @Header("X-API-Key") apiKey: String
    ): Response<List<Log>>

    @POST("api/generate-api-key")
    suspend fun generateApiKey(
        @Header("Authorization") token: String
    ): Response<Map<String, String>>
} 