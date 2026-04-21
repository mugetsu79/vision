import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { loadHlsClient } from "@/lib/hls";
import {
  acquireHlsPlaybackSlot,
  getStreamRuntimeHints,
  subscribeToHlsPlaybackBudget,
} from "@/lib/stream-playback";
import { buildApiUrl } from "@/lib/ws";
import { useAuthStore } from "@/stores/auth-store";

type StreamTransport = "connecting" | "standby" | "webrtc" | "hls" | "mjpeg" | "error";

const HLS_STARTUP_TIMEOUT_MS = 4_000;
const HLS_RETRY_DELAY_MS = 1_000;
const MAX_HLS_STARTUP_RETRIES = 3;

export function VideoStream({
  cameraId,
  cameraName,
  defaultProfile,
}: {
  cameraId: string;
  cameraName: string;
  defaultProfile: string;
}) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const tenantId = useAuthStore((state) => state.user?.tenantId ?? null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const firstFrameSentRef = useRef(false);
  const playbackStartedAtRef = useRef(0);
  const hlsRetryCountRef = useRef(0);
  const runtimeHints = useMemo(() => getStreamRuntimeHints(), []);
  const [transport, setTransport] = useState<StreamTransport>("connecting");
  const [webrtcFailed, setWebrtcFailed] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const [isPageVisible, setIsPageVisible] = useState(() => document.visibilityState !== "hidden");
  const [firstFrameMs, setFirstFrameMs] = useState<number | null>(null);
  const [hlsRetryToken, setHlsRetryToken] = useState(0);

  const hlsUrl = useMemo(
    () =>
      buildApiUrl(`/api/v1/streams/${cameraId}/hls.m3u8`, {
        access_token: accessToken,
        tenant_id: tenantId,
      }),
    [accessToken, cameraId, tenantId],
  );
  const mjpegUrl = useMemo(
    () =>
      buildApiUrl(`/video_feed/${cameraId}`, {
        access_token: accessToken,
        tenant_id: tenantId,
      }),
    [accessToken, cameraId, tenantId],
  );

  const fallbackReady = isVisible && isPageVisible;

  const emitFirstFrameMetric = useEffectEvent(
    (activeTransport: Extract<StreamTransport, "webrtc" | "hls" | "mjpeg">) => {
      if (firstFrameSentRef.current) {
        return;
      }

      firstFrameSentRef.current = true;
      const durationMs = Math.max(0, Math.round(performance.now() - playbackStartedAtRef.current));
      setFirstFrameMs(durationMs);
      window.dispatchEvent(
        new CustomEvent("argus:stream-first-frame", {
          detail: {
            cameraId,
            defaultProfile,
            durationMs,
            transport: activeTransport,
          },
        }),
      );
    },
  );

  useEffect(() => {
    const element = containerRef.current;
    if (!element || typeof IntersectionObserver === "undefined") {
      return;
    }

    const observer = new IntersectionObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }

      setIsVisible(entry.isIntersecting);
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsPageVisible(document.visibilityState !== "hidden");
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  useEffect(() => {
    firstFrameSentRef.current = false;
    playbackStartedAtRef.current = performance.now();
    hlsRetryCountRef.current = 0;
    setFirstFrameMs(null);
    setWebrtcFailed(false);
    setHlsRetryToken(0);

    if (!accessToken) {
      setTransport("error");
      return;
    }

    let disposed = false;
    let peerConnection: RTCPeerConnection | null = null;
    setTransport("connecting");

    const startStream = async () => {
      try {
        peerConnection = await startWebRtc({
          accessToken,
          cameraId,
          tenantId,
          videoElement: videoRef.current,
        });
        if (!disposed) {
          setTransport("webrtc");
        }
      } catch {
        peerConnection?.close();
        if (!disposed) {
          setWebrtcFailed(true);
        }
      }
    };

    void startStream();

    return () => {
      disposed = true;
      peerConnection?.close();
    };
  }, [accessToken, cameraId, tenantId]);

  useEffect(() => {
    if (!accessToken || !webrtcFailed) {
      return;
    }

    if (!fallbackReady) {
      setTransport("standby");
      return;
    }

    let disposed = false;
    let unsubscribe: (() => void) | null = null;
    let releaseSlot: (() => void) | null = null;
    let destroyHls: (() => void) | null = null;
    let retryTimer: number | null = null;

    const fallbackToMjpeg = () => {
      if (!disposed) {
        setTransport("mjpeg");
      }
    };

    const scheduleHlsRetry = () => {
      if (disposed) {
        return;
      }

      hlsRetryCountRef.current += 1;
      if (hlsRetryCountRef.current >= MAX_HLS_STARTUP_RETRIES) {
        fallbackToMjpeg();
        return;
      }

      setTransport("standby");
      retryTimer = window.setTimeout(() => {
        if (!disposed) {
          setHlsRetryToken((current) => current + 1);
        }
      }, HLS_RETRY_DELAY_MS);
    };

    const waitForSlot = () => {
      setTransport("standby");
      unsubscribe = subscribeToHlsPlaybackBudget(() => {
        unsubscribe?.();
        unsubscribe = null;
        if (!disposed) {
          setHlsRetryToken((current) => current + 1);
        }
      });
    };

    const startFallback = async () => {
      const videoElement = videoRef.current;
      if (!videoElement) {
        fallbackToMjpeg();
        return;
      }

      setTransport("standby");

      if (videoElement.canPlayType("application/vnd.apple.mpegurl")) {
        videoElement.src = hlsUrl;
        await videoElement.play().catch(() => undefined);
        if (!disposed) {
          setTransport("hls");
        }
        return;
      }

      const release = acquireHlsPlaybackSlot(runtimeHints.maxConcurrentHlsSessions);
      if (!release) {
        waitForSlot();
        return;
      }

      releaseSlot = release;

      try {
        destroyHls = await startHls({
          cameraName,
          hlsUrl,
          onFatalError: scheduleHlsRetry,
          onManifestParsed: () => {
            if (!disposed) {
              setTransport("hls");
            }
          },
          videoElement,
        });
      } catch {
        fallbackToMjpeg();
      }
    };

    void startFallback();

    return () => {
      disposed = true;
      unsubscribe?.();
      if (retryTimer !== null) {
        window.clearTimeout(retryTimer);
      }
      destroyHls?.();
      releaseSlot?.();
    };
  }, [
    accessToken,
    cameraName,
    fallbackReady,
    hlsRetryToken,
    hlsUrl,
    runtimeHints.maxConcurrentHlsSessions,
    webrtcFailed,
  ]);

  useEffect(() => {
    const videoElement = videoRef.current;
    if (!videoElement || (transport !== "webrtc" && transport !== "hls")) {
      return;
    }

    const handleLoadedData = () => {
      emitFirstFrameMetric(transport);
    };

    videoElement.addEventListener("loadeddata", handleLoadedData);
    return () => {
      videoElement.removeEventListener("loadeddata", handleLoadedData);
    };
  }, [emitFirstFrameMetric, transport]);

  useEffect(() => {
    const imageElement = imageRef.current;
    if (!imageElement || transport !== "mjpeg") {
      return;
    }

    const handleLoad = () => {
      emitFirstFrameMetric("mjpeg");
    };

    imageElement.addEventListener("load", handleLoad);
    return () => {
      imageElement.removeEventListener("load", handleLoad);
    };
  }, [emitFirstFrameMetric, transport]);

  return (
    <div
      ref={containerRef}
      className="absolute inset-0"
      data-first-frame-ms={firstFrameMs ?? undefined}
      data-transport={transport}
    >
      <video
        ref={videoRef}
        autoPlay
        className={transport === "mjpeg" ? "hidden" : "h-full w-full object-cover"}
        muted
        playsInline
      />

      {transport === "mjpeg" ? (
        <img
          ref={imageRef}
          alt={`${cameraName} live stream`}
          className="h-full w-full object-cover"
          src={mjpegUrl}
        />
      ) : null}

      <div className="pointer-events-none absolute left-3 top-3 flex flex-wrap gap-2">
        <Badge className="border-[#31538b] bg-[#081120]/80 text-[#eef4ff]">
          {defaultProfile}
        </Badge>
        <Badge className="border-[#31538b] bg-[#081120]/80 text-[#eef4ff]">
          {transportLabel(transport)}
        </Badge>
      </div>
    </div>
  );
}

async function startWebRtc({
  accessToken,
  cameraId,
  tenantId,
  videoElement,
}: {
  accessToken: string;
  cameraId: string;
  tenantId: string | null;
  videoElement: HTMLVideoElement | null;
}) {
  if (typeof RTCPeerConnection === "undefined") {
    throw new Error("WebRTC unavailable.");
  }

  const peerConnection = new RTCPeerConnection();
  peerConnection.addTransceiver("video", { direction: "recvonly" });
  peerConnection.ontrack = (event) => {
    if (!videoElement) {
      return;
    }
    videoElement.srcObject = event.streams[0];
    void videoElement.play().catch(() => undefined);
  };

  const offer = await peerConnection.createOffer();
  await peerConnection.setLocalDescription(offer);

  const response = await fetch(buildApiUrl(`/api/v1/streams/${cameraId}/offer`), {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
    },
    body: JSON.stringify({ sdp_offer: offer.sdp ?? "" }),
  });

  if (!response.ok) {
    throw new Error("Offer negotiation failed.");
  }

  const payload = (await response.json()) as { sdp_answer?: string };
  if (!payload.sdp_answer) {
    throw new Error("Missing SDP answer.");
  }

  await peerConnection.setRemoteDescription({
    type: "answer",
    sdp: payload.sdp_answer,
  });

  return peerConnection;
}

async function startHls({
  cameraName,
  hlsUrl,
  onFatalError,
  onManifestParsed,
  videoElement,
}: {
  cameraName: string;
  hlsUrl: string;
  onFatalError: () => void;
  onManifestParsed: () => void;
  videoElement: HTMLVideoElement | null;
}) {
  if (!videoElement) {
    throw new Error("Missing video element.");
  }

  const { Hls, isSupported } = await loadHlsClient();
  if (!isSupported()) {
    throw new Error(`LL-HLS unavailable for ${cameraName}.`);
  }

  const client = new Hls({ lowLatencyMode: true });
  let manifestParsed = false;
  const startupTimer = window.setTimeout(() => {
    if (manifestParsed) {
      return;
    }

    client.destroy();
    onFatalError();
  }, HLS_STARTUP_TIMEOUT_MS);
  client.attachMedia(videoElement);
  client.loadSource(hlsUrl);
  client.on(Hls.Events.MANIFEST_PARSED, () => {
    manifestParsed = true;
    window.clearTimeout(startupTimer);
    onManifestParsed();
    void videoElement.play().catch(() => undefined);
  });
  client.on(Hls.Events.ERROR, (_event, data) => {
    if (data.fatal) {
      window.clearTimeout(startupTimer);
      client.destroy();
      onFatalError();
    }
  });

  return () => {
    window.clearTimeout(startupTimer);
    client.destroy();
  };
}

function transportLabel(transport: StreamTransport): string {
  switch (transport) {
    case "standby":
      return "Standby preview";
    case "webrtc":
      return "WebRTC live";
    case "hls":
      return "LL-HLS fallback";
    case "mjpeg":
      return "MJPEG forensic fallback";
    case "error":
      return "Stream unavailable";
    default:
      return "Negotiating stream";
  }
}
