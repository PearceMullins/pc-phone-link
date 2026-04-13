package com.pcphonelink.companion

import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.util.Locale
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext

object WakeOnLanSender {
    suspend fun send(config: CompanionConfig, repeatCount: Int = 3) {
        withContext(Dispatchers.IO) {
            val macBytes = normalizeMac(config.macAddress)
            val payload = ByteArray(6 + (macBytes.size * 16))
            payload.fill(0xFF.toByte(), 0, 6)
            for (index in 0 until 16) {
                macBytes.copyInto(payload, destinationOffset = 6 + (index * macBytes.size))
            }

            val targetAddress = InetAddress.getByName(config.broadcastAddress)
            DatagramSocket().use { socket ->
                socket.broadcast = true
                val packet = DatagramPacket(payload, payload.size, targetAddress, config.wolPort)
                repeat(repeatCount.coerceAtLeast(1)) { attempt ->
                    socket.send(packet)
                    if (attempt < repeatCount - 1) {
                        delay(150)
                    }
                }
            }
        }
    }

    private fun normalizeMac(rawMac: String): ByteArray {
        val cleaned = rawMac.filter { character -> character.isLetterOrDigit() }.uppercase(Locale.US)
        require(cleaned.length == 12) { "Enter the MAC address as 12 hexadecimal characters." }
        require(cleaned.all { it in "0123456789ABCDEF" }) { "The MAC address contains invalid characters." }
        return cleaned
            .chunked(2)
            .map { chunk -> chunk.toInt(16).toByte() }
            .toByteArray()
    }
}
