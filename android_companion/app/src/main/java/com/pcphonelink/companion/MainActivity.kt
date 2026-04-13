package com.pcphonelink.companion

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.pcphonelink.companion.databinding.ActivityMainBinding
import java.io.IOException
import java.util.Locale
import kotlinx.coroutines.launch

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var preferences: CompanionPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        preferences = CompanionPreferences(this)
        populateFields(preferences.load())

        binding.saveSettingsButton.setOnClickListener { saveSettings() }
        binding.wakePcButton.setOnClickListener { wakePcOnly() }
        binding.wakeAndOpenButton.setOnClickListener { wakeAndOpenControls() }
        binding.openControlsButton.setOnClickListener { openControlsNow() }
    }

    private fun populateFields(config: CompanionConfig) {
        binding.controlUrlInput.setText(config.controlUrl)
        binding.launcherStartUrlInput.setText(config.launcherStartUrl.orEmpty())
        binding.macAddressInput.setText(config.macAddress)
        binding.broadcastAddressInput.setText(config.broadcastAddress)
        binding.wolPortInput.setText(config.wolPort.toString())
    }

    private fun saveSettings() {
        val config = readWakeConfigFromUi() ?: return
        preferences.save(config)
        setStatus(getString(R.string.status_settings_saved))
        toast(R.string.toast_settings_saved)
    }

    private fun wakePcOnly() {
        val config = readWakeConfigFromUi() ?: return
        preferences.save(config)
        lifecycleScope.launch {
            runBusyAction(
                startStatus = getString(R.string.status_sending_wake),
                successStatus = getString(R.string.status_wake_sent),
            ) {
                WakeOnLanSender.send(config)
                toast(R.string.toast_wake_sent)
            }
        }
    }

    private fun wakeAndOpenControls() {
        val config = readWakeConfigFromUi() ?: return
        preferences.save(config)
        lifecycleScope.launch {
            runBusyAction(
                startStatus = getString(R.string.status_sending_wake),
                successStatus = getString(R.string.status_opening_controls),
            ) {
                WakeOnLanSender.send(config)
                setStatus(getString(R.string.status_waiting_for_pc))
                var controlsReady = ControlLauncher.waitForReachable(
                    controlUrl = config.controlUrl,
                    timeoutMs = 15_000,
                    initialDelayMs = 4_000,
                )
                if (!controlsReady && !config.launcherStartUrl.isNullOrBlank()) {
                    setStatus(getString(R.string.status_starting_controls))
                    ControlLauncher.startControls(config.launcherStartUrl)
                    controlsReady = ControlLauncher.waitForReachable(
                        controlUrl = config.controlUrl,
                        timeoutMs = 90_000,
                        initialDelayMs = 4_000,
                    )
                } else if (!controlsReady) {
                    controlsReady = ControlLauncher.waitForReachable(
                        controlUrl = config.controlUrl,
                        timeoutMs = 90_000,
                    )
                }

                if (!controlsReady) {
                    throw IOException(getString(R.string.error_controls_timeout))
                }

                openControls(config.controlUrl)
                toast(R.string.toast_controls_opened)
            }
        }
    }

    private fun openControlsNow() {
        clearFieldErrors()
        val controlUrl = binding.controlUrlInput.text.toString().trim()
        if (!isValidHttpUrl(controlUrl)) {
            binding.controlUrlInput.error = getString(R.string.error_control_url)
            return
        }
        try {
            openControls(controlUrl)
        } catch (error: IOException) {
            toast(error.message ?: getString(R.string.error_no_browser))
        }
    }

    private suspend fun runBusyAction(
        startStatus: String,
        successStatus: String,
        block: suspend () -> Unit,
    ) {
        setBusy(true)
        setStatus(startStatus)
        try {
            block()
            setStatus(successStatus)
        } catch (error: Exception) {
            setStatus(getString(R.string.status_action_failed))
            toast(error.message ?: getString(R.string.error_generic))
        } finally {
            setBusy(false)
        }
    }

    private fun openControls(controlUrl: String) {
        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(controlUrl))
        try {
            startActivity(intent)
        } catch (_: ActivityNotFoundException) {
            throw IOException(getString(R.string.error_no_browser))
        }
    }

    private fun readWakeConfigFromUi(): CompanionConfig? {
        clearFieldErrors()

        val controlUrl = binding.controlUrlInput.text.toString().trim()
        if (!isValidHttpUrl(controlUrl)) {
            binding.controlUrlInput.error = getString(R.string.error_control_url)
            return null
        }

        val launcherStartUrl = binding.launcherStartUrlInput.text.toString().trim().ifBlank { null }
        if (launcherStartUrl != null && !isValidHttpUrl(launcherStartUrl)) {
            binding.launcherStartUrlInput.error = getString(R.string.error_launcher_url)
            return null
        }

        val macAddress = binding.macAddressInput.text.toString().trim()
        if (!isValidMacAddress(macAddress)) {
            binding.macAddressInput.error = getString(R.string.error_mac_address)
            return null
        }

        val broadcastAddress = binding.broadcastAddressInput.text.toString().trim()
            .ifBlank { CompanionPreferences.DEFAULT_BROADCAST_ADDRESS }
        val wolPort = binding.wolPortInput.text.toString().trim()
            .ifBlank { CompanionPreferences.DEFAULT_WOL_PORT.toString() }
            .toIntOrNull()
        if (wolPort == null || wolPort !in 1..65535) {
            binding.wolPortInput.error = getString(R.string.error_wol_port)
            return null
        }

        return CompanionConfig(
            controlUrl = controlUrl,
            launcherStartUrl = launcherStartUrl,
            macAddress = macAddress,
            broadcastAddress = broadcastAddress,
            wolPort = wolPort,
        )
    }

    private fun clearFieldErrors() {
        binding.controlUrlInput.error = null
        binding.launcherStartUrlInput.error = null
        binding.macAddressInput.error = null
        binding.wolPortInput.error = null
    }

    private fun setBusy(isBusy: Boolean) {
        binding.saveSettingsButton.isEnabled = !isBusy
        binding.wakePcButton.isEnabled = !isBusy
        binding.wakeAndOpenButton.isEnabled = !isBusy
        binding.openControlsButton.isEnabled = !isBusy
    }

    private fun setStatus(message: String) {
        binding.statusText.text = message
    }

    private fun toast(messageResId: Int) {
        Toast.makeText(this, messageResId, Toast.LENGTH_SHORT).show()
    }

    private fun toast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }

    private fun isValidHttpUrl(value: String): Boolean {
        return value.startsWith("http://") || value.startsWith("https://")
    }

    private fun isValidMacAddress(value: String): Boolean {
        val cleaned = value.filter { it.isLetterOrDigit() }.uppercase(Locale.US)
        return cleaned.length == 12 && cleaned.all { it in "0123456789ABCDEF" }
    }
}
