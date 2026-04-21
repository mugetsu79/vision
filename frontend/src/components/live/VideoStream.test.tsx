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

    vi.stubGlobal(
      "RTCPeerConnection",
      class FakeRTCPeerConnection {
        addTransceiver() {}
        createOffer() {
          return { sdp: "v=0" };
        }
        setLocalDescription() {}
        setRemoteDescription() {}
        close() {}
      },
    );

    vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
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

    await waitFor(() => expect(HTMLMediaElement.prototype.play).toHaveBeenCalled());
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

    const image = await screen.findByRole("img", { name: /depot yard live stream/i });
    expect(image).toHaveAttribute(
      "src",
      expect.stringContaining("/video_feed/22222222-2222-2222-2222-222222222222"),
    );
    expect(image.getAttribute("src")).toContain("access_token=stream-token");
    expect(screen.getByText(/mjpeg forensic fallback/i)).toBeInTheDocument();
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
