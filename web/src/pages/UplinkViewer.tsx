import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Hls from "hls.js";
import {
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Slider,
  TextField,
  Typography,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import StopIcon from "@mui/icons-material/Stop";
import axios from "axios";

type StreamItem = {
  path: string;
  device_id: string;
  hls_url: string;
  state: string;
  readers: number;
  publishers: number;
};

type RecordingIndexSegment = {
  start: string;
};

type RecordingIndexItem = {
  path: string;
  device_id: string;
  segment_count: number;
  latest_start?: string | null;
  earliest_start?: string | null;
  segments: RecordingIndexSegment[];
};

const API_PREFIX = "/api/uplink";

export default function UplinkViewer() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const whepResourceRef = useRef<string | null>(null);
  const loadRequestIdRef = useRef(0);
  const lastLoadedPathRef = useRef<string | null>(null);

  const [deviceId, setDeviceId] = useState("");
  const [streams, setStreams] = useState<StreamItem[]>([]);
  const [manualUrl, setManualUrl] = useState("");
  const [hlsError, setHlsError] = useState("");
  const [mode, setMode] = useState<"hls" | "whep">("whep");
  const [whepStatus, setWhepStatus] = useState("");
  const [whepError, setWhepError] = useState("");

  const [recordingIndex, setRecordingIndex] = useState<RecordingIndexItem[]>([]);
  const [recordingIndexLoading, setRecordingIndexLoading] = useState(false);
  const [recordingIndexError, setRecordingIndexError] = useState("");
  const [recordingFilter, setRecordingFilter] = useState("");
  const [selectedRecordingPath, setSelectedRecordingPath] = useState("");
  const [recordingSelectionMode, setRecordingSelectionMode] =
    useState<"auto" | "manual">("auto");
  const selectedRecordingPathRef = useRef<string>("");

  const [isLivePlaying, setIsLivePlaying] = useState(false);

  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState("");
  const [recPath, setRecPath] = useState("");
  const [recSegments, setRecSegments] = useState<any[]>([]);
  const [recPlayback, setRecPlayback] = useState<any[]>([]);
  const [recFormatMp4, setRecFormatMp4] = useState(true);
  const [rangeStart, setRangeStart] = useState("");
  const [rangeEnd, setRangeEnd] = useState("");
  const [segmentQuery, setSegmentQuery] = useState("");
  // 録画シーク用の絶対オフセット方式
  const [recClipStartIso, setRecClipStartIso] = useState<string | null>(null); // クリップ全体の開始ISO
  const [recClipDuration, setRecClipDuration] = useState<number | null>(null); // クリップ総尺（秒）
  const [recBaseOffsetSec, setRecBaseOffsetSec] = useState<number>(0); // 現ストリームの先頭がクリップ先頭から何秒か
  const [recSeekPos, setRecSeekPos] = useState<number>(0); // 表示用の絶対位置（秒）

  const deriveDeviceId = useCallback((path: string) => {
    if (!path) return path;
    if (path.includes("/")) return path.split("/", 1)[1];
    if (path.startsWith("uplink-")) return path.split("uplink-", 1)[1];
    return path;
  }, []);

  useEffect(() => {
    selectedRecordingPathRef.current = selectedRecordingPath;
  }, [selectedRecordingPath]);

  const formatTimestamp = useCallback((iso?: string | null) => {
    if (!iso) return "-";
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString();
  }, []);

  const loadRecordingPath = useCallback(
    async (
      path: string,
      { resetSeek = true, force = false }: { resetSeek?: boolean; force?: boolean } = {}
    ) => {
      const safePath = path?.trim();
      if (!safePath) {
        setRecError("録画パスが空です");
        return;
      }
      if (!force && lastLoadedPathRef.current === safePath) {
        return;
      }
      const requestId = ++loadRequestIdRef.current;
      setRecError("");
      setRecLoading(true);
      setRecPath(safePath);
      try {
        const resp = await axios.get(
          `${API_PREFIX}/recordings/${encodeURIComponent(safePath)}`
        );
        if (loadRequestIdRef.current !== requestId) return;
        const data = resp.data || {};
        if (resetSeek) {
          setRecClipStartIso(null);
          setRecClipDuration(null);
          setRecBaseOffsetSec(0);
          setRecSeekPos(0);
        }
        setRecSegments(data.segments || []);
        setRecPlayback(data.playback || []);
        lastLoadedPathRef.current = safePath;
      } catch (e: any) {
        if (loadRequestIdRef.current === requestId) {
          setRecError(String(e?.message || e));
        }
      } finally {
        if (loadRequestIdRef.current === requestId) {
          setRecLoading(false);
        }
      }
    },
    []
  );

  const fetchStreams = useCallback(async () => {
    try {
      const resp = await axios.get(`${API_PREFIX}/streams`);
      const items: StreamItem[] = resp.data.items || [];
      setStreams(items);
      if (!deviceId && items.length > 0) {
        setDeviceId(items[0].device_id);
      }
    } catch (e) {
      console.error("Failed to fetch streams", e);
    }
  }, [deviceId]);

  const fetchRecordingIndex = useCallback(async () => {
    setRecordingIndexError("");
    setRecordingIndexLoading(true);
    try {
      const resp = await axios.get(`${API_PREFIX}/recordings`);
      const data = resp.data || {};
      const items = (data.items || []) as any[];
      const mapped: RecordingIndexItem[] = items
        .map((it) => {
          const path = it.path as string;
          const segmentsRaw = (it.segments || []) as any[];
          const segments: RecordingIndexSegment[] = segmentsRaw
            .map((seg) => {
              const start = seg?.start;
              if (!start) return null;
              return { start: typeof start === "string" ? start : String(start) };
            })
            .filter(Boolean) as RecordingIndexSegment[];
          segments.sort((a, b) => b.start.localeCompare(a.start));
          return {
            path,
            device_id: it.device_id || deriveDeviceId(path),
            segment_count:
              typeof it.segment_count === "number" ? it.segment_count : segments.length,
            latest_start: it.latest_start || segments[0]?.start || null,
            earliest_start: it.earliest_start || segments[segments.length - 1]?.start || null,
            segments,
          } as RecordingIndexItem;
        })
        .filter((item) => item.segment_count > 0 && item.path);

      mapped.sort((a, b) => {
        if (a.latest_start && b.latest_start) {
          const cmp = b.latest_start.localeCompare(a.latest_start);
          if (cmp !== 0) return cmp;
        } else if (a.latest_start) {
          return -1;
        } else if (b.latest_start) {
          return 1;
        }
        return a.device_id.localeCompare(b.device_id);
      });

      setRecordingIndex(mapped);

      const currentSelected = selectedRecordingPathRef.current;

      if (mapped.length === 0) {
        setRecSegments([]);
        setRecPlayback([]);
        setRecClipStartIso(null);
        setRecClipDuration(null);
        setRecBaseOffsetSec(0);
        setRecSeekPos(0);
        lastLoadedPathRef.current = null;
        return;
      }

      const hasSelected =
        currentSelected && mapped.some((item) => item.path === currentSelected);

      if (!hasSelected) {
        const initialPath = mapped[0].path;
        setRecordingSelectionMode("auto");
        setSelectedRecordingPath(initialPath);
        setRecPath(initialPath);
        setSegmentQuery("");
        await loadRecordingPath(initialPath, { force: true });
      } else if (currentSelected) {
        setRecPath(currentSelected);
        await loadRecordingPath(currentSelected, { resetSeek: false, force: true });
      }
    } catch (e: any) {
      setRecordingIndexError(String(e?.message || e));
    } finally {
      setRecordingIndexLoading(false);
    }
  }, [deriveDeviceId, loadRecordingPath]);

  useEffect(() => {
    fetchStreams();
    const t = setInterval(fetchStreams, 5000);
    return () => clearInterval(t);
  }, [fetchStreams]);

  useEffect(() => {
    fetchRecordingIndex();
    const t = setInterval(fetchRecordingIndex, 60000);
    return () => clearInterval(t);
  }, [fetchRecordingIndex]);

  useEffect(() => {
    if (recordingSelectionMode === "manual") return;
    if (!deviceId) return;
    const s = streams.find((x) => x.device_id === deviceId);
    const path = s ? s.path : `uplink/${deviceId}`;
    if (!path) return;
    if (selectedRecordingPath === path) return;
    setRecordingSelectionMode("auto");
    setSelectedRecordingPath(path);
    setRecPath(path);
    setSegmentQuery("");
    void loadRecordingPath(path, { resetSeek: false });
  }, [deviceId, streams, loadRecordingPath, recordingSelectionMode, selectedRecordingPath]);

  const filteredRecordingIndex = useMemo(() => {
    const q = recordingFilter.trim().toLowerCase();
    if (!q) return recordingIndex;
    return recordingIndex.filter((item) => {
      const did = item.device_id?.toLowerCase?.() || "";
      const path = item.path?.toLowerCase?.() || "";
      return did.includes(q) || path.includes(q);
    });
  }, [recordingIndex, recordingFilter]);

  const activeRecordingMeta = useMemo(
    () => recordingIndex.find((item) => item.path === selectedRecordingPath),
    [recordingIndex, selectedRecordingPath]
  );

  const filteredSegments = useMemo(() => {
    const source = (recPlayback.length > 0 ? recPlayback : recSegments) as any[];
    const q = segmentQuery.trim().toLowerCase();
    if (!q) return source;
    return source.filter((seg) =>
      String(seg?.start || "").toLowerCase().includes(q)
    );
  }, [recPlayback, recSegments, segmentQuery]);

  const play = (hlsUrl: string) => {
    setHlsError("");
    const video = videoRef.current;
    if (!video) {
      setIsLivePlaying(false);
      return;
    }
    // fully reset any previous file playback to avoid contention
    try {
      video.pause();
    } catch {}
    try {
      (video as any).srcObject = null;
    } catch {}
    try {
      video.removeAttribute("src");
      video.load();
    } catch {}
    if (Hls.isSupported()) {
      // clean up previous instance
      if (hlsRef.current) {
        try {
          hlsRef.current.destroy();
        } catch {}
        hlsRef.current = null;
      }
      const hls = new Hls({
        lowLatencyMode: true,
        enableWorker: true,
        startPosition: -1,
        // keep history minimal but allow full 2s+ segments to buffer
        backBufferLength: 0,
        maxBufferLength: 6,
        maxBufferHole: 0.5,
        // chase live edge aggressively while leaving small headroom
        liveSyncDurationCount: 2,
        liveMaxLatencyDurationCount: 4,
        maxLiveSyncPlaybackRate: 1.5,
      });
      hlsRef.current = hls;
      setIsLivePlaying(true);
      hls.loadSource(hlsUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {
          setIsLivePlaying(false);
        });
      });
      hls.on(Hls.Events.LEVEL_LOADED, () => {
        // try to stick to live edge during live playback
        try {
          (hls as any).seekToLivePosition?.();
        } catch {}
      });
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.details === "fragGap") {
          const v = videoRef.current;
          if (v && v.seekable && v.seekable.length > 0) {
            const end = v.seekable.end(v.seekable.length - 1);
            v.currentTime = Math.max(0, end - 0.5);
          }
          try {
            hls.startLoad();
          } catch {}
          return;
        }
        const msg = `${data.type}: ${data.details}`;
        setHlsError(msg);
        if (data.fatal) {
          if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
            hls.startLoad();
          } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
            hls.recoverMediaError();
          } else {
            try {
              hls.destroy();
            } catch {}
            hlsRef.current = null;
            // try quick reload at same URL
            setTimeout(() => play(hlsUrl), 500);
          }
        } else if (data.details === "bufferSeekOverHole") {
          const v = videoRef.current;
          if (v && v.seekable && v.seekable.length > 0) {
            const end = v.seekable.end(v.seekable.length - 1);
            v.currentTime = Math.max(0, end - 0.5);
          } else {
            try {
              (hls as any).seekToLivePosition?.();
            } catch {}
          }
        }
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = hlsUrl;
      setIsLivePlaying(true);
      video.play().catch((e) => {
        setHlsError(String(e));
        setIsLivePlaying(false);
      });
    } else {
      alert("HLS is not supported in this browser");
      setIsLivePlaying(false);
    }
  };

  const buildUrlFromDevice = () => {
    const s = streams.find((x) => x.device_id === deviceId);
    if (s && s.hls_url) return s.hls_url;
    const host = window.location.hostname;
    const port = 8888; // fallback
    return `http://${host}:${port}/${deviceId ? `uplink/${deviceId}` : "uplink"}/index.m3u8`;
  };

  const buildWhepUrlFromDevice = () => {
    const s = streams.find((x) => x.device_id === deviceId);
    const path = s ? s.path : deviceId ? `uplink/${deviceId}` : "";
    if (!path) return "";
    const host = window.location.hostname;
    const port = 8889; // MediaMTX WebRTC HTTP port
    return `http://${host}:${port}/${path}/whep`;
  };

  const waitIceComplete = (pc: RTCPeerConnection, timeoutMs = 1200) =>
    new Promise<void>((resolve) => {
      if (pc.iceGatheringState === "complete") return resolve();
      const check = () => {
        if (pc.iceGatheringState === "complete") {
          pc.removeEventListener("icegatheringstatechange", check);
          resolve();
        }
      };
      pc.addEventListener("icegatheringstatechange", check);
      // fail-safe: don't wait too long; speed up WHEP start
      setTimeout(() => {
        try {
          pc.removeEventListener("icegatheringstatechange", check);
        } catch {}
        resolve();
      }, timeoutMs);
    });

  const stopWhep = async () => {
    try {
      const pc = pcRef.current;
      pcRef.current = null;
      if (pc) pc.close();
      const res = whepResourceRef.current;
      whepResourceRef.current = null;
      if (res) {
        try {
          await fetch(res, { method: "DELETE" });
        } catch {}
      }
      setWhepStatus("stopped");
    } catch {}
  };

  const playWhep = async () => {
    setWhepError("");
    setWhepStatus("connecting");
    // cleanup other modes
    if (hlsRef.current) {
      try {
        hlsRef.current.destroy();
      } catch {}
      hlsRef.current = null;
    }
    await stopWhep();
    const video = videoRef.current;
    if (!video) {
      setIsLivePlaying(false);
      return;
    }
    setIsLivePlaying(true);
    // ensure file playback is fully cleared before attaching streams
    try {
      video.pause();
    } catch {}
    try {
      (video as any).srcObject = null;
    } catch {}
    try {
      video.removeAttribute("src");
      video.load();
    } catch {}
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }],
    });
    pcRef.current = pc;
    pc.addTransceiver("video", { direction: "recvonly" });
    pc.addTransceiver("audio", { direction: "recvonly" });
    pc.ontrack = (ev) => {
      if (video.srcObject !== ev.streams[0]) {
        video.srcObject = ev.streams[0];
        video.play().catch(() => {});
      }
    };
    pc.onconnectionstatechange = () => {
      setWhepStatus(pc.connectionState);
    };
    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await waitIceComplete(pc, 1200);
      const whepUrl = buildWhepUrlFromDevice();
      if (!whepUrl) throw new Error("WHEP URL is not available");
      const resp = await fetch(whepUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/sdp",
          Accept: "application/sdp",
        },
        body: pc.localDescription?.sdp || "",
      });
      if (!resp.ok) throw new Error(`WHEP POST failed: ${resp.status}`);
      const answerSdp = await resp.text();
      const loc = resp.headers.get("Location");
      if (loc) whepResourceRef.current = new URL(loc, whepUrl).toString();
      await pc.setRemoteDescription({ type: "answer", sdp: answerSdp });
      setWhepStatus("connected");
      setIsLivePlaying(true);
    } catch (e: any) {
      setWhepError(String(e?.message || e));
      setWhepStatus("error");
      await stopWhep();
      setIsLivePlaying(false);
    }
  };

  const stopAll = async () => {
    if (hlsRef.current) {
      try {
        hlsRef.current.destroy();
      } catch {}
      hlsRef.current = null;
    }
    await stopWhep();
    const v = videoRef.current;
    if (v) {
      v.pause();
      v.removeAttribute("src");
      (v as any).srcObject = null;
      v.load();
    }
    setIsLivePlaying(false);
  };

  const goFullscreen = () => {
    const el = videoRef.current;
    if (!el) return;
    const anyEl = el as any;
    (
      anyEl.requestFullscreen ||
      anyEl.webkitRequestFullscreen ||
      anyEl.msRequestFullscreen ||
      anyEl.mozRequestFullScreen
    )?.call(el);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        カメラ ライブ/録画 再生
      </Typography>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box
            sx={{
              display: "flex",
              gap: 2,
              flexWrap: "wrap",
              alignItems: "center",
            }}
          >
            <FormControl sx={{ minWidth: 220 }}>
              <InputLabel id="stream-select-label">
                オンラインのカメラ
              </InputLabel>
              <Select
                id="stream-select"
                labelId="stream-select-label"
                label="オンラインのカメラ"
                value={deviceId}
                name="deviceId"
                onChange={(e) => {
                  setRecordingSelectionMode("auto");
                  setDeviceId(e.target.value);
                }}
              >
                {streams.map((s) => (
                  <MenuItem key={s.path} value={s.device_id}>
                    {s.device_id}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl sx={{ minWidth: 140 }}>
              <InputLabel id="mode-label">再生方式</InputLabel>
              <Select
                id="mode-select"
                labelId="mode-label"
                label="再生方式"
                value={mode}
                name="playbackMode"
                onChange={(e) => setMode(e.target.value as any)}
              >
                <MenuItem value="whep">低遅延（WHEP）</MenuItem>
                <MenuItem value="hls">標準（HLS）</MenuItem>
              </Select>
            </FormControl>
            <Button
              variant="contained"
              startIcon={<PlayArrowIcon />}
              disabled={!deviceId || isLivePlaying}
              color={isLivePlaying ? "success" : "primary"}
              onClick={async () => {
                await stopAll();
                mode === "whep" ? await playWhep() : play(buildUrlFromDevice());
              }}
            >
              {isLivePlaying ? "ライブ再生中" : "ライブ再生開始"}
            </Button>
            <Button
              variant="outlined"
              color="warning"
              startIcon={<StopIcon />}
              disabled={!isLivePlaying}
              onClick={stopAll}
            >
              {isLivePlaying ? "停止" : "停止済み"}
            </Button>
            <TextField
              size="small"
              label="HLS URL (手動)"
              sx={{ minWidth: 360 }}
              value={manualUrl}
              id="manual-hls-url"
              name="manualHlsUrl"
              onChange={(e) => setManualUrl(e.target.value)}
            />
            <Button variant="outlined" onClick={() => play(manualUrl)}>
              手動URLで再生
            </Button>
          </Box>
        </CardContent>
      </Card>

      <Box
        sx={{
          position: "relative",
          width: "100%",
          maxWidth: "min(100vw, 1280px)",
          aspectRatio: "16 / 9",
          background: "#000",
        }}
      >
        <video
          ref={videoRef}
          controls
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            background: "#000",
          }}
          onDoubleClick={goFullscreen}
          onTimeUpdate={(e) => {
            if (!recClipStartIso) return;
            if ((window as any).__recSeeking) return; // シーク確定中はバー更新を抑止
            const v = e.currentTarget as HTMLVideoElement;
            const rel = Math.max(0, Math.floor(v.currentTime || 0));
            const abs = recBaseOffsetSec + rel;
            const capped =
              recClipDuration != null
                ? Math.min(abs, Math.max(0, Math.floor(recClipDuration)))
                : abs;
            setRecSeekPos(capped);
          }}
        />
      </Box>
      {(hlsError || whepError || (mode === "whep" && whepStatus)) && (
        <Box sx={{ mt: 1 }}>
          {mode === "whep" && whepStatus && (
            <Typography variant="body2" color="text.secondary">
              WHEP 状態: {whepStatus}
            </Typography>
          )}
          {hlsError && (
            <Typography variant="body2" color="error">
              HLS エラー: {hlsError}
            </Typography>
          )}
          {whepError && (
            <Typography variant="body2" color="error">
              WHEP エラー: {whepError}
            </Typography>
          )}
        </Box>
      )}

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            録画一覧と再生
          </Typography>
          <Box
            sx={{
              display: "flex",
              gap: 2,
              flexWrap: "wrap",
              alignItems: "center",
              mb: 2,
            }}
          >
            <TextField
              size="small"
              sx={{ minWidth: 300 }}
              label="デバイス/パス検索"
              value={recordingFilter}
              id="recording-filter"
              name="recordingFilter"
              onChange={(e) => setRecordingFilter(e.target.value)}
              placeholder="device-id や path を入力"
            />
            <Button
              variant="outlined"
              onClick={fetchRecordingIndex}
              disabled={recordingIndexLoading}
            >
              {recordingIndexLoading ? "更新中..." : "録画インデックス更新"}
            </Button>
            {recordingIndexError && (
              <Typography variant="body2" color="error">
                {recordingIndexError}
              </Typography>
            )}
            {!recordingIndexLoading && recordingIndex.length > 0 && (
              <Typography variant="body2" sx={{ ml: "auto" }}>
                登録パス: {recordingIndex.length} 件
              </Typography>
            )}
          </Box>
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", md: "row" },
              gap: 2,
            }}
          >
            <Box
              sx={{
                flexBasis: { xs: "100%", md: 280 },
                flexShrink: 0,
                maxHeight: 320,
                overflowY: "auto",
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 1,
              }}
            >
              {recordingIndexLoading ? (
                <Typography variant="body2" sx={{ p: 2 }}>
                  読み込み中...
                </Typography>
              ) : filteredRecordingIndex.length === 0 ? (
                <Typography variant="body2" sx={{ p: 2 }}>
                  一致する録画がありません。
                </Typography>
              ) : (
                filteredRecordingIndex.map((item) => {
                  const isActive = item.path === selectedRecordingPath;
                  return (
                    <Box
                      key={item.path}
                      sx={{
                        px: 1.5,
                        py: 1,
                        cursor: "pointer",
                        borderBottom: "1px solid",
                        borderColor: "divider",
                        bgcolor: isActive ? "action.selected" : "transparent",
                        "&:hover": {
                          bgcolor: isActive ? "action.selected" : "action.hover",
                        },
                      }}
                      onClick={() => {
                        setRecordingSelectionMode("manual");
                        setSelectedRecordingPath(item.path);
                        setRecPath(item.path);
                        setSegmentQuery("");
                        void loadRecordingPath(item.path, { resetSeek: false });
                      }}
                    >
                      <Typography variant="subtitle2">
                        {item.device_id || deriveDeviceId(item.path)}
                      </Typography>
                      <Typography variant="caption" sx={{ display: "block" }}>
                        最新 {formatTimestamp(item.latest_start)} ／ {item.segment_count}件
                      </Typography>
                    </Box>
                  );
                })
              )}
            </Box>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              {selectedRecordingPath ? (
                <>
                  <Typography variant="subtitle1" sx={{ mb: 1 }}>
                    選択中: {deriveDeviceId(selectedRecordingPath)} ({selectedRecordingPath})
                  </Typography>
                  {activeRecordingMeta && (
                    <Typography variant="body2" sx={{ mb: 2 }}>
                      最新: {formatTimestamp(activeRecordingMeta.latest_start)} ／ 最古: {" "}
                      {formatTimestamp(activeRecordingMeta.earliest_start)} ／ 総{" "}
                      {activeRecordingMeta.segment_count} 件
                    </Typography>
                  )}
                  <Box
                    sx={{
                      display: "flex",
                      gap: 2,
                      flexWrap: "wrap",
                      alignItems: "center",
                      mb: 2,
                    }}
                  >
                    <TextField
                      size="small"
                      sx={{ minWidth: 320, flexGrow: 1 }}
                      label="録画パス"
                      value={recPath}
                      id="recording-path-input"
                      name="recordingPath"
                      onChange={(e) => setRecPath(e.target.value)}
                      placeholder="uplink/xxxxxxxxxxxxxxxx"
                    />
                    <Button
                      variant="outlined"
                      disabled={!recPath}
                      onClick={() => {
                        const safe = recPath.trim();
                        if (!safe) {
                          setRecError("録画パスが空です");
                          return;
                        }
                        setRecordingSelectionMode("manual");
                        setSelectedRecordingPath(safe);
                        setSegmentQuery("");
                        void loadRecordingPath(safe, { resetSeek: true, force: true });
                      }}
                    >
                      選択パスを読込
                    </Button>
                    <FormControl sx={{ minWidth: 140 }}>
                      <InputLabel id="fmt-label">録画フォーマット</InputLabel>
                      <Select
                        id="recording-format-select"
                        labelId="fmt-label"
                        label="録画フォーマット"
                        value={recFormatMp4 ? "mp4" : "fmp4"}
                        name="recordingFormat"
                        onChange={(e) =>
                          setRecFormatMp4((e.target.value as string) === "mp4")
                        }
                      >
                        <MenuItem value="mp4">MP4（互換性高）</MenuItem>
                        <MenuItem value="fmp4">fMP4（デフォルト）</MenuItem>
                      </Select>
                    </FormControl>
                    <Button
                      variant="text"
                      onClick={() => {
                        const s = streams.find((x) => x.device_id === deviceId);
                        const raw = s ? s.path : deviceId ? `uplink/${deviceId}` : "";
                        if (raw) {
                          setRecordingSelectionMode("auto");
                          setRecPath(raw);
                          setSelectedRecordingPath(raw);
                          setSegmentQuery("");
                          void loadRecordingPath(raw, { resetSeek: false });
                        }
                      }}
                    >
                      現在のデバイスから入力
                    </Button>
                  </Box>
                  <Box
                    sx={{
                      display: "flex",
                      gap: 2,
                      flexWrap: "wrap",
                      alignItems: "center",
                      mb: 2,
                    }}
                  >
                    <TextField
                      size="small"
                      sx={{ minWidth: 280, flexGrow: 1 }}
                      label="録画検索 (開始時刻)"
                      value={segmentQuery}
                      id="segment-query"
                      name="segmentQuery"
                      onChange={(e) => setSegmentQuery(e.target.value)}
                      placeholder="2025-09-22T10:00"
                    />
                    <Typography variant="body2">
                      表示件数: {filteredSegments.length}
                    </Typography>
                  </Box>
                  {recClipStartIso && recClipDuration != null && (
                    <Box sx={{ mb: 2 }}>
                      <Typography variant="body2">録画シーク（このクリップ内）</Typography>
                      <Slider
                        value={Math.min(
                          recSeekPos,
                          Math.max(0, recClipDuration ?? 0)
                        )}
                        min={0}
                        max={Math.max(1, Math.floor(recClipDuration ?? 0))}
                        valueLabelDisplay="auto"
                        onChange={(_, val) => {
                          if (typeof val === "number") {
                            setRecSeekPos(val);
                          }
                        }}
                        onChangeCommitted={async (_, val) => {
                          if (typeof val !== "number") return;
                          if (!recClipStartIso) return;
                          const baseMs = new Date(recClipStartIso).getTime();
                          if (!baseMs || isNaN(baseMs)) return;
                          const seekAbsSec = Math.max(0, Math.floor(val));
                          const newStart = new Date(
                            baseMs + seekAbsSec * 1000
                          ).toISOString();
                          const loc = window.location;
                          const getBase = `${loc.protocol}//${loc.hostname}:9996`;
                          const newDur =
                            recClipDuration != null
                              ? Math.max(1, recClipDuration - seekAbsSec)
                              : undefined;
                          const url = `${getBase}/get?path=${encodeURIComponent(
                            recPath
                          )}&start=${encodeURIComponent(newStart)}${
                            newDur ? `&duration=${newDur}` : ""
                          }${recFormatMp4 ? "&format=mp4" : ""}`;
                          try {
                            (window as any).__recSeeking = true;
                            await stopAll();
                            const v = videoRef.current;
                            if (!v) return;
                            (v as any).srcObject = null;
                            v.src = url;
                            await v.play();
                            setRecBaseOffsetSec(seekAbsSec);
                            setRecSeekPos(seekAbsSec);
                            (window as any).__recSeeking = false;
                          } catch (e) {
                            setHlsError(String(e));
                            (window as any).__recSeeking = false;
                          }
                        }}
                      />
                    </Box>
                  )}
                  <Box
                    sx={{
                      display: "flex",
                      gap: 2,
                      flexWrap: "wrap",
                      alignItems: "center",
                      mb: 2,
                    }}
                  >
                    <TextField
                      size="small"
                      sx={{ minWidth: 320 }}
                      label="開始 (RFC3339, 例: 2025-08-24T09:00:00Z)"
                      value={rangeStart}
                      id="range-start"
                      name="rangeStart"
                      onChange={(e) => setRangeStart(e.target.value)}
                    />
                    <TextField
                      size="small"
                      sx={{ minWidth: 320 }}
                      label="終了 (RFC3339, 空なら単一指定)"
                      value={rangeEnd}
                      id="range-end"
                      name="rangeEnd"
                      onChange={(e) => setRangeEnd(e.target.value)}
                    />
                    <Button
                      color="error"
                      variant="outlined"
                      disabled={!recPath || !rangeStart}
                      onClick={async () => {
                        if (
                          !confirm(
                            `この範囲の録画を削除しますか？\npath=${recPath}\nstart=${rangeStart}\nend=${
                              rangeEnd || "(なし)"
                            }\n注意: この操作は元に戻せません。`
                          )
                        )
                          return;
                        try {
                          await axios.delete(`${API_PREFIX}/recordings/range`, {
                            params: {
                              path: recPath,
                              start: rangeStart,
                              ...(rangeEnd ? { end: rangeEnd } : {}),
                            },
                          });
                          await loadRecordingPath(recPath, { force: true });
                        } catch (e: any) {
                          setRecError(
                            `範囲削除に失敗しました: ${String(e?.message || e)}`
                          );
                        }
                      }}
                    >
                      期間内を削除
                    </Button>
                    <Button
                      color="error"
                      variant="outlined"
                      disabled={!recPath}
                      onClick={async () => {
                        if (
                          !confirm(
                            `このパスの全録画を削除しますか？\npath=${recPath}\n注意: この操作は元に戻せません。`
                          )
                        )
                          return;
                        try {
                          await axios.delete(`${API_PREFIX}/recordings/all`, {
                            params: { path: recPath },
                          });
                          await loadRecordingPath(recPath, { force: true });
                        } catch (e: any) {
                          setRecError(
                            `全削除に失敗しました: ${String(e?.message || e)}`
                          );
                        }
                      }}
                    >
                      すべて削除
                    </Button>
                  </Box>
                  {recLoading && (
                    <Typography variant="body2">読み込み中...</Typography>
                  )}
                  {recError && (
                    <Typography variant="body2" color="error">
                      {recError}
                    </Typography>
                  )}
                  {!recLoading && filteredSegments.length > 0 ? (
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns: "1fr auto auto",
                        rowGap: 1,
                        columnGap: 8,
                        alignItems: "center",
                      }}
                    >
                      <Typography variant="subtitle2">開始時刻</Typography>
                      <Typography variant="subtitle2" sx={{ textAlign: "right" }}>
                        長さ
                      </Typography>
                      <Typography variant="subtitle2" sx={{ textAlign: "right" }}>
                        操作
                      </Typography>
                      {filteredSegments.map((it: any) => {
                        const start = it.start as string;
                        const dur = (it as any).duration as number | undefined;
                        let url = (it as any).url as string | undefined;
                        if (!url && (it as any).playback_url)
                          url = (it as any).playback_url as string;
                        if (!url && start) {
                          const loc = window.location;
                          const base = `${loc.protocol}//${loc.hostname}:9996`;
                          url = `${base}/get?path=${encodeURIComponent(
                            recPath
                          )}&start=${encodeURIComponent(start)}${
                            dur ? `&duration=${dur}` : ""
                          }`;
                        }
                        if (url && recFormatMp4) {
                          url += (url.includes("?") ? "&" : "?") + "format=mp4";
                        }
                        return (
                          <React.Fragment key={start}>
                            <Typography variant="body2">{start}</Typography>
                            <Typography
                              variant="body2"
                              sx={{ textAlign: "right" }}
                            >
                              {dur ? `${dur.toFixed(1)}s` : "-"}
                            </Typography>
                            <Box
                              sx={{
                                display: "flex",
                                gap: 1,
                                justifyContent: "flex-end",
                              }}
                            >
                              <Button
                                size="small"
                                variant="outlined"
                                onClick={async () => {
                                  await stopAll();
                                  const v = videoRef.current;
                                  if (!v || !url) return;
                                  try {
                                    (v as any).srcObject = null;
                                    v.src = url;
                                    await v.play();
                                    setRecClipStartIso(start || null);
                                    setRecClipDuration((dur ?? null) as any);
                                    setRecBaseOffsetSec(0);
                                    setRecSeekPos(0);
                                  } catch (e) {
                                    setHlsError(String(e));
                                  }
                                }}
                              >
                                再生
                              </Button>
                              {url && (
                                <Button
                                  size="small"
                                  component="a"
                                  href={url}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  開く
                                </Button>
                              )}
                              <Button
                                size="small"
                                color="error"
                                variant="outlined"
                                onClick={async () => {
                                  if (!recPath || !start) return;
                                  if (
                                    !confirm(
                                      `この録画を削除しますか？\npath=${recPath}\nstart=${start}`
                                    )
                                  )
                                    return;
                                  try {
                                    await axios.delete(
                                      `${API_PREFIX}/recordings/segment`,
                                      { params: { path: recPath, start } }
                                    );
                                    await loadRecordingPath(recPath, {
                                      resetSeek: false,
                                      force: true,
                                    });
                                  } catch (e: any) {
                                    setRecError(
                                      `削除に失敗しました: ${String(
                                        e?.message || e
                                      )}`
                                    );
                                  }
                                }}
                              >
                                削除
                              </Button>
                            </Box>
                          </React.Fragment>
                        );
                      })}
                    </Box>
                  ) : (
                    !recLoading && (
                      <Typography variant="body2" color="text.secondary">
                        録画が見つかりません。
                      </Typography>
                    )
                  )}
                </>
              ) : (
                <Typography variant="body2">
                  左の一覧から録画を選択してください。
                </Typography>
              )}
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
