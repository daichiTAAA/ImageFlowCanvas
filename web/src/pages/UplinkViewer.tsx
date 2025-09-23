import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
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
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDateFns } from "@mui/x-date-pickers/AdapterDateFns";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import StopIcon from "@mui/icons-material/Stop";
import axios from "axios";
import { formatRFC3339, parseISO, isValid } from "date-fns";
import { inspectionApi } from "../services/api";

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

type DeviceProcessLink = {
  id: string;
  device_id: string;
  process_code: string;
  process?: {
    process_code?: string;
    process_name?: string;
  } | null;
};

const API_PREFIX = "/api/uplink";

const serializeStreams = (items: StreamItem[] | undefined) =>
  (items ?? [])
    .map(
      (s) =>
        `${s?.path ?? ""}|${s?.device_id ?? ""}|${s?.hls_url ?? ""}|${
          s?.state ?? ""
        }|${String(s?.readers ?? "")}|${String(s?.publishers ?? "")}`
    )
    .sort()
    .join("||");

const areStreamListsEqual = (
  prev: StreamItem[] | undefined,
  next: StreamItem[] | undefined
) => serializeStreams(prev) === serializeStreams(next);

const serializeIndexSegments = (
  segments: RecordingIndexSegment[] | undefined
) => (segments ?? []).map((s) => s?.start ?? "").join("|");

const areRecordingIndexItemsEqual = (
  a?: RecordingIndexItem | null,
  b?: RecordingIndexItem | null
) => {
  if (!a && !b) return true;
  if (!a || !b) return false;
  if (a.path !== b.path) return false;
  if ((a.device_id ?? "") !== (b.device_id ?? "")) return false;
  if ((a.segment_count ?? 0) !== (b.segment_count ?? 0)) return false;
  if ((a.latest_start ?? "") !== (b.latest_start ?? "")) return false;
  if ((a.earliest_start ?? "") !== (b.earliest_start ?? "")) return false;
  return (
    serializeIndexSegments(a.segments) === serializeIndexSegments(b.segments)
  );
};

const areRecordingIndexListsEqual = (
  prev: RecordingIndexItem[] | undefined,
  next: RecordingIndexItem[] | undefined
) => {
  const a = prev ?? [];
  const b = next ?? [];
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) {
    if (!areRecordingIndexItemsEqual(a[i], b[i])) {
      return false;
    }
  }
  return true;
};

const areObjectArraysEqual = (prev: any[], next: any[], keys: string[]) => {
  if (!Array.isArray(prev) || !Array.isArray(next)) return false;
  if (prev.length !== next.length) return false;
  for (let i = 0; i < prev.length; i += 1) {
    const p = prev[i] ?? {};
    const n = next[i] ?? {};
    for (const key of keys) {
      if ((p?.[key] ?? null) !== (n?.[key] ?? null)) {
        return false;
      }
    }
  }
  return true;
};

export default function UplinkViewer() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const whepResourceRef = useRef<string | null>(null);
  const loadRequestIdRef = useRef(0);
  const lastLoadedPathRef = useRef<string | null>(null);

  const [deviceId, setDeviceId] = useState("");
  const [streams, setStreams] = useState<StreamItem[]>([]);
  const [deviceProcessLinks, setDeviceProcessLinks] =
    useState<DeviceProcessLink[]>([]);
  const streamsRef = useRef<StreamItem[]>([]);
  const [hlsError, setHlsError] = useState("");
  const [mode, setMode] = useState<"hls" | "whep">("whep");
  const [whepStatus, setWhepStatus] = useState("");
  const [whepError, setWhepError] = useState("");

  const [recordingIndex, setRecordingIndex] = useState<RecordingIndexItem[]>(
    []
  );
  const [recordingIndexLoading, setRecordingIndexLoading] = useState(false);
  const [recordingIndexError, setRecordingIndexError] = useState("");
  const [recordingFilter, setRecordingFilter] = useState("");
  const [selectedRecordingPath, setSelectedRecordingPath] = useState("");
  const [recordingSelectionMode, setRecordingSelectionMode] = useState<
    "auto" | "manual"
  >("auto");
  const selectedRecordingPathRef = useRef<string>("");

  const [isLivePlaying, setIsLivePlaying] = useState(false);

  const [recLoading, setRecLoading] = useState(false);
  const [recError, setRecError] = useState("");
  const [recPath, setRecPath] = useState("");
  const [recSegments, setRecSegments] = useState<any[]>([]);
  const [recPlayback, setRecPlayback] = useState<any[]>([]);
  const [rangeStart, setRangeStart] = useState("");
  const [rangeEnd, setRangeEnd] = useState("");
  const [rangeStartDt, setRangeStartDt] = useState<Date | null>(null);
  const [rangeEndDt, setRangeEndDt] = useState<Date | null>(null);
  const recordingIndexRef = useRef<RecordingIndexItem[]>([]);
  // 録画シーク用の絶対オフセット方式
  const [recClipStartIso, setRecClipStartIso] = useState<string | null>(null); // クリップ全体の開始ISO
  const [recClipDuration, setRecClipDuration] = useState<number | null>(null); // クリップ総尺（秒）
  const [recBaseOffsetSec, setRecBaseOffsetSec] = useState<number>(0); // 現ストリームの先頭がクリップ先頭から何秒か
  const [recSeekPos, setRecSeekPos] = useState<number>(0); // 表示用の絶対位置（秒）

  const RECORDING_PLAYBACK_FORMAT = "mp4";

  const deriveDeviceId = useCallback((path: string) => {
    if (!path) return path;
    if (path.includes("/")) return path.split("/", 1)[1];
    if (path.startsWith("uplink-")) return path.split("uplink-", 1)[1];
    return path;
  }, []);

  useEffect(() => {
    selectedRecordingPathRef.current = selectedRecordingPath;
  }, [selectedRecordingPath]);

  useEffect(() => {
    recordingIndexRef.current = recordingIndex;
  }, [recordingIndex]);

  useEffect(() => {
    streamsRef.current = streams;
  }, [streams]);

  const deviceProcessMap = useMemo(() => {
    const map: Record<string, { process_code: string; process_name?: string }> = {};
    deviceProcessLinks.forEach((link) => {
      if (!link?.device_id) return;
      map[link.device_id] = {
        process_code: link.process_code,
        process_name: link.process?.process_name ?? undefined,
      };
    });
    return map;
  }, [deviceProcessLinks]);

  const selectedDeviceProcess = useMemo(() => {
    if (!deviceId) return null;
    return deviceProcessMap[deviceId] || null;
  }, [deviceId, deviceProcessMap]);

  const timestampFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat(undefined, {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
        timeZoneName: "short",
      }),
    []
  );

  const formatTimestamp = useCallback(
    (iso?: string | null) => {
      if (!iso) return "-";
      const d = new Date(iso);
      if (Number.isNaN(d.getTime())) return iso;
      try {
        return timestampFormatter.format(d);
      } catch (err) {
        return d.toLocaleString();
      }
    },
    [timestampFormatter]
  );

  const toRfc3339 = useCallback((date: Date) => {
    try {
      return formatRFC3339(date, { fractionDigits: 0 });
    } catch (err) {
      return date.toISOString();
    }
  }, []);

  const handleRangeStartDateChange = useCallback(
    (value: Date | null) => {
      setRangeStartDt(value);
      setRangeStart(value ? toRfc3339(value) : "");
    },
    [toRfc3339]
  );

  const handleRangeEndDateChange = useCallback(
    (value: Date | null) => {
      setRangeEndDt(value);
      setRangeEnd(value ? toRfc3339(value) : "");
    },
    [toRfc3339]
  );

  const handleRangeStartTextChange = useCallback((value: string) => {
    setRangeStart(value);
    if (!value) {
      setRangeStartDt(null);
      return;
    }
    try {
      const parsed = parseISO(value);
      if (isValid(parsed)) {
        setRangeStartDt(parsed);
      }
    } catch {
      // ignore parse failures while user is typing free-form RFC3339 strings
    }
  }, []);

  const handleRangeEndTextChange = useCallback((value: string) => {
    setRangeEnd(value);
    if (!value) {
      setRangeEndDt(null);
      return;
    }
    try {
      const parsed = parseISO(value);
      if (isValid(parsed)) {
        setRangeEndDt(parsed);
      }
    } catch {
      // ignore parse failures while user is typing free-form RFC3339 strings
    }
  }, []);

  const loadRecordingPath = useCallback(
    async (
      path: string,
      {
        resetSeek = true,
        force = false,
      }: { resetSeek?: boolean; force?: boolean } = {}
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
        const nextSegments = Array.isArray(data.segments) ? data.segments : [];
        const nextPlayback = Array.isArray(data.playback) ? data.playback : [];
        setRecSegments((prev) =>
          areObjectArraysEqual(prev, nextSegments, [
            "start",
            "duration",
            "url",
            "playback_url",
          ])
            ? prev
            : nextSegments
        );
        setRecPlayback((prev) =>
          areObjectArraysEqual(prev, nextPlayback, ["start", "duration", "url"])
            ? prev
            : nextPlayback
        );
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

  const fetchDeviceProcessLinks = useCallback(async () => {
    try {
      const resp = await inspectionApi.listDeviceProcessLinks({ page_size: 300 });
      const items: DeviceProcessLink[] = resp.items || [];
      setDeviceProcessLinks(items);
    } catch (e) {
      console.error("Failed to fetch device-process links", e);
    }
  }, []);

  const fetchStreams = useCallback(async () => {
    try {
      const resp = await axios.get(`${API_PREFIX}/streams`);
      const items: StreamItem[] = resp.data.items || [];
      if (!areStreamListsEqual(streamsRef.current, items)) {
        setStreams(items);
      }
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
              return {
                start: typeof start === "string" ? start : String(start),
              };
            })
            .filter(Boolean) as RecordingIndexSegment[];
          segments.sort((a, b) => b.start.localeCompare(a.start));
          return {
            path,
            device_id: it.device_id || deriveDeviceId(path),
            segment_count:
              typeof it.segment_count === "number"
                ? it.segment_count
                : segments.length,
            latest_start: it.latest_start || segments[0]?.start || null,
            earliest_start:
              it.earliest_start || segments[segments.length - 1]?.start || null,
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

      const previousIndex = recordingIndexRef.current;
      const currentSelected = selectedRecordingPathRef.current;
      const indexChanged = !areRecordingIndexListsEqual(previousIndex, mapped);

      if (!indexChanged) {
        return;
      }

      setRecordingIndex(mapped);

      if (mapped.length === 0) {
        setRecSegments((prev) => (prev.length === 0 ? prev : []));
        setRecPlayback((prev) => (prev.length === 0 ? prev : []));
        setRecClipStartIso(null);
        setRecClipDuration(null);
        setRecBaseOffsetSec(0);
        setRecSeekPos(0);
        lastLoadedPathRef.current = null;
        if (selectedRecordingPathRef.current) {
          setSelectedRecordingPath("");
          setRecPath("");
        }
        return;
      }

      const hasSelected = Boolean(
        currentSelected && mapped.some((item) => item.path === currentSelected)
      );

      if (!hasSelected) {
        const initialPath = mapped[0].path;
        setRecordingSelectionMode("auto");
        setSelectedRecordingPath(initialPath);
        setRecPath(initialPath);
        await loadRecordingPath(initialPath, { force: true });
        return;
      }

      if (currentSelected) {
        const prevSelectedItem =
          previousIndex.find((item) => item.path === currentSelected) ?? null;
        const nextSelectedItem =
          mapped.find((item) => item.path === currentSelected) ?? null;
        const shouldReloadSelected =
          nextSelectedItem &&
          (!prevSelectedItem ||
            !areRecordingIndexItemsEqual(prevSelectedItem, nextSelectedItem));

        if (shouldReloadSelected) {
          setRecPath(currentSelected);
          await loadRecordingPath(currentSelected, {
            resetSeek: false,
            force: true,
          });
        }
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
    fetchDeviceProcessLinks();
    const t = setInterval(fetchDeviceProcessLinks, 60000);
    return () => clearInterval(t);
  }, [fetchDeviceProcessLinks]);

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
    void loadRecordingPath(path, { resetSeek: false });
  }, [
    deviceId,
    streams,
    loadRecordingPath,
    recordingSelectionMode,
    selectedRecordingPath,
  ]);

  const filteredRecordingIndex = useMemo(() => {
    const q = recordingFilter.trim().toLowerCase();
    if (!q) return recordingIndex;
    return recordingIndex.filter((item) => {
      const did = item.device_id?.toLowerCase?.() || "";
      const path = item.path?.toLowerCase?.() || "";
      const info = deviceProcessMap[item.device_id];
      const processCode = info?.process_code
        ? info.process_code.toLowerCase()
        : "";
      const processName = info?.process_name
        ? info.process_name.toLowerCase()
        : "";
      return (
        did.includes(q) ||
        path.includes(q) ||
        processCode.includes(q) ||
        processName.includes(q)
      );
    });
  }, [recordingIndex, recordingFilter, deviceProcessMap]);

  const activeRecordingMeta = useMemo(
    () => recordingIndex.find((item) => item.path === selectedRecordingPath),
    [recordingIndex, selectedRecordingPath]
  );

  const displaySegments = useMemo(
    () => (recPlayback.length > 0 ? recPlayback : recSegments) as any[],
    [recPlayback, recSegments]
  );

  const filteredSegments = useMemo(() => {
    const base = Array.isArray(displaySegments) ? displaySegments : [];
    if (!rangeStartDt && !rangeEndDt) {
      return base;
    }
    const startMs = rangeStartDt ? rangeStartDt.getTime() : null;
    const endMs = rangeEndDt ? rangeEndDt.getTime() : null;
    return base.filter((segment: any) => {
      const raw = segment?.start;
      if (!raw) return false;
      const ms = new Date(raw).getTime();
      if (Number.isNaN(ms)) return false;
      if (startMs !== null && ms < startMs) return false;
      if (endMs !== null && ms > endMs) return false;
      return true;
    });
  }, [displaySegments, rangeStartDt, rangeEndDt]);

  const isRangeFilterActive = useMemo(
    () => Boolean(rangeStartDt || rangeEndDt),
    [rangeStartDt, rangeEndDt]
  );

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
    return `http://${host}:${port}/${
      deviceId ? `uplink/${deviceId}` : "uplink"
    }/index.m3u8`;
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
    <LocalizationProvider dateAdapter={AdapterDateFns}>
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
                  {streams.map((s) => {
                    const info = deviceProcessMap[s.device_id];
                    return (
                      <MenuItem key={s.path} value={s.device_id}>
                        <Box sx={{ display: "flex", flexDirection: "column" }}>
                          <Typography variant="body2" component="span">
                            {s.device_id}
                          </Typography>
                          {info ? (
                            <Typography
                              variant="caption"
                              color="text.secondary"
                              component="span"
                            >
                              工程: {info.process_code}
                              {info.process_name
                                ? ` (${info.process_name})`
                                : ""}
                            </Typography>
                          ) : (
                            <Typography
                              variant="caption"
                              color="text.disabled"
                              component="span"
                            >
                              工程未登録
                            </Typography>
                          )}
                        </Box>
                      </MenuItem>
                    );
                  })}
                </Select>
              </FormControl>
              <Box sx={{ minWidth: 200 }}>
                <Typography variant="body2">
                  {selectedDeviceProcess
                    ? `工程コード: ${selectedDeviceProcess.process_code}`
                    : "工程コード: 未登録"}
                </Typography>
                {selectedDeviceProcess?.process_name && (
                  <Typography variant="caption" color="text.secondary">
                    {selectedDeviceProcess.process_name}
                  </Typography>
                )}
              </Box>
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
                  mode === "whep"
                    ? await playWhep()
                    : play(buildUrlFromDevice());
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
                    const info = deviceProcessMap[item.device_id];
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
                            bgcolor: isActive
                              ? "action.selected"
                              : "action.hover",
                          },
                        }}
                        onClick={() => {
                          setRecordingSelectionMode("manual");
                          setSelectedRecordingPath(item.path);
                          setRecPath(item.path);
                          void loadRecordingPath(item.path, {
                            resetSeek: false,
                          });
                        }}
                      >
                        <Typography variant="subtitle2">
                          {item.device_id || deriveDeviceId(item.path)}
                        </Typography>
                        {info && (
                          <Typography
                            variant="caption"
                            sx={{ display: "block" }}
                            color="text.secondary"
                          >
                            工程: {info.process_code}
                            {info.process_name ? ` (${info.process_name})` : ""}
                          </Typography>
                        )}
                        <Typography variant="caption" sx={{ display: "block" }}>
                          最新 {formatTimestamp(item.latest_start)} ／{" "}
                          {item.segment_count}件
                        </Typography>
                      </Box>
                    );
                  })
                )}
              </Box>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                {selectedRecordingPath ? (
                  <>
                    {recClipStartIso && recClipDuration != null && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body2">
                          録画シーク（このクリップ内）
                        </Typography>
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
                            const params = new URLSearchParams();
                            params.set("path", recPath);
                            params.set("start", newStart);
                            if (newDur) params.set("duration", String(newDur));
                            if (RECORDING_PLAYBACK_FORMAT) {
                              params.set("format", RECORDING_PLAYBACK_FORMAT);
                            }
                            const url = `${getBase}/get?${params.toString()}`;
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
                        flexWrap: { xs: "wrap", md: "nowrap" },
                        alignItems: "stretch",
                        mb: 2,
                        width: "100%",
                      }}
                    >
                      <Box
                        sx={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 1,
                          minWidth: 280,
                          flexBasis: 280,
                          flexGrow: 1,
                          height: "100%",
                        }}
                      >
                        <DateTimePicker
                          label="開始 (ローカル時刻)"
                          value={rangeStartDt}
                          onChange={handleRangeStartDateChange}
                          ampm={false}
                          format="yyyy/MM/dd HH:mm:ss"
                          slotProps={{
                            textField: {
                              size: "small",
                              id: "range-start-datetime",
                              sx: { minWidth: 280 },
                            },
                          }}
                          views={[
                            "year",
                            "month",
                            "day",
                            "hours",
                            "minutes",
                            "seconds",
                          ]}
                        />
                      </Box>
                      <Box
                        sx={{
                          display: "flex",
                          flexDirection: "column",
                          gap: 1,
                          minWidth: 280,
                          flexBasis: 280,
                          flexGrow: 1,
                          height: "100%",
                        }}
                      >
                        <DateTimePicker
                          label="終了 (ローカル時刻)"
                          value={rangeEndDt}
                          onChange={handleRangeEndDateChange}
                          ampm={false}
                          format="yyyy/MM/dd HH:mm:ss"
                          slotProps={{
                            textField: {
                              size: "small",
                              id: "range-end-datetime",
                              sx: { minWidth: 280 },
                            },
                          }}
                          views={[
                            "year",
                            "month",
                            "day",
                            "hours",
                            "minutes",
                            "seconds",
                          ]}
                        />
                      </Box>
                      <Box
                        sx={{
                          display: "flex",
                          flexDirection: { xs: "column", sm: "row" },
                          gap: { xs: 1, sm: 2 },
                          minWidth: 200,
                          flexBasis: 220,
                          flexGrow: 0,
                          height: "100%",
                          alignItems: "stretch",
                          justifyContent: "flex-start",
                        }}
                      >
                        <Button
                          sx={{ minHeight: 40, whiteSpace: "nowrap" }}
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
                              await axios.delete(
                                `${API_PREFIX}/recordings/range`,
                                {
                                  params: {
                                    path: recPath,
                                    start: rangeStart,
                                    ...(rangeEnd ? { end: rangeEnd } : {}),
                                  },
                                }
                              );
                              await loadRecordingPath(recPath, { force: true });
                            } catch (e: any) {
                              setRecError(
                                `範囲削除に失敗しました: ${String(
                                  e?.message || e
                                )}`
                              );
                            }
                          }}
                        >
                          期間内を削除
                        </Button>
                        <Button
                          sx={{ minHeight: 40, whiteSpace: "nowrap" }}
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
                              await axios.delete(
                                `${API_PREFIX}/recordings/all`,
                                {
                                  params: { path: recPath },
                                }
                              );
                              await loadRecordingPath(recPath, { force: true });
                            } catch (e: any) {
                              setRecError(
                                `全削除に失敗しました: ${String(
                                  e?.message || e
                                )}`
                              );
                            }
                          }}
                        >
                          すべて削除
                        </Button>
                      </Box>
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
                        <Typography
                          variant="subtitle2"
                          sx={{ textAlign: "right" }}
                        >
                          長さ
                        </Typography>
                        <Typography
                          variant="subtitle2"
                          sx={{ textAlign: "right" }}
                        >
                          操作
                        </Typography>
                        {filteredSegments.map((it: any) => {
                          const start = it.start as string;
                          const formattedStart = formatTimestamp(start);
                          const dur = (it as any).duration as
                            | number
                            | undefined;
                          let url = (it as any).url as string | undefined;
                          if (!url && (it as any).playback_url)
                            url = (it as any).playback_url as string;
                          if (!url && start) {
                            const loc = window.location;
                            const base = `${loc.protocol}//${loc.hostname}:9996`;
                            const params = new URLSearchParams();
                            params.set("path", recPath);
                            params.set("start", start);
                            if (dur) params.set("duration", String(dur));
                            if (RECORDING_PLAYBACK_FORMAT) {
                              params.set("format", RECORDING_PLAYBACK_FORMAT);
                            }
                            url = `${base}/get?${params.toString()}`;
                          } else if (
                            url &&
                            RECORDING_PLAYBACK_FORMAT &&
                            !url.includes("format=")
                          ) {
                            url +=
                              (url.includes("?") ? "&" : "?") +
                              `format=${RECORDING_PLAYBACK_FORMAT}`;
                          }
                          return (
                            <React.Fragment key={start}>
                              <Typography
                                variant="body2"
                                title={start || undefined}
                              >
                                {formattedStart}
                              </Typography>
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
                          {displaySegments.length === 0
                            ? "録画が見つかりません。"
                            : "指定した期間に一致する録画がありません。"}
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
    </LocalizationProvider>
  );
}
