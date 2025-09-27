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
  whep_url?: string;
};

type ThinkletSegmentMeta = {
  deviceId?: string;
  deviceIdentifier?: string;
  deviceUuid?: string;
  deviceName?: string;
  deviceLastState?: string;
  deviceLastSeenAt?: string;
  session?: {
    id?: string;
    status?: string;
    startedAt?: string;
    endedAt?: string | null;
    coverageEnd?: string | null;
    startCommand?: string | null;
    startConfidence?: number | null;
    endCommand?: string | null;
    endConfidence?: number | null;
  } | null;
  lastEvent?: {
    command?: string | null;
    normalizedCommand?: string | null;
    recognizedText?: string | null;
    confidence?: number | null;
    source?: string | null;
    timestamp?: string | null;
  } | null;
};

type RecordingSegment = {
  start: string;
  duration?: number;
  url?: string;
  playback_url?: string;
  thinklet?: ThinkletSegmentMeta | null;
  thinkletToken?: string;
};

type RecordingIndexSegment = {
  start: string;
};

type RecordingIndexItem = {
  path: string;
  device_id: string;
  device_name?: string | null;
  device_last_state?: string | null;
  device_last_seen_at?: string | null;
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

type DeviceStatusSummary = {
  deviceId: string;
  deviceUuid?: string | null;
  deviceIdentifier?: string | null;
  deviceName: string;
  state?: string | null;
  sessionId?: string | null;
  batteryLevel?: number | null;
  temperatureC?: number | null;
  networkQuality?: string | null;
  isStreaming: boolean;
  lastSeenAt?: string | null;
  processCode?: string | null;
  processName?: string | null;
};

type DeviceOption = {
  deviceId: string;
  status: DeviceStatusSummary | null;
  stream: StreamItem | null;
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

const serializeDeviceStatuses = (items: DeviceStatusSummary[]) =>
  items
    .map((s) =>
      [
        s.deviceId ?? "",
        s.deviceName ?? "",
        s.deviceUuid ?? "",
        s.state ?? "",
        s.sessionId ?? "",
        s.networkQuality ?? "",
        s.isStreaming ? "1" : "0",
        s.processCode ?? "",
        s.processName ?? "",
      ].join("|")
    )
    .sort()
    .join("||");

const areDeviceStatusListsEqual = (
  prev: DeviceStatusSummary[] | undefined,
  next: DeviceStatusSummary[] | undefined
) =>
  serializeDeviceStatuses(prev ?? []) === serializeDeviceStatuses(next ?? []);

export default function UplinkViewer() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const whepResourceRef = useRef<string | null>(null);
  const loadRequestIdRef = useRef(0);
  const lastLoadedPathRef = useRef<string | null>(null);

  const [deviceId, setDeviceId] = useState("");
  const [streams, setStreams] = useState<StreamItem[]>([]);
  const [deviceProcessLinks, setDeviceProcessLinks] = useState<
    DeviceProcessLink[]
  >([]);
  const [deviceStatuses, setDeviceStatuses] = useState<DeviceStatusSummary[]>(
    []
  );
  const streamsRef = useRef<StreamItem[]>([]);
  const deviceStatusesRef = useRef<DeviceStatusSummary[]>([]);
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
  const [recSegments, setRecSegments] = useState<RecordingSegment[]>([]);
  const [recPlayback, setRecPlayback] = useState<RecordingSegment[]>([]);
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

  useEffect(() => {
    deviceStatusesRef.current = deviceStatuses;
  }, [deviceStatuses]);

  const deviceStatusMap = useMemo(() => {
    const map: Record<string, DeviceStatusSummary> = {};
    deviceStatuses.forEach((status) => {
      const keys = [
        status?.deviceId,
        status?.deviceIdentifier,
        status?.deviceUuid,
      ].filter((value): value is string => Boolean(value));
      keys.forEach((key) => {
        map[key] = status;
      });
    });
    return map;
  }, [deviceStatuses]);

  const deviceProcessMap = useMemo(() => {
    const map: Record<string, { process_code: string; process_name?: string }> =
      {};
    deviceProcessLinks.forEach((link) => {
      if (!link?.device_id) return;
      map[link.device_id] = {
        process_code: link.process_code,
        process_name: link.process?.process_name ?? undefined,
      };
    });
    deviceStatuses.forEach((status) => {
      if (!status?.processCode) return;
      const keys = [
        status.deviceId,
        status.deviceIdentifier,
        status.deviceUuid,
      ].filter((value): value is string => Boolean(value));
      keys.forEach((key) => {
        map[key] = {
          process_code: status.processCode!,
          process_name: status.processName ?? undefined,
        };
      });
    });
    return map;
  }, [deviceProcessLinks, deviceStatuses]);

  const streamMap = useMemo(() => {
    const map: Record<string, StreamItem> = {};
    streams.forEach((stream) => {
      if (!stream?.device_id) return;
      map[stream.device_id] = stream;
    });
    return map;
  }, [streams]);

  const deviceOptions = useMemo(() => {
    const options: DeviceOption[] = [];
    const seen = new Set<string>();

    deviceStatuses.forEach((status) => {
      const key =
        status?.deviceId ||
        status?.deviceIdentifier ||
        status?.deviceUuid ||
        "";
      if (!key || seen.has(key)) return;
      seen.add(key);
      options.push({
        deviceId: key,
        status,
        stream: streamMap[key] ?? null,
      });
    });

    streams.forEach((stream) => {
      const key = stream?.device_id;
      if (!key || seen.has(key)) return;
      seen.add(key);
      options.push({
        deviceId: key,
        status: null,
        stream,
      });
    });

    options.sort((a, b) => {
      const labelA = (a.status?.deviceName || a.deviceId || "").toLowerCase();
      const labelB = (b.status?.deviceName || b.deviceId || "").toLowerCase();
      if (labelA < labelB) return -1;
      if (labelA > labelB) return 1;
      return 0;
    });

    return options;
  }, [deviceStatuses, streamMap]);

  const selectedDeviceOption = useMemo(
    () =>
      deviceOptions.find((option) => option.deviceId === deviceId) ?? null,
    [deviceId, deviceOptions]
  );

  useEffect(() => {
    if (deviceId) return;
    if (deviceOptions.length === 0) return;
    const streamingPreferred = deviceOptions.find(
      (option) => option.status?.isStreaming || option.stream
    );
    const next = streamingPreferred || deviceOptions[0];
    if (next) {
      setDeviceId(next.deviceId);
    }
  }, [deviceId, deviceOptions]);

  const selectedDeviceProcess = useMemo(() => {
    if (!deviceId) return null;
    const fromMap = deviceProcessMap[deviceId];
    if (fromMap) return fromMap;
    const status = deviceStatusMap[deviceId];
    if (status?.processCode) {
      return {
        process_code: status.processCode,
        process_name: status.processName ?? undefined,
      };
    }
    return null;
  }, [deviceId, deviceProcessMap, deviceStatusMap]);

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
        const segmentsRaw = Array.isArray(data.segments) ? data.segments : [];
        const playbackRaw = Array.isArray(data.playback) ? data.playback : [];

        const thinkletByStart = new Map<string, ThinkletSegmentMeta | null>();
        const tokenByStart = new Map<string, string>();

        const mappedSegments: RecordingSegment[] = segmentsRaw
          .map((seg) => {
            const rawStart = seg?.start;
            const start =
              typeof rawStart === "string"
                ? rawStart
                : rawStart != null
                ? String(rawStart)
                : "";
            if (!start) return null;
            const durationValue = seg?.duration;
            const duration =
              typeof durationValue === "number"
                ? durationValue
                : durationValue != null
                ? Number(durationValue)
                : undefined;
            const thinklet =
              (seg?.thinklet as ThinkletSegmentMeta | null) ?? null;
            const tokenFromBackend =
              typeof seg?.thinkletToken === "string"
                ? seg.thinkletToken
                : undefined;
            const token = tokenFromBackend
              ? tokenFromBackend
              : thinklet
              ? `${
                  thinklet.deviceId ??
                  thinklet.deviceIdentifier ??
                  thinklet.deviceUuid ??
                  ""
                }|${thinklet.session?.id ?? ""}|${
                  thinklet.lastEvent?.timestamp ?? ""
                }`
              : "";
            thinkletByStart.set(start, thinklet);
            tokenByStart.set(start, token);
            return {
              start,
              duration,
              url: typeof seg?.url === "string" ? seg.url : undefined,
              playback_url:
                typeof seg?.playback_url === "string"
                  ? seg.playback_url
                  : undefined,
              thinklet,
              thinkletToken: token,
            } as RecordingSegment;
          })
          .filter(Boolean) as RecordingSegment[];

        const mappedPlayback: RecordingSegment[] = playbackRaw
          .map((seg) => {
            const rawStart = seg?.start;
            const start =
              typeof rawStart === "string"
                ? rawStart
                : rawStart != null
                ? String(rawStart)
                : "";
            if (!start) return null;
            const durationValue = seg?.duration;
            const duration =
              typeof durationValue === "number"
                ? durationValue
                : durationValue != null
                ? Number(durationValue)
                : undefined;
            const thinklet =
              (seg?.thinklet as ThinkletSegmentMeta | null) ??
              thinkletByStart.get(start) ??
              null;
            const tokenFromBackend =
              typeof seg?.thinkletToken === "string"
                ? seg.thinkletToken
                : undefined;
            const token = tokenFromBackend
              ? tokenFromBackend
              : tokenByStart.get(start) ??
                (thinklet
                  ? `${
                      thinklet.deviceId ??
                      thinklet.deviceIdentifier ??
                      thinklet.deviceUuid ??
                      ""
                    }|${thinklet.session?.id ?? ""}|${
                      thinklet.lastEvent?.timestamp ?? ""
                    }`
                  : "");
            if (!tokenByStart.has(start)) {
              tokenByStart.set(start, token);
            }
            if (!thinkletByStart.has(start)) {
              thinkletByStart.set(start, thinklet);
            }
            return {
              start,
              duration,
              url: typeof seg?.url === "string" ? seg.url : undefined,
              playback_url: undefined,
              thinklet,
              thinkletToken: token,
            } as RecordingSegment;
          })
          .filter(Boolean) as RecordingSegment[];

        setRecSegments((prev) =>
          areObjectArraysEqual(prev, mappedSegments, [
            "start",
            "duration",
            "url",
            "playback_url",
            "thinkletToken",
          ])
            ? prev
            : mappedSegments
        );
        setRecPlayback((prev) =>
          areObjectArraysEqual(prev, mappedPlayback, [
            "start",
            "duration",
            "url",
            "thinkletToken",
          ])
            ? prev
            : mappedPlayback
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
      const resp = await inspectionApi.listDeviceProcessLinks({
        page_size: 300,
      });
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
    } catch (e) {
      console.error("Failed to fetch streams", e);
    }
  }, []);

  const fetchDeviceStatuses = useCallback(async () => {
    try {
      const resp = await axios.get(`/api/thinklet/devices/status`);
      const items: DeviceStatusSummary[] = Array.isArray(resp.data)
        ? resp.data
        : [];
      if (!areDeviceStatusListsEqual(deviceStatusesRef.current, items)) {
        setDeviceStatuses(items);
      }
    } catch (e) {
      console.error("Failed to fetch device statuses", e);
    }
  }, []);

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
            device_name: it.device_name ?? null,
            device_last_state: it.device_last_state ?? null,
            device_last_seen_at: it.device_last_seen_at ?? null,
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
    fetchDeviceStatuses();
    const t = setInterval(fetchDeviceStatuses, 5000);
    return () => clearInterval(t);
  }, [fetchDeviceStatuses]);

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
    const path = selectedDeviceOption?.stream?.path ??
      (deviceId ? `uplink/${deviceId}` : "");
    if (!path) return;
    if (selectedRecordingPath === path) return;
    setRecordingSelectionMode("auto");
    setSelectedRecordingPath(path);
    setRecPath(path);
    void loadRecordingPath(path, { resetSeek: false });
  }, [
    deviceId,
    selectedDeviceOption,
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

  const displaySegments = useMemo<RecordingSegment[]>(
    () => (recPlayback.length > 0 ? recPlayback : recSegments),
    [recPlayback, recSegments]
  );

  const sortedDeviceStatuses = useMemo(() => {
    const clone = [...deviceStatuses];
    clone.sort((a, b) => {
    const aKey = (
      a.deviceName ||
      a.deviceId ||
      a.deviceIdentifier ||
      a.deviceUuid ||
      ""
    ).toLowerCase();
    const bKey = (
      b.deviceName ||
      b.deviceId ||
      b.deviceIdentifier ||
      b.deviceUuid ||
      ""
    ).toLowerCase();
      return aKey.localeCompare(bKey);
    });
    return clone;
  }, [deviceStatuses]);

  const filteredSegments = useMemo(() => {
    const base = displaySegments;
    if (!rangeStartDt && !rangeEndDt) {
      return base;
    }
    const startMs = rangeStartDt ? rangeStartDt.getTime() : null;
    const endMs = rangeEndDt ? rangeEndDt.getTime() : null;
    return base.filter((segment) => {
      const raw = segment.start;
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

  const activeStatus = useMemo(() => {
    if (!deviceId) return null;
    return deviceStatusMap[deviceId] || null;
  }, [deviceId, deviceStatusMap]);

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
    const stream = selectedDeviceOption?.stream;
    if (stream?.hls_url) return stream.hls_url;
    const host = window.location.hostname;
    const port = 8888; // fallback
    return `http://${host}:${port}/${
      deviceId ? `uplink/${deviceId}` : "uplink"
    }/index.m3u8`;
  };

  const buildWhepUrlFromDevice = () => {
    const stream = selectedDeviceOption?.stream;
    if (stream?.whep_url) return stream.whep_url;
    const path = stream?.path ?? (deviceId ? `uplink/${deviceId}` : "");
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
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              カメラステータス
            </Typography>
            {sortedDeviceStatuses.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                ステータス情報がありません。
              </Typography>
            ) : (
              <Box sx={{ overflowX: "auto" }}>
                <Box
                  component="table"
                  sx={{
                    width: "100%",
                    borderCollapse: "collapse",
                    "& th, & td": {
                      borderBottom: "1px solid",
                      borderColor: "divider",
                      p: 1,
                      textAlign: "left",
                      verticalAlign: "top",
                    },
                    "& th": {
                      fontWeight: 600,
                      color: "text.secondary",
                    },
                  }}
                >
                  <Box component="thead">
                    <Box component="tr">
                      <Box component="th">デバイスID</Box>
                      <Box component="th">デバイス名</Box>
                      <Box component="th">ステータス</Box>
                      <Box component="th">工程</Box>
                      <Box component="th">ネットワーク</Box>
                      <Box component="th">最終更新</Box>
                    </Box>
                  </Box>
                  <Box component="tbody">
                    {sortedDeviceStatuses.map((status) => {
                      const statusLabel =
                        status.state ||
                        (status.isStreaming ? "配信中" : "停止");
                      const statusColor = status.isStreaming
                        ? "success.main"
                        : status.state
                        ? "text.primary"
                        : "text.secondary";
                      const processLabel = status.processCode
                        ? status.processName
                          ? `${status.processCode} (${status.processName})`
                          : status.processCode
                        : "未登録";
                      return (
                        <Box
                          component="tr"
                          key={
                            status.deviceId ||
                            status.deviceUuid ||
                            status.deviceName
                          }
                          sx={{ "&:last-of-type td": { borderBottom: "none" } }}
                        >
                          <Box component="td">
                            <Typography variant="body2">
                              {status.deviceId ||
                                status.deviceIdentifier ||
                                "-"}
                            </Typography>
                            {status.deviceUuid && (
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                display="block"
                              >
                                {status.deviceUuid}
                              </Typography>
                            )}
                          </Box>
                          <Box component="td">{status.deviceName || "-"}</Box>
                          <Box component="td">
                            <Typography
                              variant="body2"
                              sx={{
                                color: statusColor,
                                fontWeight: status.isStreaming
                                  ? 600
                                  : undefined,
                              }}
                            >
                              {statusLabel}
                            </Typography>
                          </Box>
                          <Box component="td">{processLabel}</Box>
                          <Box component="td">
                            {status.networkQuality || "-"}
                            {typeof status.batteryLevel === "number" && (
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                display="block"
                              >
                                バッテリー: {status.batteryLevel}%
                              </Typography>
                            )}
                          </Box>
                          <Box component="td">
                            {formatTimestamp(status.lastSeenAt)}
                          </Box>
                        </Box>
                      );
                    })}
                  </Box>
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
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
                  {deviceOptions.map((option) => {
                    const info = deviceProcessMap[option.deviceId];
                    const label =
                      option.status?.deviceName || option.deviceId || "-";
                    const streaming =
                      option.status?.isStreaming || Boolean(option.stream);
                    return (
                      <MenuItem key={option.deviceId} value={option.deviceId}>
                        <Box sx={{ display: "flex", flexDirection: "column" }}>
                          <Typography variant="body2" component="span">
                            {label}
                          </Typography>
                          <Typography
                            variant="caption"
                            color={
                              streaming ? "success.main" : "text.disabled"
                            }
                            component="span"
                          >
                            {streaming ? "配信中" : "停止中"}
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
                {activeStatus && (
                  <>
                    <Typography
                      variant="caption"
                      color={
                        activeStatus.isStreaming
                          ? "success.main"
                          : "text.secondary"
                      }
                      display="block"
                    >
                      現在:{" "}
                      {activeStatus.state ||
                        (activeStatus.isStreaming ? "配信中" : "停止")}
                    </Typography>
                    {activeStatus.networkQuality && (
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        display="block"
                      >
                        ネットワーク: {activeStatus.networkQuality}
                      </Typography>
                    )}
                    {activeStatus.lastSeenAt && (
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        display="block"
                      >
                        最終更新: {formatTimestamp(activeStatus.lastSeenAt)}
                      </Typography>
                    )}
                  </>
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
            {activeRecordingMeta && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2">
                  選択中デバイス:{" "}
                  {activeRecordingMeta.device_name ||
                    activeRecordingMeta.device_id}
                </Typography>
                {activeRecordingMeta.device_last_state && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    display="block"
                  >
                    状態: {activeRecordingMeta.device_last_state}
                  </Typography>
                )}
                {activeRecordingMeta.device_last_seen_at && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    display="block"
                  >
                    最終通信:{" "}
                    {formatTimestamp(activeRecordingMeta.device_last_seen_at)}
                  </Typography>
                )}
                {activeRecordingMeta.latest_start && (
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    display="block"
                  >
                    最新録画:{" "}
                    {formatTimestamp(activeRecordingMeta.latest_start)}
                  </Typography>
                )}
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
                    const status = deviceStatusMap[item.device_id];
                    const statusLabel = status
                      ? status.state || (status.isStreaming ? "配信中" : "停止")
                      : null;
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
                        {item.device_name && (
                          <Typography
                            variant="caption"
                            sx={{ display: "block" }}
                            color="text.secondary"
                          >
                            デバイス名: {item.device_name}
                          </Typography>
                        )}
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
                        {statusLabel && (
                          <Typography
                            variant="caption"
                            sx={{ display: "block" }}
                            color={
                              status?.isStreaming
                                ? "success.main"
                                : "text.secondary"
                            }
                          >
                            現在: {statusLabel}
                          </Typography>
                        )}
                        {item.device_last_state && !statusLabel && (
                          <Typography
                            variant="caption"
                            sx={{ display: "block" }}
                            color="text.secondary"
                          >
                            状態: {item.device_last_state}
                          </Typography>
                        )}
                        {status?.lastSeenAt && (
                          <Typography
                            variant="caption"
                            sx={{ display: "block" }}
                            color="text.secondary"
                          >
                            最終更新: {formatTimestamp(status.lastSeenAt)}
                          </Typography>
                        )}
                        {item.device_last_seen_at && (
                          <Typography
                            variant="caption"
                            sx={{ display: "block" }}
                            color="text.secondary"
                          >
                            最終通信:{" "}
                            {formatTimestamp(item.device_last_seen_at)}
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
                        {filteredSegments.map((segment) => {
                          const start = segment.start;
                          const formattedStart = formatTimestamp(start);
                          const dur = segment.duration;
                          let url = segment.url;
                          if (!url && segment.playback_url)
                            url = segment.playback_url;
                          if (!url && start) {
                            const loc = window.location;
                            const base = `${loc.protocol}//${loc.hostname}:9996`;
                            const params = new URLSearchParams();
                            params.set("path", recPath);
                            params.set("start", start);
                            if (dur != null)
                              params.set("duration", String(dur));
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
                          const thinklet = segment.thinklet;
                          const identifierText =
                            thinklet?.deviceId || thinklet?.deviceIdentifier;
                          const deviceLine = thinklet?.deviceName
                            ? `${thinklet.deviceName}${
                                identifierText ? ` (${identifierText})` : ""
                              }`
                            : identifierText ??
                              thinklet?.deviceUuid ??
                              null;
                          const session = thinklet?.session ?? null;
                          const lastEvent = thinklet?.lastEvent ?? null;
                          const sessionLabel = session?.id
                            ? session.id.length > 8
                              ? `${session.id.slice(0, 8)}…`
                              : session.id
                            : undefined;
                          const confidencePercent =
                            typeof lastEvent?.confidence === "number"
                              ? Math.round(lastEvent.confidence * 100)
                              : null;
                          const startConfidencePercent =
                            typeof session?.startConfidence === "number"
                              ? Math.round(session.startConfidence * 100)
                              : null;
                          const endConfidencePercent =
                            typeof session?.endConfidence === "number"
                              ? Math.round(session.endConfidence * 100)
                              : null;
                          const sessionEndLabel = session?.endedAt
                            ? ` ／ 終了 ${formatTimestamp(session.endedAt)}`
                            : session?.coverageEnd
                            ? ` ／ 推定終了 ${formatTimestamp(
                                session.coverageEnd
                              )}`
                            : "";
                          return (
                            <React.Fragment key={start}>
                              <Box>
                                <Typography
                                  variant="body2"
                                  title={start || undefined}
                                >
                                  {formattedStart}
                                </Typography>
                                {deviceLine && (
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    display="block"
                                  >
                                    デバイス: {deviceLine}
                                  </Typography>
                                )}
                                {thinklet?.deviceUuid &&
                                  thinklet.deviceUuid !== identifierText && (
                                    <Typography
                                      variant="caption"
                                      color="text.secondary"
                                      display="block"
                                    >
                                      UUID: {thinklet.deviceUuid}
                                    </Typography>
                                  )}
                                {thinklet?.deviceLastState && (
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    display="block"
                                  >
                                    最終状態: {thinklet.deviceLastState}
                                    {thinklet.deviceLastSeenAt
                                      ? `（${formatTimestamp(
                                          thinklet.deviceLastSeenAt
                                        )}）`
                                      : ""}
                                  </Typography>
                                )}
                                {session && (
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    display="block"
                                  >
                                    セッション: {sessionLabel ?? "-"}
                                    {session.status
                                      ? ` ／ ${session.status}`
                                      : ""}
                                  </Typography>
                                )}
                                {session?.startedAt && (
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    display="block"
                                  >
                                    開始 {formatTimestamp(session.startedAt)}
                                    {sessionEndLabel}
                                  </Typography>
                                )}
                                {session?.startCommand && (
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    display="block"
                                  >
                                    開始コマンド: {session.startCommand}
                                    {startConfidencePercent != null
                                      ? `（信頼度 ${startConfidencePercent}%）`
                                      : ""}
                                  </Typography>
                                )}
                                {session?.endCommand && (
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    display="block"
                                  >
                                    終了コマンド: {session.endCommand}
                                    {endConfidencePercent != null
                                      ? `（信頼度 ${endConfidencePercent}%）`
                                      : ""}
                                  </Typography>
                                )}
                                {lastEvent?.command && (
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    display="block"
                                  >
                                    最終コマンド: {lastEvent.command}
                                    {confidencePercent != null
                                      ? `（信頼度 ${confidencePercent}%）`
                                      : ""}
                                  </Typography>
                                )}
                                {lastEvent?.recognizedText && (
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    display="block"
                                  >
                                    音声: 「{lastEvent.recognizedText}」
                                  </Typography>
                                )}
                                {lastEvent?.timestamp && (
                                  <Typography
                                    variant="caption"
                                    color="text.secondary"
                                    display="block"
                                  >
                                    コマンド時刻:{" "}
                                    {formatTimestamp(lastEvent.timestamp)}
                                  </Typography>
                                )}
                              </Box>
                              <Typography
                                variant="body2"
                                sx={{ textAlign: "right" }}
                              >
                                {typeof dur === "number"
                                  ? `${dur.toFixed(1)}s`
                                  : "-"}
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
                                      setRecClipDuration(dur ?? null);
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
