import React, { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';
import { Box, Button, Card, CardContent, FormControl, InputLabel, MenuItem, Select, TextField, Typography } from '@mui/material';
import axios from 'axios';

type StreamItem = {
  path: string;
  device_id: string;
  hls_url: string;
  state: string;
  readers: number;
  publishers: number;
};

export default function ThinkletViewer() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const whepResourceRef = useRef<string | null>(null);
  const [deviceId, setDeviceId] = useState('');
  const [streams, setStreams] = useState<StreamItem[]>([]);
  const [manualUrl, setManualUrl] = useState('');
  const [activeUrl, setActiveUrl] = useState('');
  const [hlsError, setHlsError] = useState('');
  const [mode, setMode] = useState<'hls' | 'whep'>('whep');
  const [whepStatus, setWhepStatus] = useState('');
  const [whepError, setWhepError] = useState('');

  const fetchStreams = async () => {
    try {
      const resp = await axios.get('/api/thinklet/streams');
      setStreams(resp.data.items || []);
    } catch (e) {
      console.error('Failed to fetch streams', e);
    }
  };

  useEffect(() => {
    fetchStreams();
    const t = setInterval(fetchStreams, 5000);
    return () => clearInterval(t);
  }, []);

  const play = (hlsUrl: string) => {
    setActiveUrl(hlsUrl);
    setHlsError('');
    const video = videoRef.current;
    if (!video) return;
    if (Hls.isSupported()) {
      // clean up previous instance
      if (hlsRef.current) {
        try { hlsRef.current.destroy(); } catch {}
        hlsRef.current = null;
      }
      const hls = new Hls({
        lowLatencyMode: true,
        enableWorker: true,
        startPosition: -1,
        // keep buffers tiny for live
        backBufferLength: 0,
        maxBufferLength: 1,
        maxBufferHole: 0.5,
        // chase live edge aggressively
        liveSyncDurationCount: 1,
        liveMaxLatencyDurationCount: 3,
        maxLiveSyncPlaybackRate: 1.5,
      });
      hlsRef.current = hls;
      hls.loadSource(hlsUrl);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
      });
      hls.on(Hls.Events.LEVEL_LOADED, () => {
        // try to stick to live edge during live playback
        try { (hls as any).seekToLivePosition?.(); } catch {}
      });
      hls.on(Hls.Events.ERROR, (_, data) => {
        const msg = `${data.type}: ${data.details}`;
        setHlsError(msg);
        if (data.fatal) {
          if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
            hls.startLoad();
          } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
            hls.recoverMediaError();
          } else {
            try { hls.destroy(); } catch {}
            hlsRef.current = null;
            // try quick reload at same URL
            setTimeout(() => play(hlsUrl), 500);
          }
        } else if (data.details === 'bufferSeekOverHole') {
          const v = videoRef.current;
          if (v && v.seekable && v.seekable.length > 0) {
            const end = v.seekable.end(v.seekable.length - 1);
            v.currentTime = Math.max(0, end - 0.5);
          } else {
            try { (hls as any).seekToLivePosition?.(); } catch {}
          }
        }
      });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = hlsUrl;
      video.play().catch((e) => { setHlsError(String(e)); });
    } else {
      alert('HLS is not supported in this browser');
    }
  };

  const buildUrlFromDevice = () => {
    const s = streams.find((x) => x.device_id === deviceId);
    if (s && s.hls_url) return s.hls_url;
    const host = window.location.hostname;
    const port = 8888; // fallback
    return `http://${host}:${port}/thinklet/${deviceId}/index.m3u8`;
  };

  const buildWhepUrlFromDevice = () => {
    const s = streams.find((x) => x.device_id === deviceId);
    const path = s ? s.path : `thinklet/${deviceId}`;
    const host = window.location.hostname;
    const port = 8889; // MediaMTX WebRTC HTTP port
    return `http://${host}:${port}/${path}/whep`;
  };

  const waitIceComplete = (pc: RTCPeerConnection) => new Promise<void>((resolve) => {
    if (pc.iceGatheringState === 'complete') return resolve();
    const check = () => {
      if (pc.iceGatheringState === 'complete') {
        pc.removeEventListener('icegatheringstatechange', check);
        resolve();
      }
    };
    pc.addEventListener('icegatheringstatechange', check);
  });

  const stopWhep = async () => {
    try {
      const pc = pcRef.current; pcRef.current = null;
      if (pc) pc.close();
      const res = whepResourceRef.current; whepResourceRef.current = null;
      if (res) {
        try { await fetch(res, { method: 'DELETE' }); } catch {}
      }
      setWhepStatus('stopped');
    } catch {}
  };

  const playWhep = async () => {
    setWhepError(''); setWhepStatus('connecting');
    // cleanup other modes
    if (hlsRef.current) { try { hlsRef.current.destroy(); } catch {}; hlsRef.current = null; }
    await stopWhep();
    const video = videoRef.current; if (!video) return;
    const pc = new RTCPeerConnection({ iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] });
    pcRef.current = pc;
    pc.addTransceiver('video', { direction: 'recvonly' });
    pc.addTransceiver('audio', { direction: 'recvonly' });
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
      await waitIceComplete(pc);
      const whepUrl = buildWhepUrlFromDevice();
      const resp = await fetch(whepUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/sdp', 'Accept': 'application/sdp' },
        body: pc.localDescription?.sdp || ''
      });
      if (!resp.ok) throw new Error(`WHEP POST failed: ${resp.status}`);
      const answerSdp = await resp.text();
      const loc = resp.headers.get('Location');
      if (loc) whepResourceRef.current = new URL(loc, whepUrl).toString();
      await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });
      setActiveUrl(whepUrl);
      setWhepStatus('connected');
    } catch (e: any) {
      setWhepError(String(e?.message || e));
      setWhepStatus('error');
      await stopWhep();
    }
  };

  const stopAll = async () => {
    if (hlsRef.current) { try { hlsRef.current.destroy(); } catch {}; hlsRef.current = null; }
    await stopWhep();
    setActiveUrl('');
  };

  const goFullscreen = () => {
    const el = videoRef.current;
    if (!el) return;
    const anyEl = el as any;
    (anyEl.requestFullscreen || anyEl.webkitRequestFullscreen || anyEl.msRequestFullscreen || anyEl.mozRequestFullScreen)?.call(el);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>THINKLET ライブ/録画 再生</Typography>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <FormControl sx={{ minWidth: 220 }}>
              <InputLabel id="stream-select-label">オンラインのTHINKLET</InputLabel>
              <Select
                labelId="stream-select-label"
                label="オンラインのTHINKLET"
                value={deviceId}
                onChange={(e) => setDeviceId(e.target.value)}
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
              <Select labelId="mode-label" label="再生方式" value={mode} onChange={(e) => setMode(e.target.value as any)}>
                <MenuItem value="whep">低遅延（WHEP）</MenuItem>
                <MenuItem value="hls">標準（HLS）</MenuItem>
              </Select>
            </FormControl>
            <Button
              variant="contained"
              disabled={!deviceId}
              onClick={() => mode === 'whep' ? playWhep() : play(buildUrlFromDevice())}
            >
              ライブ再生開始
            </Button>
            <Button variant="outlined" color="warning" onClick={stopAll}>停止</Button>
            <TextField size="small" label="HLS URL (手動)" sx={{ minWidth: 360 }}
              value={manualUrl} onChange={(e) => setManualUrl(e.target.value)} />
            <Button variant="outlined" onClick={() => play(manualUrl)}>
              手動URLで再生
            </Button>
          </Box>
        </CardContent>
      </Card>

      <Box sx={{ position: 'relative', width: '100%', maxWidth: 'min(100vw, 1280px)', aspectRatio: '16 / 9', background: '#000' }}>
        <video
          ref={videoRef}
          controls
          style={{ width: '100%', height: '100%', objectFit: 'contain', background: '#000' }}
          onDoubleClick={goFullscreen}
        />
      </Box>

      <Box sx={{ mt: 2 }}>
        <Typography variant="body2">現在のURL: {activeUrl || '-'}</Typography>
        {hlsError && <Typography variant="body2" color="error">再生エラー: {hlsError}</Typography>}
        {mode === 'whep' && (
          <>
            <Typography variant="body2">WHEP 状態: {whepStatus || '-'}</Typography>
            {whepError && <Typography variant="body2" color="error">WHEP エラー: {whepError}</Typography>}
          </>
        )}
        <Button size="small" sx={{ mt: 1 }} variant="outlined" onClick={goFullscreen}>全画面</Button>
      </Box>
    </Box>
  );
}
