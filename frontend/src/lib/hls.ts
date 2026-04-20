export interface HlsErrorData {
  fatal?: boolean;
}

export interface HlsClientInstance {
  attachMedia(media: HTMLMediaElement): void;
  destroy(): void;
  loadSource(url: string): void;
  on(event: string, listener: (event: string, data: HlsErrorData) => void): void;
}

export interface HlsClientConstructor {
  new (config?: Record<string, unknown>): HlsClientInstance;
  Events: {
    ERROR: string;
    MANIFEST_PARSED: string;
  };
  isSupported(): boolean;
}

export async function loadHlsClient(): Promise<{
  Hls: HlsClientConstructor;
  isSupported: () => boolean;
}> {
  const module = (await import("hls.js")) as { default: HlsClientConstructor };

  return {
    Hls: module.default,
    isSupported: () => module.default.isSupported(),
  };
}
