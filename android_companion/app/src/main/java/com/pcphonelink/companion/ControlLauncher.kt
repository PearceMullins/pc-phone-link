package com.pcphonelink.companion

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import org.json.JSONObject

object ControlLauncher {
    suspend fun startControls(startUrl: String) {
        withContext(Dispatchers.IO) {
            val connection = openConnection(startUrl, method = "POST")
            try {
                connection.doOutput = true
                connection.outputStream.use { }
                val statusCode = connection.responseCode
                if (statusCode in 200..299) {
                    return@withContext
                }
                throw IOException(readFailureMessage(connection, statusCode))
            } finally {
                connection.disconnect()
            }
        }
    }

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

    private fun readFailureMessage(connection: HttpURLConnection, statusCode: Int): String {
        val body = try {
            val stream = connection.errorStream ?: connection.inputStream
            stream?.bufferedReader()?.use { it.readText() }?.trim().orEmpty()
        } catch (_: IOException) {
            ""
        }
        if (body.isBlank()) {
            return "The launcher returned HTTP $statusCode."
        }

        return try {
            val parsed = JSONObject(body)
            parsed.optString("detail").ifBlank { parsed.optString("message") }.ifBlank { body }
        } catch (_: Exception) {
            body
        }
    }
}
