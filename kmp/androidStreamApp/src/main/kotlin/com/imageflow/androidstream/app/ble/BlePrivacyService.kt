package com.imageflow.androidstream.app.ble

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import android.util.Log
import com.imageflow.androidstream.app.AppConfig
import com.imageflow.androidstream.app.MainActivity
import com.imageflow.androidstream.app.R
import java.util.concurrent.ConcurrentHashMap

class BlePrivacyService : Service() {
    companion object {
        private const val TAG = "AndroidStreamBle"
        private const val EVAL_INTERVAL_MS = 75L
        private const val ENSURE_INTERVAL_MS = 2000L
        private const val SCAN_ENTRY_TTL_MS = 2500L

        fun start(context: Context) {
            val intent = Intent(context, BlePrivacyService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, BlePrivacyService::class.java))
        }
    }

    private var scanner: android.bluetooth.le.BluetoothLeScanner? = null
    private var callback: ScanCallback? = null
    private var btReceiver: android.content.BroadcastReceiver? = null

    private val controlRssi = ConcurrentHashMap<String, Pair<Int, Long>>()
    private val ambientRssi = ConcurrentHashMap<String, Pair<Int, Long>>()
    private val macToUidKey = ConcurrentHashMap<String, Pair<String, Long>>()

    private var inPrivacy = false
    private var aboveSince = 0L
    private var belowSince = 0L
    private var lastUpdateAt = 0L
    private var lastUpdateRssi: Int? = null
    private var lastUpdateProximity: String? = null
    private var lastControlKey: String? = null
    private var lastControlRssi: Int? = null
    private var lastControlAt: Long = 0L

    private val mainHandler by lazy { android.os.Handler(mainLooper) }

    private val evalRunnable = object : Runnable {
        override fun run() {
            evaluatePrivacyState()
            mainHandler.postDelayed(this, EVAL_INTERVAL_MS)
        }
    }

    private val ensureRunnable = object : Runnable {
        override fun run() {
            tryEnsureScanning()
            mainHandler.postDelayed(this, ENSURE_INTERVAL_MS)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "BLE service created")
        startForegroundWithNotification()
        startBleScanning()
        mainHandler.post(evalRunnable)
        mainHandler.postDelayed(ensureRunnable, ENSURE_INTERVAL_MS)
        btReceiver = object : android.content.BroadcastReceiver() {
            override fun onReceive(context: Context?, intent: Intent?) {
                if (intent?.action == BluetoothAdapter.ACTION_STATE_CHANGED) {
                    when (intent.getIntExtra(BluetoothAdapter.EXTRA_STATE, BluetoothAdapter.ERROR)) {
                        BluetoothAdapter.STATE_ON -> {
                            Log.i(TAG, "Bluetooth enabled; restarting scan")
                            startBleScanning()
                        }
                        BluetoothAdapter.STATE_OFF -> {
                            Log.w(TAG, "Bluetooth disabled; stopping scan")
                            stopBleScanning()
                        }
                    }
                }
            }
        }
        registerReceiver(btReceiver, android.content.IntentFilter(BluetoothAdapter.ACTION_STATE_CHANGED))
    }

    override fun onDestroy() {
        super.onDestroy()
        stopBleScanning()
        mainHandler.removeCallbacksAndMessages(null)
        try { unregisterReceiver(btReceiver) } catch (_: Exception) {}
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    private fun startForegroundWithNotification() {
        val mgr = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channelId = "androidstream_privacy_ble"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(channelId, "Privacy BLE", NotificationManager.IMPORTANCE_MIN)
            ch.setShowBadge(false)
            mgr.createNotificationChannel(ch)
        }
        val pi = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val notification: Notification = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, channelId)
                .setSmallIcon(R.drawable.ic_stat_name)
                .setContentTitle("BLE プライバシー検知")
                .setContentText("ビーコンをスキャンしています")
                .setContentIntent(pi)
                .setOngoing(true)
                .build()
        } else {
            Notification.Builder(this)
                .setSmallIcon(R.drawable.ic_stat_name)
                .setContentTitle("BLE プライバシー検知")
                .setContentText("ビーコンをスキャンしています")
                .setContentIntent(pi)
                .setOngoing(true)
                .build()
        }
        startForeground(1001, notification)
    }

    private fun startBleScanning() {
        val manager = getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        val adapter = manager.adapter ?: return
        if (!adapter.isEnabled) {
            Log.w(TAG, "Bluetooth disabled; cannot scan")
            return
        }
        val scanner = adapter.bluetoothLeScanner ?: return
        this.scanner = scanner

        val beaconType = AppConfig.getBeaconType(this)
        val filters = mutableListOf<ScanFilter>()
        if (beaconType == "eddystone_uid") {
            val svcUuid = android.os.ParcelUuid.fromString("0000feaa-0000-1000-8000-00805f9b34fb")
            filters += ScanFilter.Builder().setServiceUuid(svcUuid).build()
        }
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()
        callback = object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                handleScanResult(result)
            }

            override fun onBatchScanResults(results: MutableList<ScanResult>) {
                results.forEach { handleScanResult(it) }
            }

            override fun onScanFailed(errorCode: Int) {
                Log.w(TAG, "BLE scan failed: $errorCode")
            }
        }
        try {
            if (filters.isEmpty()) {
                scanner.startScan(callback)
            } else {
                scanner.startScan(filters, settings, callback)
            }
            Log.i(TAG, "BLE scanning started (type=${beaconType})")
        } catch (se: SecurityException) {
            Log.w(TAG, "Missing BLE permission: ${se.message}")
        } catch (iae: IllegalArgumentException) {
            Log.w(TAG, "BLE scan start failed: ${iae.message}; retrying fallback")
            try { scanner.startScan(callback); Log.i(TAG, "BLE scan fallback started") } catch (_: Exception) {}
        } catch (e: Exception) {
            Log.w(TAG, "BLE scan error: ${e.message}")
        }
    }

    private fun stopBleScanning() {
        try { scanner?.stopScan(callback) } catch (_: Exception) {}
        scanner = null
        callback = null
    }

    private fun tryEnsureScanning() {
        if (scanner != null) return
        val manager = getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        val adapter = manager.adapter
        if (adapter != null && adapter.isEnabled) {
            Log.i(TAG, "Scanner missing while BT ON; restarting")
            startBleScanning()
        }
    }

    private fun handleScanResult(result: ScanResult) {
        val record = result.scanRecord ?: return
        val now = SystemClock.elapsedRealtime()
        val beaconType = AppConfig.getBeaconType(this)
        val strict = AppConfig.isMatchStrict(this)

        var matchedForControl = false
        var beaconId: String? = null
        val mac = try { result.device?.address ?: "" } catch (_: Exception) { "" }

        if (beaconType == "eddystone_uid" || beaconType == "any") {
            val ed = BeaconParsers.parseEddystoneUid(record)
            if (ed != null) {
                val nsCfg = AppConfig.getEddystoneNamespace(this)?.lowercase()
                val instCfg = AppConfig.getEddystoneInstance(this)?.lowercase()
                val nsHex = ed.nsHex()
                val instHex = ed.instHex()
                val nsOk = nsCfg.isNullOrBlank() || nsHex == nsCfg
                val instOk = instCfg.isNullOrBlank() || instHex == instCfg
                if (!nsCfg.isNullOrBlank() || !instCfg.isNullOrBlank()) {
                    if (nsOk && instOk) {
                        matchedForControl = true
                        beaconId = "eddystone:${nsHex}:${instHex}"
                        if (mac.isNotEmpty()) macToUidKey[mac] = beaconId!! to now
                    }
                }
            }
        }
        if (!matchedForControl && beaconType == "any") {
            val frameType = BeaconParsers.getEddystoneFrameType(record)
            if (frameType != null) {
                beaconId = String.format("eddystone:ft=0x%02x", frameType)
            }
        }
        if (!matchedForControl && beaconType == "eddystone_uid") {
            val extend = AppConfig.getHoldExtendNonUid(this)
            if (extend && mac.isNotEmpty()) {
                val pair = macToUidKey[mac]
                if (pair != null) {
                    lastControlKey = pair.first
                    lastControlRssi = result.rssi
                    lastControlAt = now
                }
            }
        }
        if (!matchedForControl && (beaconType == "ibeacon" || beaconType == "any")) {
            val ib = BeaconParsers.parseIBeacon(record)
            if (ib != null) {
                val uuidCfg = AppConfig.getIBeaconUuid(this)?.lowercase()
                val majorCfg = AppConfig.getIBeaconMajor(this)
                val minorCfg = AppConfig.getIBeaconMinor(this)
                val uuidHex = ib.uuid.toString().lowercase()
                val uuidOk = uuidCfg.isNullOrBlank() || uuidHex == uuidCfg
                val majorOk = majorCfg == null || ib.major == majorCfg
                val minorOk = minorCfg == null || ib.minor == minorCfg
                if (!uuidCfg.isNullOrBlank() || majorCfg != null || minorCfg != null) {
                    if (uuidOk && majorOk && minorOk) {
                        matchedForControl = true
                        beaconId = "ibeacon:${uuidHex}:${ib.major}:${ib.minor}"
                    }
                }
            }
        }

        val key = beaconId ?: "unknown"
        if (matchedForControl) {
            controlRssi[key] = result.rssi to now
            lastControlKey = key
            lastControlRssi = result.rssi
            lastControlAt = now
        } else {
            ambientRssi[key] = result.rssi to now
        }
    }

    private fun evaluatePrivacyState() {
        val now = SystemClock.elapsedRealtime()
        val expireBefore = now - SCAN_ENTRY_TTL_MS
        controlRssi.entries.removeIf { it.value.second < expireBefore }
        ambientRssi.entries.removeIf { it.value.second < expireBefore }

        val strict = AppConfig.isMatchStrict(this)
        val source = if (strict) controlRssi else if (controlRssi.isNotEmpty()) controlRssi else ambientRssi
        var strongest: Int? = null
        var strongestKey: String? = null
        source.forEach { (key, value) ->
            if (strongest == null || value.first > strongest!!) {
                strongest = value.first
                strongestKey = key
            }
        }

        val enterRssi = AppConfig.getEnterRssi(this)
        val exitRssi = AppConfig.getExitRssi(this)
        val enterSec = AppConfig.getEnterSeconds(this)
        val exitSec = AppConfig.getExitSeconds(this)
        val holdSec = AppConfig.getPresenceHoldSeconds(this)

        if (strict && strongest == null && lastControlAt > 0 && (now - lastControlAt) <= holdSec * 1000L) {
            strongest = lastControlRssi
            strongestKey = lastControlKey
        }

        if (strongest != null) {
            if (strongest!! >= enterRssi) {
                if (aboveSince == 0L) aboveSince = now
                belowSince = 0L
            } else if (strongest!! <= exitRssi) {
                if (belowSince == 0L) belowSince = now
                aboveSince = 0L
            }
        } else {
            if (belowSince == 0L) belowSince = now
            aboveSince = 0L
        }

        if (!inPrivacy && aboveSince > 0 && now - aboveSince >= enterSec * 1000L) {
            inPrivacy = true
            aboveSince = 0L
            broadcastEnter(strongestKey ?: "unknown", strongest ?: -127)
        } else if (inPrivacy && belowSince > 0 && now - belowSince >= exitSec * 1000L) {
            inPrivacy = false
            belowSince = 0L
            broadcastExit(strongestKey ?: "unknown", strongest ?: -127)
        }

        val nowProximity = when {
            strongest == null -> "far"
            strongest!! >= enterRssi -> "near"
            strongest!! <= exitRssi -> "far"
            else -> "mid"
        }
        val shouldSend = (now - lastUpdateAt >= 1000L) ||
            (lastUpdateRssi == null && strongest != null) ||
            (lastUpdateRssi != null && strongest == null) ||
            (strongest != null && lastUpdateRssi != null && kotlin.math.abs(strongest!! - lastUpdateRssi!!) >= 3) ||
            (nowProximity != lastUpdateProximity)
        if (shouldSend) {
            lastUpdateAt = now
            lastUpdateRssi = strongest
            lastUpdateProximity = nowProximity
            broadcastUpdate(strongestKey ?: "unknown", strongest, nowProximity)
        }
    }

    private fun broadcastEnter(beaconId: String, rssi: Int) {
        Log.i(TAG, "PRIVACY ENTER by $beaconId rssi=$rssi")
        val intent = Intent(PrivacyEvents.ACTION_PRIVACY_ENTER).apply {
            putExtra(PrivacyEvents.EXTRA_BEACON_ID, beaconId)
            putExtra(PrivacyEvents.EXTRA_RSSI, rssi)
        }
        sendBroadcast(intent)
    }

    private fun broadcastExit(beaconId: String, rssi: Int) {
        Log.i(TAG, "PRIVACY EXIT by $beaconId rssi=$rssi")
        val intent = Intent(PrivacyEvents.ACTION_PRIVACY_EXIT).apply {
            putExtra(PrivacyEvents.EXTRA_BEACON_ID, beaconId)
            putExtra(PrivacyEvents.EXTRA_RSSI, rssi)
        }
        sendBroadcast(intent)
    }

    private fun broadcastUpdate(beaconId: String, rssi: Int?, proximity: String) {
        val intent = Intent(PrivacyEvents.ACTION_PRIVACY_UPDATE).apply {
            putExtra(PrivacyEvents.EXTRA_BEACON_ID, beaconId)
            if (rssi != null) putExtra(PrivacyEvents.EXTRA_RSSI, rssi)
            putExtra(PrivacyEvents.EXTRA_PROXIMITY, proximity)
            putExtra(PrivacyEvents.EXTRA_IN_PRIVACY, inPrivacy)
        }
        sendBroadcast(intent)
    }
}
