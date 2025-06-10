package com.example.smsgateway.data.models

import java.util.Date

data class User(
    val id: Int,
    val username: String,
    val role: String,
    val apiKey: String
)

data class SimCard(
    val id: Int,
    val number: String,
    val status: String
)

data class Message(
    val id: Int,
    val sender: String,
    val recipient: String,
    val message: String,
    val direction: String,
    val status: String,
    val timestamp: Date,
    val senderSim: Int
)

data class SmsStatus(
    val id: Int,
    val senderNumber: String,
    val receiverNumber: String,
    val message: String,
    val status: String,
    val timestamp: Date
)

data class Log(
    val id: Int,
    val action: String,
    val details: String,
    val status: String,
    val timestamp: Date,
    val senderSim: Int
)

data class SystemStats(
    val memory: MemoryStats,
    val components: List<ComponentStats>,
    val database: DatabaseStats,
    val messages: MessageStats,
    val simCards: SimCardStats
)

data class MemoryStats(
    val total: Long,
    val used: Long,
    val free: Long,
    val percent: Float
)

data class ComponentStats(
    val name: String,
    val memoryUsage: Long,
    val percentage: Float,
    val lastUpdated: Date
)

data class DatabaseStats(
    val name: String,
    val sizeBytes: Long,
    val sizeMb: Float,
    val lastUpdated: Date
)

data class MessageStats(
    val totalMessages: Int,
    val incomingMessages: Int,
    val outgoingMessages: Int,
    val messagesToday: Int,
    val messagesPerDay: List<DailyMessageCount>
)

data class DailyMessageCount(
    val date: Date,
    val count: Int
)

data class SimCardStats(
    val totalSims: Int,
    val activeSims: Int,
    val inactiveSims: Int,
    val mostUsedSim: MostUsedSim,
    val mostUsedSims: List<MostUsedSim>
)

data class MostUsedSim(
    val number: String,
    val messageCount: Int
) 