package com.example.smsgateway.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation.NavController
import com.example.smsgateway.data.models.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StatisticsScreen(navController: NavController) {
    var isLoading by remember { mutableStateOf(false) }
    var stats by remember { mutableStateOf<SystemStats?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Statistics") },
                navigationIcon = {
                    IconButton(onClick = { navController.navigateUp() }) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = { /* TODO: Implement refresh */ }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                    }
                }
            )
        }
    ) { paddingValues ->
        if (isLoading) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator()
            }
        } else if (stats == null) {
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Text("No statistics available")
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                item {
                    MemoryStatsCard(stats.memory)
                }
                
                item {
                    DatabaseStatsCard(stats.database)
                }
                
                item {
                    MessageStatsCard(stats.messages)
                }
                
                item {
                    SimCardStatsCard(stats.simCards)
                }
                
                item {
                    ComponentStatsCard(stats.components)
                }
            }
        }
    }
}

@Composable
fun MemoryStatsCard(memory: MemoryStats) {
    StatCard(
        title = "Memory Usage",
        icon = Icons.Default.Memory,
        content = {
            Column {
                LinearProgressIndicator(
                    progress = memory.percent / 100f,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 8.dp)
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("Used: ${formatBytes(memory.used)}")
                    Text("Free: ${formatBytes(memory.free)}")
                    Text("Total: ${formatBytes(memory.total)}")
                }
            }
        }
    )
}

@Composable
fun DatabaseStatsCard(database: DatabaseStats) {
    StatCard(
        title = "Database",
        icon = Icons.Default.Storage,
        content = {
            Column {
                Text("Size: ${String.format("%.2f", database.sizeMb)} MB")
                Text("Last Updated: ${database.lastUpdated}")
            }
        }
    )
}

@Composable
fun MessageStatsCard(messages: MessageStats) {
    StatCard(
        title = "Messages",
        icon = Icons.Default.Message,
        content = {
            Column {
                Text("Total: ${messages.totalMessages}")
                Text("Incoming: ${messages.incomingMessages}")
                Text("Outgoing: ${messages.outgoingMessages}")
                Text("Today: ${messages.messagesToday}")
            }
        }
    )
}

@Composable
fun SimCardStatsCard(simCards: SimCardStats) {
    StatCard(
        title = "SIM Cards",
        icon = Icons.Default.Phone,
        content = {
            Column {
                Text("Total: ${simCards.totalSims}")
                Text("Active: ${simCards.activeSims}")
                Text("Inactive: ${simCards.inactiveSims}")
                Text("Most Used: ${simCards.mostUsedSim.number}")
            }
        }
    )
}

@Composable
fun ComponentStatsCard(components: List<ComponentStats>) {
    StatCard(
        title = "Components",
        icon = Icons.Default.DeviceHub,
        content = {
            Column {
                components.forEach { component ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(component.name)
                        Text("${String.format("%.1f", component.percentage)}%")
                    }
                }
            }
        }
    )
}

@Composable
fun StatCard(
    title: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    content: @Composable () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(bottom = 16.dp)
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = null,
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = title,
                    style = MaterialTheme.typography.titleLarge
                )
            }
            content()
        }
    }
}

private fun formatBytes(bytes: Long): String {
    val units = arrayOf("B", "KB", "MB", "GB")
    var value = bytes.toDouble()
    var unitIndex = 0
    while (value >= 1024 && unitIndex < units.size - 1) {
        value /= 1024
        unitIndex++
    }
    return String.format("%.1f %s", value, units[unitIndex])
} 