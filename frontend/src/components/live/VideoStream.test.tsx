import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { HlsClientConstructor } from "@/lib/hls";

vi.mock("@/lib/config", () => ({
  frontendConfig: {
    apiBaseUrl: "http://127.0.0.1:8000",
    oidcAuthority: "http://127.0.0.1:8080/realms/argus-dev",
    oidcClientId: "argus-frontend",
    oidcRedirectUri: "http://127.0.0.1:3000/auth/callback",
    oidcPostLogoutRedirectUri: "http://127.0.0.1:3000/signin",
  },
}));

const destroyMock = vi.fn();
const loadSourceMock = vi.fn();
const attachMediaMock = vi.fn();
const onMock = vi.fn();
const isSupportedMock = vi.fn();
const loadHlsClientMock = vi.fn<
  () => Promise<{ Hls: HlsClientConstructor; isSupported: () => boolean }>
>();
const observedElements = new Map<Element, IntersectionObserverCallback>();
let defaultIntersectionVisible = true;
let mediaPlayMock: ReturnType<typeof vi.fn<() => Promise<void>>>;

class FakeRTCPeerConnection {
  static instances: FakeRTCPeerConnection[] = [];
  static remoteDescriptionBlocker: Promise<void> | null = null;
  static remoteDescriptionCallCount = 0;

  connectionState = "connected";
  closed = false;
  iceConnectionState = "connected";
  onconnectionstatechange: (() => void) | null = null;
  oniceconnectionstatechange: (() => void) | null = null;
  ontrack: ((event: { streams: MediaStream[] }) => void) | null = null;

  constructor() {
    FakeRTCPeerConnection.instances.push(this);
  }

  static reset() {
    FakeRTCPeerConnection.instances = [];
    FakeRTCPeerConnection.remoteDescriptionBlocker = null;
    FakeRTCPeerConnection.remoteDescriptionCallCount = 0;
  }

  addTransceiver() {}

  createOffer() {
    return { sdp: "v=0" };
  }

  setLocalDescription() {}

  setRemoteDescription() {
    FakeRTCPeerConnection.remoteDescriptionCallCount += 1;
    return FakeRTCPeerConnection.remoteDescriptionBlocker ?? Promise.resolve();
  }

  close() {
    this.closed = true;
  }

  emitConnectionState(connectionState: string, iceConnectionState = connectionState) {
    this.connectionState = connectionState;
    this.iceConnectionState = iceConnectionState;
    this.onconnectionstatechange?.();
    this.oniceconnectionstatechange?.();
  }
}

vi.mock("@/lib/hls", () => ({
  loadHlsClient: () => loadHlsClientMock(),
}));

import { VideoStream } from "@/components/live/VideoStream";
import { useAuthStore } from "@/stores/auth-store";

const initialAuthState = useAuthStore.getState();

describe("VideoStream", () => {
  beforeEach(() => {
    useAuthStore.setState({
      status: "authenticated",
      accessToken: "stream-token",
      user: {
        sub: "viewer-1",
        email: "viewer@argus.local",
        role: "viewer",
        realm: "argus-dev",
        tenantId: "tenant-1",
        isSuperadmin: false,
      },
    });

    FakeRTCPeerConnection.reset();
    vi.stubGlobal("RTCPeerConnection", FakeRTCPeerConnection);

    mediaPlayMock = vi.fn<() => Promise<void>>().mockResolvedValue();
    vi.spyOn(HTMLMediaElement.prototype, "play").mockImplementation(mediaPlayMock);
    defaultIntersectionVisible = true;
    observedElements.clear();
    vi.stubGlobal(
      "IntersectionObserver",
      class FakeIntersectionObserver {
        private readonly callback: IntersectionObserverCallback;

        constructor(callback: IntersectionObserverCallback) {
          this.callback = callback;
        }

        observe(element: Element) {
          observedElements.set(element, this.callback);
          this.callback(
            [
              {
                boundingClientRect: element.getBoundingClientRect(),
                intersectionRatio: defaultIntersectionVisible ? 1 : 0,
                intersectionRect: element.getBoundingClientRect(),
                isIntersecting: defaultIntersectionVisible,
                rootBounds: null,
                target: element,
                time: 0,
              },
            ] as IntersectionObserverEntry[],
            this as unknown as IntersectionObserver,
          );
        }

        disconnect() {}
        unobserve() {}
        takeRecords() {
          return [];
        }
      },
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    FakeRTCPeerConnection.reset();
    useAuthStore.setState(initialAuthState, true);
    destroyMock.mockReset();
    loadSourceMock.mockReset();
    attachMediaMock.mockReset();
    onMock.mockReset();
    isSupportedMock.mockReset();
    loadHlsClientMock.mockReset();
  });

  test("falls back to HLS when WebRTC negotiation fails", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("upstream failed", { status: 502 }),
    );
    isSupportedMock.mockReturnValue(true);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return true;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    act(() => {
      render(
        <VideoStream
          cameraId="11111111-1111-1111-1111-111111111111"
          cameraName="North Gate"
          defaultProfile="720p10"
        />,
      );
    });

    await waitFor(() => expect(loadSourceMock).toHaveBeenCalledTimes(1));
    expect(loadSourceMock.mock.calls[0]?.[0]).toContain(
      "/api/v1/streams/11111111-1111-1111-1111-111111111111/hls.m3u8",
    );
    expect(loadSourceMock.mock.calls[0]?.[0]).toContain("access_token=stream-token");
    expect(await screen.findByText(/standby preview/i)).toBeInTheDocument();
    expect(FakeRTCPeerConnection.instances[0]?.closed).toBe(true);
  });

  test("retries WebRTC without HLS fallback when the stream path is not ready", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "WebRTC stream is not ready yet." }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      }),
    );
    isSupportedMock.mockReturnValue(true);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return true;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    await act(async () => {
      render(
        <VideoStream
          cameraId="12121212-1212-1212-1212-121212121212"
          cameraName="Stream Not Ready"
          defaultProfile="annotated"
        />,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(loadHlsClientMock).not.toHaveBeenCalled();
    expect(screen.getByText(/standby preview/i)).toBeInTheDocument();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(loadHlsClientMock).not.toHaveBeenCalled();
  });

  test("starts playback after the HLS manifest is parsed", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("upstream failed", { status: 502 }),
    );

    const hlsListeners = new Map<string, (event: string, data?: { fatal?: boolean }) => void>();
    onMock.mockImplementation((event: string, listener: (event: string) => void) => {
      hlsListeners.set(event, listener);
    });
    isSupportedMock.mockReturnValue(true);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return true;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    render(
      <VideoStream
        cameraId="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        cameraName="Warehouse North"
        defaultProfile="720p10"
      />,
    );

    await waitFor(() => expect(loadSourceMock).toHaveBeenCalledTimes(1));
    const manifestParsedListener = hlsListeners.get("manifestParsed");
    expect(manifestParsedListener).toBeDefined();

    act(() => {
      manifestParsedListener?.("manifestParsed");
    });

    await waitFor(() => expect(mediaPlayMock).toHaveBeenCalled());
    expect(screen.getByText(/ll-hls fallback/i)).toBeInTheDocument();
  });

  test("retries HLS startup when the manifest never becomes available", async () => {
    vi.useFakeTimers();
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("upstream failed", { status: 502 }),
    );

    isSupportedMock.mockReturnValue(true);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return true;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    await act(async () => {
      render(
        <VideoStream
          cameraId="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
          cameraName="Warehouse South"
          defaultProfile="720p10"
        />,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(loadSourceMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
    });

    expect(destroyMock).toHaveBeenCalled();

    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(loadSourceMock).toHaveBeenCalledTimes(2);
  });

  test("falls back to MJPEG after repeated HLS startup stalls", async () => {
    vi.useFakeTimers();
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("upstream failed", { status: 502 }),
    );

    isSupportedMock.mockReturnValue(true);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return true;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    await act(async () => {
      render(
        <VideoStream
          cameraId="cccccccc-cccc-cccc-cccc-cccccccccccc"
          cameraName="Warehouse West"
          defaultProfile="720p10"
        />,
      );
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(loadSourceMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(loadSourceMock).toHaveBeenCalledTimes(2);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(loadSourceMock).toHaveBeenCalledTimes(3);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4_000);
      await Promise.resolve();
      await Promise.resolve();
    });

    const image = screen.getByRole("img", { name: /warehouse west live stream/i });
    expect(image).toHaveAttribute(
      "src",
      expect.stringContaining("/video_feed/cccccccc-cccc-cccc-cccc-cccccccccccc"),
    );
    expect(screen.getByText(/mjpeg forensic fallback/i)).toBeInTheDocument();
  });

  test("falls back to MJPEG after repeated native HLS startup stalls", async () => {
    vi.useFakeTimers();
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("upstream failed", { status: 502 }),
    );
    vi.spyOn(HTMLMediaElement.prototype, "canPlayType").mockReturnValue("maybe");

    await act(async () => {
      render(
        <VideoStream
          cameraId="dddddddd-dddd-dddd-dddd-dddddddddddd"
          cameraName="Warehouse East"
          defaultProfile="720p10"
        />,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(loadHlsClientMock).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
      await Promise.resolve();
      await Promise.resolve();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5_000);
      await Promise.resolve();
      await Promise.resolve();
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(4_000);
      await Promise.resolve();
      await Promise.resolve();
    });

    const image = screen.getByRole("img", { name: /warehouse east live stream/i });
    expect(image).toHaveAttribute(
      "src",
      expect.stringContaining("/video_feed/dddddddd-dddd-dddd-dddd-dddddddddddd"),
    );
    expect(screen.getByText(/mjpeg forensic fallback/i)).toBeInTheDocument();
  });

  test("falls back to MJPEG when HLS is unavailable", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("upstream failed", { status: 502 }),
    );
    isSupportedMock.mockReturnValue(false);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return false;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    act(() => {
      render(
        <VideoStream
          cameraId="22222222-2222-2222-2222-222222222222"
          cameraName="Depot Yard"
          defaultProfile="540p5"
        />,
      );
    });

    expect(
      screen.getByRole("region", { name: /depot yard stream panel/i }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/depot yard live video/i)).toBeInTheDocument();
    const image = await screen.findByRole("img", { name: /depot yard live stream/i });
    expect(image).toHaveAttribute(
      "src",
      expect.stringContaining("/video_feed/22222222-2222-2222-2222-222222222222"),
    );
    expect(image.getAttribute("src")).toContain("access_token=stream-token");
    expect(screen.getByText(/mjpeg forensic fallback/i)).toBeInTheDocument();
  });

  test("restarts the stream session when the MJPEG fallback breaks at runtime", async () => {
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(new Response("upstream failed", { status: 502 }));
    isSupportedMock.mockReturnValue(false);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return false;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    render(
      <VideoStream
        cameraId="23232323-2323-2323-2323-232323232323"
        cameraName="Depot Recovery"
        defaultProfile="540p5"
      />,
    );

    const image = await screen.findByRole("img", { name: /depot recovery live stream/i });
    const initialFetchCount = fetchMock.mock.calls.length;

    act(() => {
      image.dispatchEvent(new Event("error"));
    });

    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(initialFetchCount), {
      timeout: 2_500,
    });
  });

  test("restarts from WebRTC after a fatal HLS runtime disconnect", async () => {
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(new Response("upstream failed", { status: 502 }));

    const hlsListeners = new Map<string, (event: string, data?: { fatal?: boolean }) => void>();
    onMock.mockImplementation(
      (event: string, listener: (event: string, data?: { fatal?: boolean }) => void) => {
        hlsListeners.set(event, listener);
      },
    );
    isSupportedMock.mockReturnValue(true);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return true;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    render(
      <VideoStream
        cameraId="34343434-3434-3434-3434-343434343434"
        cameraName="North Recovery"
        defaultProfile="720p10"
      />,
    );

    await waitFor(() => expect(loadSourceMock).toHaveBeenCalledTimes(1));
    act(() => {
      hlsListeners.get("manifestParsed")?.("manifestParsed");
    });
    const initialFetchCount = fetchMock.mock.calls.length;

    act(() => {
      hlsListeners.get("error")?.("error", { fatal: true });
    });

    await waitFor(() => expect(fetchMock.mock.calls.length).toBeGreaterThan(initialFetchCount), {
      timeout: 2_500,
    });
  });

  test("restarts the live tile after a short delay when the worker heartbeat recovers after going stale", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(new Response("upstream failed", { status: 502 }));
    isSupportedMock.mockReturnValue(false);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return false;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    const staleHeartbeatTs = new Date(Date.now() - 20_000).toISOString();
    const freshHeartbeatTs = new Date().toISOString();
    const { rerender } = await act(async () => {
      const view = render(
        <VideoStream
          cameraId="45454545-4545-4545-4545-454545454545"
          cameraName="Heartbeat Recovery"
          defaultProfile="720p10"
          heartbeatTs={staleHeartbeatTs}
        />,
      );
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
      return view;
    });

    expect(screen.getByRole("img", { name: /heartbeat recovery live stream/i })).toBeInTheDocument();
    const initialFetchCount = fetchMock.mock.calls.length;

    await act(async () => {
      rerender(
        <VideoStream
          cameraId="45454545-4545-4545-4545-454545454545"
          cameraName="Heartbeat Recovery"
          defaultProfile="720p10"
          heartbeatTs={freshHeartbeatTs}
        />,
      );
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchMock.mock.calls.length).toBe(initialFetchCount);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_500);
    });

    expect(fetchMock.mock.calls.length).toBe(initialFetchCount);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchMock.mock.calls.length).toBeGreaterThan(initialFetchCount);
  });

  test("restarts the live tile after a late-starting worker first reports a fresh heartbeat", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .spyOn(global, "fetch")
      .mockResolvedValue(new Response("upstream failed", { status: 502 }));
    isSupportedMock.mockReturnValue(false);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return false;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    const freshHeartbeatTs = new Date().toISOString();
    const { rerender } = await act(async () => {
      const view = render(
        <VideoStream
          cameraId="46464646-4646-4646-4646-464646464646"
          cameraName="Late Worker"
          defaultProfile="720p10"
          heartbeatTs={null}
        />,
      );
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
      return view;
    });

    expect(screen.getByRole("img", { name: /late worker live stream/i })).toBeInTheDocument();
    const initialFetchCount = fetchMock.mock.calls.length;

    await act(async () => {
      rerender(
        <VideoStream
          cameraId="46464646-4646-4646-4646-464646464646"
          cameraName="Late Worker"
          defaultProfile="720p10"
          heartbeatTs={freshHeartbeatTs}
        />,
      );
      await Promise.resolve();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchMock.mock.calls.length).toBe(initialFetchCount);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2_500);
    });

    expect(fetchMock.mock.calls.length).toBe(initialFetchCount);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchMock.mock.calls.length).toBeGreaterThan(initialFetchCount);
  });

  test("falls back to HLS when WebRTC negotiates but does not deliver a first frame", async () => {
    vi.useFakeTimers();
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ sdp_answer: "v=0" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    isSupportedMock.mockReturnValue(true);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return true;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    await act(async () => {
      render(
        <VideoStream
          cameraId="47474747-4747-4747-4747-474747474747"
          cameraName="Silent WebRTC"
          defaultProfile="720p10"
          heartbeatTs={new Date().toISOString()}
        />,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByText(/webrtc live/i)).toBeInTheDocument();
    expect(loadSourceMock).not.toHaveBeenCalled();

    await act(async () => {
      await vi.advanceTimersByTimeAsync(9_000);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(loadSourceMock).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/standby preview/i)).toBeInTheDocument();
  });

  test("does not restart an active WebRTC session just because telemetry heartbeat becomes stale", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ sdp_answer: "v=0" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const nearlyStaleHeartbeatTs = new Date(Date.now() - 10_000).toISOString();

    await act(async () => {
      render(
        <VideoStream
          cameraId="56565656-5656-5656-5656-565656565656"
          cameraName="Stable WebRTC"
          defaultProfile="720p10"
          heartbeatTs={nearlyStaleHeartbeatTs}
        />,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(6_500);
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  test("does not restart WebRTC on a transient disconnected pulse", async () => {
    vi.useFakeTimers();
    const fetchMock = vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ sdp_answer: "v=0" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    await act(async () => {
      render(
        <VideoStream
          cameraId="67676767-6767-6767-6767-676767676767"
          cameraName="Transient Disconnect"
          defaultProfile="720p10"
          heartbeatTs={new Date().toISOString()}
        />,
      );
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const peerConnection = FakeRTCPeerConnection.instances[0];
    expect(peerConnection).toBeDefined();

    act(() => {
      peerConnection?.emitConnectionState("disconnected");
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_500);
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);

    act(() => {
      peerConnection?.emitConnectionState("connected");
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  test("closes WebRTC peer when unmounted before negotiation finishes", async () => {
    let releaseRemoteDescription!: () => void;
    FakeRTCPeerConnection.remoteDescriptionBlocker = new Promise<void>((resolve) => {
      releaseRemoteDescription = resolve;
    });
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ sdp_answer: "v=0" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const view = render(
      <VideoStream
        cameraId="78787878-7878-7878-7878-787878787878"
        cameraName="Unmounting WebRTC"
        defaultProfile="native"
        heartbeatTs={new Date().toISOString()}
      />,
    );

    await waitFor(() => expect(FakeRTCPeerConnection.remoteDescriptionCallCount).toBe(1));
    const peerConnection = FakeRTCPeerConnection.instances[0];
    expect(peerConnection).toBeDefined();

    view.unmount();
    await act(async () => {
      releaseRemoteDescription();
      await Promise.resolve();
    });

    expect(peerConnection?.closed).toBe(true);
  });

  test("waits to start HLS fallback until the live tile is visible", async () => {
    defaultIntersectionVisible = false;
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("upstream failed", { status: 502 }),
    );
    isSupportedMock.mockReturnValue(true);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return true;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    const view = render(
      <VideoStream
        cameraId="33333333-3333-3333-3333-333333333333"
        cameraName="South Lot"
        defaultProfile="720p10"
      />,
    );

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(1));
    expect(loadSourceMock).not.toHaveBeenCalled();
    expect(screen.getByText(/standby preview/i)).toBeInTheDocument();

    const root = view.container.firstElementChild;
    if (!root) {
      throw new Error("Expected stream root.");
    }

    observedElements.get(root)?.(
      [
        {
          boundingClientRect: root.getBoundingClientRect(),
          intersectionRatio: 1,
          intersectionRect: root.getBoundingClientRect(),
          isIntersecting: true,
          rootBounds: null,
          target: root,
          time: 1,
        },
      ] as IntersectionObserverEntry[],
      {} as IntersectionObserver,
    );

    await waitFor(() => expect(loadSourceMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/standby preview/i)).toBeInTheDocument();
  });

  test("publishes a first-frame metric when the stream becomes visible", async () => {
    const metrics: Array<Record<string, unknown>> = [];
    const handleMetric = (event: Event) => {
      metrics.push((event as CustomEvent<Record<string, unknown>>).detail);
    };

    window.addEventListener("argus:stream-first-frame", handleMetric as EventListener);

    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response("upstream failed", { status: 502 }),
    );
    const hlsListeners = new Map<string, (event: string, data?: { fatal?: boolean }) => void>();
    onMock.mockImplementation((event: string, listener: (event: string) => void) => {
      hlsListeners.set(event, listener);
    });
    isSupportedMock.mockReturnValue(true);
    loadHlsClientMock.mockResolvedValue({
      isSupported: isSupportedMock,
      Hls: class FakeHls {
        static Events = { ERROR: "error", MANIFEST_PARSED: "manifestParsed" };
        static isSupported() {
          return true;
        }

        loadSource = loadSourceMock;
        attachMedia = attachMediaMock;
        on = onMock;
        destroy = destroyMock;
      },
    });

    const view = render(
      <VideoStream
        cameraId="44444444-4444-4444-4444-444444444444"
        cameraName="East Dock"
        defaultProfile="540p5"
      />,
    );

    await waitFor(() => expect(loadSourceMock).toHaveBeenCalledTimes(1));
    const manifestParsedListener = hlsListeners.get("manifestParsed");
    expect(manifestParsedListener).toBeDefined();

    act(() => {
      manifestParsedListener?.("manifestParsed");
    });

    const video = view.container.querySelector("video");
    if (!video) {
      throw new Error("Expected video element.");
    }

    act(() => {
      video.dispatchEvent(new Event("loadeddata"));
    });

    await waitFor(() => expect(metrics).toHaveLength(1));
    expect(metrics[0]).toMatchObject({
      cameraId: "44444444-4444-4444-4444-444444444444",
      defaultProfile: "540p5",
      transport: "hls",
    });
    expect(metrics[0]?.durationMs).toEqual(expect.any(Number));

    window.removeEventListener("argus:stream-first-frame", handleMetric as EventListener);
  });
});
