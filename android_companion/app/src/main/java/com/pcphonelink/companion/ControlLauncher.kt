package com.pcphonelink.companion

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext

object ControlLauncher {
    suspend fun waitForReachable(
        controlUrl: String,
        timeoutMs: Long,
        pollIntervalMs: Long = 2_000,
        initialDelayMs: Long = 0,
    ): Boolean {
        return withContext(Dispatchers.IO) {
            if (initialDelayMs > 0) {
                delay(initialDelayMs)
            }
            val deadline = System.currentTimeMillis() + timeoutMs
            while (System.currentTimeMillis() < deadline) {
                if (isReachable(controlUrl)) {
                    return@withContext true
                }
                delay(pollIntervalMs)
            }
            return@withContext false
        }
    }

    private fun isReachable(controlUrl: String): Boolean {
        val connection = openConnection(controlUrl, method = "GET")
        return try {
            val statusCode = connection.responseCode
            statusCode in 200..499
        } catch (_: IOException) {
            false
        } finally {
            connection.disconnect()
        }
    }

    private fun openConnection(rawUrl: String, method: String): HttpURLConnection {
        val connection = (URL(rawUrl).openConnection() as HttpURLConnection)
        connection.requestMethod = method
        connection.instanceFollowRedirects = false
        connection.connectTimeout = 5_000
        connection.readTimeout = 5_000
        connection.setRequestProperty("User-Agent", "PC Phone Link Companion")
        return connection
    }
}
