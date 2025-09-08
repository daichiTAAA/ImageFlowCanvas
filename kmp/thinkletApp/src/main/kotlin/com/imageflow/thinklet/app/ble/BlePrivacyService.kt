package com.imageflow.thinklet.app.ble

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.bluetooth.le.*
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import android.util.Log
import com.imageflow.thinklet.app.AppConfig
import com.imageflow.thinklet.app.MainActivity
import com.imageflow.thinklet.app.R
import java.util.concurrent.ConcurrentHashMap
import kotlin.math.max

class BlePrivacyService : Service() {
    private var scanner: BluetoothLeScanner? = null
    private var cb: ScanCallback? = null
    private var btReceiver: android.content.BroadcastReceiver? = null

    // rssi state
    private val lastRssi = ConcurrentHashMap<String, Pair<Int, Long>>() // beaconId -> (rssi, tsMs)
    private var inPrivacy = false
    private var aboveSince = 0L
    private var belowSince = 0L
    private var lastUpdateAt = 0L
    private var lastUpdateRssi: Int? = null
    private var lastUpdateProximity: String? = null

    private val evalRunnable = object : Runnable {
        override fun run() {
            evalState()
            // schedule next
            mainHandler.postDelayed(this, 500)
        }
    }

    private val mainHandler by lazy { android.os.Handler(mainLooper) }
    private val ensureRunnable = object : Runnable {
        override fun run() {
            tryEnsureScanning()
            mainHandler.postDelayed(this, 3000)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "BLE service created")
        startForegroundWithNotification()
        startBle()
        mainHandler.post(evalRunnable)
        mainHandler.postDelayed(ensureRunnable, 3000)
        // Listen Bluetooth state changes to start/stop scanning dynamically
        btReceiver = object : android.content.BroadcastReceiver() {
            override fun onReceive(context: Context?, intent: Intent?) {
                if (intent?.action == BluetoothAdapter.ACTION_STATE_CHANGED) {
                    when (intent.getIntExtra(BluetoothAdapter.EXTRA_STATE, BluetoothAdapter.ERROR)) {
                        BluetoothAdapter.STATE_ON -> {
                            Log.i(TAG, "Bluetooth turned ON; (re)starting scan")
                            startBle()
                        }
                        BluetoothAdapter.STATE_OFF -> {
                            Log.w(TAG, "Bluetooth turned OFF; stopping scan")
                            stopBle()
                        }
                    }
                }
            }
        }
        registerReceiver(btReceiver, android.content.IntentFilter(BluetoothAdapter.ACTION_STATE_CHANGED))
    }

    override fun onDestroy() {
        super.onDestroy()
        stopBle()
        mainHandler.removeCallbacksAndMessages(null)
        try { unregisterReceiver(btReceiver) } catch (_: Exception) {}
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    private fun startForegroundWithNotification() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val chId = "privacy_ble"
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val ch = NotificationChannel(chId, "Privacy BLE", NotificationManager.IMPORTANCE_MIN)
            ch.setShowBadge(false)
            nm.createNotificationChannel(ch)
        }
        val pi = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        val n: Notification = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, chId)
                .setSmallIcon(R.drawable.ic_stat_name)
                .setContentTitle("Privacy BLE scanning")
                .setContentText("Detecting privacy beacons…")
                .setContentIntent(pi)
                .setOngoing(true)
                .build()
        } else {
            Notification.Builder(this)
                .setSmallIcon(R.drawable.ic_stat_name)
                .setContentTitle("Privacy BLE scanning")
                .setContentText("Detecting privacy beacons…")
                .setContentIntent(pi)
                .setOngoing(true)
                .build()
        }
        startForeground(1001, n)
    }

    private fun startBle() {
        val mgr = getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        val adapter: BluetoothAdapter = mgr.adapter ?: return
        if (!adapter.isEnabled) {
            Log.w(TAG, "Bluetooth disabled; cannot scan")
            return
        }
        scanner = adapter.bluetoothLeScanner ?: return

        val type = AppConfig.getBeaconType(this)
        val filters = mutableListOf<ScanFilter>()
        // Important: when type is "any", don't add service filters, otherwise iBeacon frames are filtered out
        if (type == "eddystone_uid") {
            val svcUuid = android.os.ParcelUuid.fromString("0000feaa-0000-1000-8000-00805f9b34fb")
            filters += ScanFilter.Builder().setServiceUuid(svcUuid).build()
        }
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()
        cb = object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                handleResult(result)
            }

            override fun onBatchScanResults(results: MutableList<ScanResult>) {
                results.forEach { handleResult(it) }
            }

            override fun onScanFailed(errorCode: Int) {
                Log.w(TAG, "BLE scan failed: $errorCode")
            }
        }
        try {
            if (filters.isEmpty()) {
                // Use simplest overload to avoid NPE on some Android 8.x stacks
                scanner?.startScan(cb)
            } else {
                scanner?.startScan(filters, settings, cb)
            }
            Log.i(TAG, "BLE scanning started (type=${type})")
        } catch (e: SecurityException) {
            Log.w(TAG, "BLE permission missing: ${e.message}")
        } catch (e: IllegalArgumentException) {
            // Defensive: some devices throw when settings/filters are not supported
            Log.w(TAG, "BLE scan start failed (args): ${e.message}; retrying with default settings")
            try { scanner?.startScan(cb); Log.i(TAG, "BLE scanning started (fallback)") } catch (_: Exception) {}
        } catch (e: Exception) {
            Log.w(TAG, "BLE scan error: ${e.message}")
        }
    }

    private fun stopBle() {
        try { scanner?.stopScan(cb) } catch (_: Exception) {}
        cb = null
        scanner = null
    }

    private fun tryEnsureScanning() {
        if (scanner != null) return
        val mgr = getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
        val adapter = mgr.adapter
        if (adapter != null && adapter.isEnabled) {
            Log.i(TAG, "ensure: scanner is null but BT ON; starting scan")
            startBle()
        }
    }

    private fun handleResult(r: ScanResult) {
        val rec = r.scanRecord ?: return
        val now = SystemClock.elapsedRealtime()
        val type = AppConfig.getBeaconType(this)

        var matched = false
        var beaconId: String? = null
        // Eddystone UID (strict)
        if (type == "eddystone_uid" || type == "any") {
            val ed = BeaconParsers.parseEddystoneUid(rec)
            if (ed != null) {
                val nsCfg = AppConfig.getEddystoneNamespace(this)?.lowercase()
                val instCfg = AppConfig.getEddystoneInstance(this)?.lowercase()
                val nsHex = ed.nsHex()
                val instHex = ed.instHex()
                val nsOk = nsCfg.isNullOrBlank() || nsHex == nsCfg
                val instOk = instCfg.isNullOrBlank() || instHex == instCfg
                if (nsOk && instOk) {
                    matched = true
                    beaconId = "eddystone:${nsHex}:${instHex}"
                }
            }
        }
        // Any Eddystone frame (URL/TLM/EID) for visibility when beacon.type=any
        if (!matched && type == "any") {
            val ft = BeaconParsers.getEddystoneFrameType(rec)
            if (ft != null) {
                matched = true
                beaconId = String.format("eddystone:ft=0x%02x", ft)
            }
        }
        // iBeacon
        if (!matched && (type == "ibeacon" || type == "any")) {
            val ib = BeaconParsers.parseIBeacon(rec)
            if (ib != null) {
                val uuidCfg = AppConfig.getIBeaconUuid(this)?.lowercase()
                val majorCfg = AppConfig.getIBeaconMajor(this)
                val minorCfg = AppConfig.getIBeaconMinor(this)
                val uuidHex = ib.uuid.toString().lowercase()
                val uuidOk = uuidCfg.isNullOrBlank() || uuidHex == uuidCfg
                val majorOk = majorCfg == null || ib.major == majorCfg
                val minorOk = minorCfg == null || ib.minor == minorCfg
                if (uuidOk && majorOk && minorOk) {
                    matched = true
                    beaconId = "ibeacon:${uuidHex}:${ib.major}:${ib.minor}"
                }
            }
        }

        if (matched) {
            val key = beaconId ?: "unknown"
            lastRssi[key] = r.rssi to now
        }
    }

    private fun evalState() {
        val now = SystemClock.elapsedRealtime()
        // expire old entries > 3s
        val expireBefore = now - 3000
        lastRssi.entries.removeIf { it.value.second < expireBefore }

        // pick strongest current RSSI
        var strongest: Int? = null
        var strongestKey: String? = null
        lastRssi.forEach { (k, v) ->
            if (strongest == null || v.first > strongest!!) {
                strongest = v.first
                strongestKey = k
            }
        }

        val enterRssi = AppConfig.getEnterRssi(this)
        val exitRssi = AppConfig.getExitRssi(this)
        val enterSec = AppConfig.getEnterSeconds(this)
        val exitSec = AppConfig.getExitSeconds(this)

        if (strongest != null) {
            if (strongest!! >= enterRssi) {
                // above threshold
                if (aboveSince == 0L) aboveSince = now
                belowSince = 0L
            } else if (strongest!! <= exitRssi) {
                // below threshold
                if (belowSince == 0L) belowSince = now
                aboveSince = 0L
            } else {
                // between thresholds → do not change timers to keep hysteresis
            }
        } else {
            // no beacon → treat as far
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

        // Send periodic RSSI/proximity update (throttled)
        val nowProx = when {
            strongest == null -> "far"
            strongest!! >= enterRssi -> "near"
            strongest!! <= exitRssi -> "far"
            else -> "mid"
        }
        val shouldSend = (now - lastUpdateAt >= 1000L) ||
                (lastUpdateRssi == null && strongest != null) ||
                (lastUpdateRssi != null && strongest == null) ||
                (strongest != null && lastUpdateRssi != null && kotlin.math.abs(strongest!! - lastUpdateRssi!!) >= 3) ||
                (nowProx != lastUpdateProximity)
        if (shouldSend) {
            lastUpdateAt = now
            lastUpdateRssi = strongest
            lastUpdateProximity = nowProx
            broadcastUpdate(strongestKey ?: "unknown", strongest, nowProx)
        }
    }

    private fun broadcastEnter(beaconId: String, rssi: Int) {
        Log.i(TAG, "PRIVACY ENTER due to $beaconId rssi=$rssi")
        val i = Intent(PrivacyEvents.ACTION_PRIVACY_ENTER)
        i.putExtra(PrivacyEvents.EXTRA_BEACON_ID, beaconId)
        i.putExtra(PrivacyEvents.EXTRA_RSSI, rssi)
        sendBroadcast(i)
    }

    private fun broadcastExit(beaconId: String, rssi: Int) {
        Log.i(TAG, "PRIVACY EXIT due to $beaconId rssi=$rssi")
        val i = Intent(PrivacyEvents.ACTION_PRIVACY_EXIT)
        i.putExtra(PrivacyEvents.EXTRA_BEACON_ID, beaconId)
        i.putExtra(PrivacyEvents.EXTRA_RSSI, rssi)
        sendBroadcast(i)
    }

    private fun broadcastUpdate(beaconId: String, rssiNullable: Int?, proximity: String) {
        val i = Intent(PrivacyEvents.ACTION_PRIVACY_UPDATE)
        i.putExtra(PrivacyEvents.EXTRA_BEACON_ID, beaconId)
        if (rssiNullable != null) i.putExtra(PrivacyEvents.EXTRA_RSSI, rssiNullable)
        i.putExtra(PrivacyEvents.EXTRA_PROXIMITY, proximity)
        i.putExtra(PrivacyEvents.EXTRA_IN_PRIVACY, inPrivacy)
        sendBroadcast(i)
    }

    companion object {
        private const val TAG = "BlePrivacy"

        fun start(context: Context) {
            val i = Intent(context, BlePrivacyService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(i)
            } else {
                context.startService(i)
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, BlePrivacyService::class.java))
        }
    }
}
