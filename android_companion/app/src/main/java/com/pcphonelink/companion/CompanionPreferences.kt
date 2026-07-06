package com.pcphonelink.companion

import android.content.Context

data class CompanionConfig(
    val controlUrl: String,
    val macAddress: String,
    val broadcastAddress: String,
    val wolPort: Int,
)

class CompanionPreferences(context: Context) {
    private val sharedPreferences = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)

    fun load(): CompanionConfig {
        return CompanionConfig(
            controlUrl = sharedPreferences.getString(KEY_CONTROL_URL, "") ?: "",
            macAddress = sharedPreferences.getString(KEY_MAC_ADDRESS, "") ?: "",
            broadcastAddress = sharedPreferences.getString(KEY_BROADCAST_ADDRESS, DEFAULT_BROADCAST_ADDRESS)
                ?: DEFAULT_BROADCAST_ADDRESS,
            wolPort = sharedPreferences.getInt(KEY_WOL_PORT, DEFAULT_WOL_PORT),
        )
    }

    fun save(config: CompanionConfig) {
        sharedPreferences.edit()
            .putString(KEY_CONTROL_URL, config.controlUrl)
            .putString(KEY_MAC_ADDRESS, config.macAddress)
            .putString(KEY_BROADCAST_ADDRESS, config.broadcastAddress)
            .putInt(KEY_WOL_PORT, config.wolPort)
            .apply()
    }

    companion object {
        private const val PREFERENCES_NAME = "pc_phone_link_companion"
        private const val KEY_CONTROL_URL = "control_url"
        private const val KEY_MAC_ADDRESS = "mac_address"
        private const val KEY_BROADCAST_ADDRESS = "broadcast_address"
        private const val KEY_WOL_PORT = "wol_port"

        const val DEFAULT_BROADCAST_ADDRESS = "255.255.255.255"
        const val DEFAULT_WOL_PORT = 9
    }
}
