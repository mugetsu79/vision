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
const STREAM_RECONNECT_BASE_DELAY_MS = 1_000;
const STREAM_RECONNECT_MAX_DELAY_MS = 5_000;
const WEBRTC_FIRST_FRAME_TIMEOUT_MS = 8_000;
const HEARTBEAT_STALE_AFTER_MS = 15_000;
const HEARTBEAT_RECOVERY_PROMOTION_DELAY_MS = 3_000;
const WEBRTC_DISCONNECT_GRACE_MS = 2_000;

let streamSessionCounter = 0;

class StreamNotReadyError extends Error {
  constructor() {
    super("WebRTC stream is not ready yet.");
    this.name = "StreamNotReadyError";
  }
}

export function VideoStream({
  cameraId,
  cameraName,
  defaultProfile,
  heartbeatTs = null,
}: {
  cameraId: string;
  cameraName: string;
  defaultProfile: string;
  heartbeatTs?: string | null;
}) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const tenantId = useAuthStore((state) => state.user?.tenantId ?? null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const firstFrameSentRef = useRef(false);
  const playbackStartedAtRef = useRef(0);
  const hlsRetryCountRef = useRef(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptRef = useRef(0);
  const heartbeatStatusRef = useRef<"unknown" | "fresh" | "stale">("unknown");
  const runtimeHints = useMemo(() => getStreamRuntimeHints(), []);
  const [transport, setTransport] = useState<StreamTransport>("connecting");
  const [webrtcFailed, setWebrtcFailed] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const [isPageVisible, setIsPageVisible] = useState(() => document.visibilityState !== "hidden");
  const [firstFrameMs, setFirstFrameMs] = useState<number | null>(null);
  const [hlsRetryToken, setHlsRetryToken] = useState(0);
  const [sessionToken, setSessionToken] = useState(() => nextStreamSessionToken());

  const clearReconnectTimer = useEffectEvent(() => {
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  });

  const restartSession = useEffectEvent(() => {
    clearReconnectTimer();
    firstFrameSentRef.current = false;
    playbackStartedAtRef.current = performance.now();
    hlsRetryCountRef.current = 0;
    setFirstFrameMs(null);
    setWebrtcFailed(false);
    setHlsRetryToken(0);
    setTransport("connecting");
    setSessionToken(nextStreamSessionToken());
  });

  const requestSessionRestart = useEffectEvent(
    (mode: "backoff" | "immediate" | "recovery" = "backoff") => {
    if (!accessToken) {
      setTransport("error");
      return;
    }

    if (mode === "immediate") {
      reconnectAttemptRef.current = 0;
      restartSession();
      return;
    }

    if (reconnectTimerRef.current !== null) {
      return;
    }

    if (mode === "recovery") {
      reconnectTimerRef.current = window.setTimeout(() => {
        reconnectTimerRef.current = null;
        reconnectAttemptRef.current = 0;
        restartSession();
      }, HEARTBEAT_RECOVERY_PROMOTION_DELAY_MS);
      return;
    }

    const delay = Math.min(
      STREAM_RECONNECT_BASE_DELAY_MS * (2 ** reconnectAttemptRef.current),
      STREAM_RECONNECT_MAX_DELAY_MS,
    );
    setTransport("standby");
    reconnectTimerRef.current = window.setTimeout(() => {
      reconnectTimerRef.current = null;
      reconnectAttemptRef.current += 1;
      restartSession();
    }, delay);
  });

  const hlsUrl = useMemo(
    () =>
      buildApiUrl(`/api/v1/streams/${cameraId}/hls.m3u8`, {
        access_token: accessToken,
        session_token: String(sessionToken),
        tenant_id: tenantId,
      }),
    [accessToken, cameraId, sessionToken, tenantId],
  );
  const mjpegUrl = useMemo(
    () =>
      buildApiUrl(`/video_feed/${cameraId}`, {
        access_token: accessToken,
        session_token: String(sessionToken),
        tenant_id: tenantId,
      }),
    [accessToken, cameraId, sessionToken, tenantId],
  );

  const fallbackReady = isVisible && isPageVisible;

  const emitFirstFrameMetric = useEffectEvent(
    (activeTransport: Extract<StreamTransport, "webrtc" | "hls" | "mjpeg">) => {
      if (firstFrameSentRef.current) {
        return;
      }

      clearReconnectTimer();
      reconnectAttemptRef.current = 0;
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
    clearReconnectTimer();
    reconnectAttemptRef.current = 0;
    heartbeatStatusRef.current = "unknown";

    return () => {
      clearReconnectTimer();
    };
  }, [accessToken, cameraId, tenantId]);

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
    let stopWebRtc: (() => void) | null = null;
    let firstFrameTimer: number | null = null;
    setTransport("connecting");

    const startStream = async () => {
      try {
        const stop = await startWebRtc({
          accessToken,
          cameraId,
          onConnectionLost: () => {
            if (!disposed) {
              requestSessionRestart();
            }
          },
          sessionToken,
          tenantId,
          videoElement: videoRef.current,
        });
        if (disposed) {
          stop();
          return;
        }

        stopWebRtc = stop;
        if (!disposed) {
          setTransport("webrtc");
          firstFrameTimer = window.setTimeout(() => {
            if (disposed || firstFrameSentRef.current) {
              return;
            }

            stopWebRtc?.();
            stopWebRtc = null;
            setWebrtcFailed(true);
          }, WEBRTC_FIRST_FRAME_TIMEOUT_MS);
        }
      } catch (error) {
        stopWebRtc?.();
        if (!disposed) {
          if (error instanceof StreamNotReadyError) {
            requestSessionRestart();
            return;
          }

          setWebrtcFailed(true);
        }
      }
    };

    void startStream();

    return () => {
      disposed = true;
      if (firstFrameTimer !== null) {
        window.clearTimeout(firstFrameTimer);
      }
      stopWebRtc?.();
    };
  }, [accessToken, cameraId, sessionToken, tenantId]);

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
        destroyHls = await startNativeHls({
          hlsUrl,
          onRuntimeFailure: () => {
            if (!disposed) {
              requestSessionRestart();
            }
          },
          onStartupFailure: scheduleHlsRetry,
          onLoadedData: () => {
            if (!disposed) {
              setTransport("hls");
            }
          },
          videoElement,
        });
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
          onRuntimeFailure: () => {
            if (!disposed) {
              requestSessionRestart();
            }
          },
          onStartupFailure: scheduleHlsRetry,
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

    const handleError = () => {
      requestSessionRestart();
    };

    imageElement.addEventListener("load", handleLoad);
    imageElement.addEventListener("error", handleError);
    return () => {
      imageElement.removeEventListener("load", handleLoad);
      imageElement.removeEventListener("error", handleError);
    };
  }, [emitFirstFrameMetric, transport]);

  useEffect(() => {
    if (!accessToken) {
      heartbeatStatusRef.current = "unknown";
      return;
    }

    let staleTimer: number | null = null;
    const parsedHeartbeatTs = heartbeatTs ? Date.parse(heartbeatTs) : Number.NaN;
    const nextStatus: "unknown" | "fresh" | "stale" = Number.isNaN(parsedHeartbeatTs)
      ? "unknown"
      : Date.now() - parsedHeartbeatTs <= HEARTBEAT_STALE_AFTER_MS
        ? "fresh"
        : "stale";
    const previousStatus = heartbeatStatusRef.current;
    heartbeatStatusRef.current = nextStatus;

    const recoveredFromUnavailable =
      (previousStatus === "unknown" || previousStatus === "stale") &&
      nextStatus === "fresh";

    if (recoveredFromUnavailable && transport !== "connecting" && transport !== "webrtc") {
      requestSessionRestart("recovery");
    }

    if (nextStatus === "fresh") {
      const remainingFreshMs = Math.max(
        0,
        HEARTBEAT_STALE_AFTER_MS - (Date.now() - parsedHeartbeatTs),
      );
      staleTimer = window.setTimeout(() => {
        if (heartbeatStatusRef.current !== "fresh") {
          return;
        }

        heartbeatStatusRef.current = "stale";
      }, remainingFreshMs + 50);
    }

    return () => {
      if (staleTimer !== null) {
        window.clearTimeout(staleTimer);
      }
    };
  }, [accessToken, heartbeatTs, transport]);

  return (
    <div
      ref={containerRef}
      aria-label={`${cameraName} stream panel`}
      className="absolute inset-0"
      data-first-frame-ms={firstFrameMs ?? undefined}
      data-transport={transport}
      role="region"
    >
      <video
        ref={videoRef}
        aria-label={`${cameraName} live video`}
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
  onConnectionLost,
  sessionToken,
  tenantId,
  videoElement,
}: {
  accessToken: string;
  cameraId: string;
  onConnectionLost: () => void;
  sessionToken: number;
  tenantId: string | null;
  videoElement: HTMLVideoElement | null;
}) {
  if (typeof RTCPeerConnection === "undefined") {
    throw new Error("WebRTC unavailable.");
  }

  const peerConnection = new RTCPeerConnection();
  let disconnectTimer: number | null = null;

  const clearDisconnectTimer = () => {
    if (disconnectTimer !== null) {
      window.clearTimeout(disconnectTimer);
      disconnectTimer = null;
    }
  };

  const scheduleConnectionLoss = () => {
    if (disconnectTimer !== null) {
      return;
    }

    disconnectTimer = window.setTimeout(() => {
      disconnectTimer = null;
      onConnectionLost();
    }, WEBRTC_DISCONNECT_GRACE_MS);
  };

  const stop = () => {
    clearDisconnectTimer();
    if (videoElement?.srcObject) {
      videoElement.srcObject = null;
    }
    peerConnection.close();
  };

  peerConnection.addTransceiver("video", { direction: "recvonly" });
  peerConnection.ontrack = (event) => {
    if (!videoElement) {
      return;
    }
    videoElement.srcObject = event.streams[0];
    void videoElement.play().catch(() => undefined);
  };
  const handleConnectionLoss = () => {
    const healthyIceStates = new Set(["connected", "completed"]);
    if (
      peerConnection.connectionState === "connected" ||
      healthyIceStates.has(peerConnection.iceConnectionState)
    ) {
      clearDisconnectTimer();
      return;
    }

    const closedConnectionStates = new Set(["closed", "disconnected", "failed"]);
    if (
      closedConnectionStates.has(peerConnection.connectionState) ||
      closedConnectionStates.has(peerConnection.iceConnectionState)
    ) {
      scheduleConnectionLoss();
    }
  };
  peerConnection.onconnectionstatechange = handleConnectionLoss;
  peerConnection.oniceconnectionstatechange = handleConnectionLoss;

  try {
    const offer = await peerConnection.createOffer();
    await peerConnection.setLocalDescription(offer);

    const response = await fetch(
      buildApiUrl(`/api/v1/streams/${cameraId}/offer`, {
        session_token: String(sessionToken),
      }),
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
          ...(tenantId ? { "X-Tenant-ID": tenantId } : {}),
        },
        body: JSON.stringify({ sdp_offer: offer.sdp ?? "" }),
      },
    );

    if (response.status === 404) {
      throw new StreamNotReadyError();
    }

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

  } catch (error) {
    stop();
    throw error;
  }

  return stop;
}

async function startHls({
  cameraName,
  hlsUrl,
  onRuntimeFailure,
  onStartupFailure,
  onManifestParsed,
  videoElement,
}: {
  cameraName: string;
  hlsUrl: string;
  onRuntimeFailure: () => void;
  onStartupFailure: () => void;
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
    onStartupFailure();
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
      if (manifestParsed) {
        onRuntimeFailure();
        return;
      }

      onStartupFailure();
    }
  });

  return () => {
    window.clearTimeout(startupTimer);
    client.destroy();
  };
}

async function startNativeHls({
  hlsUrl,
  onRuntimeFailure,
  onStartupFailure,
  onLoadedData,
  videoElement,
}: {
  hlsUrl: string;
  onRuntimeFailure: () => void;
  onStartupFailure: () => void;
  onLoadedData: () => void;
  videoElement: HTMLVideoElement;
}) {
  let disposed = false;
  let startupComplete = false;

  const cleanup = () => {
    videoElement.removeEventListener("loadeddata", handleLoadedData);
    videoElement.removeEventListener("error", handleError);
    window.clearTimeout(startupTimer);
  };

  const failStartup = () => {
    if (disposed) {
      return;
    }

    disposed = true;
    cleanup();
    videoElement.removeAttribute("src");
    onStartupFailure();
  };

  const failRuntime = () => {
    if (disposed) {
      return;
    }

    disposed = true;
    cleanup();
    videoElement.removeAttribute("src");
    onRuntimeFailure();
  };

  const handleLoadedData = () => {
    if (disposed || startupComplete) {
      return;
    }

    startupComplete = true;
    window.clearTimeout(startupTimer);
    onLoadedData();
  };

  const handleError = () => {
    if (startupComplete) {
      failRuntime();
      return;
    }

    failStartup();
  };

  const startupTimer = window.setTimeout(() => {
    failStartup();
  }, HLS_STARTUP_TIMEOUT_MS);

  videoElement.addEventListener("loadeddata", handleLoadedData);
  videoElement.addEventListener("error", handleError);
  videoElement.src = hlsUrl;
  await videoElement.play().catch(() => undefined);

  return () => {
    disposed = true;
    cleanup();
    videoElement.removeAttribute("src");
  };
}

function nextStreamSessionToken(): number {
  streamSessionCounter += 1;
  return streamSessionCounter;
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
