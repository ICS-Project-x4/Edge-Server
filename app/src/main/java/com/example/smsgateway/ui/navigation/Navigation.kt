package com.example.smsgateway.ui.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.example.smsgateway.ui.screens.*

sealed class Screen(val route: String) {
    object Login : Screen("login")
    object Dashboard : Screen("dashboard")
    object SendSms : Screen("send_sms")
    object Inbox : Screen("inbox")
    object Outbox : Screen("outbox")
    object Statistics : Screen("statistics")
    object Account : Screen("account")
}

@Composable
fun Navigation(navController: NavHostController) {
    NavHost(navController = navController, startDestination = Screen.Login.route) {
        composable(Screen.Login.route) {
            LoginScreen(navController)
        }
        composable(Screen.Dashboard.route) {
            DashboardScreen(navController)
        }
        composable(Screen.SendSms.route) {
            SendSmsScreen(navController)
        }
        composable(Screen.Inbox.route) {
            InboxScreen(navController)
        }
        composable(Screen.Outbox.route) {
            OutboxScreen(navController)
        }
        composable(Screen.Statistics.route) {
            StatisticsScreen(navController)
        }
        composable(Screen.Account.route) {
            AccountScreen(navController)
        }
    }
} 