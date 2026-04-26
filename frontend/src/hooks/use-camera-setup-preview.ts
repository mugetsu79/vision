import { useEffect, useState } from "react";

import { useQuery } from "@tanstack/react-query";

import { resolveAccessToken, toApiError } from "@/lib/api";
import { frontendConfig } from "@/lib/config";

type CameraSetupPreviewPayload = {
  camera_id: string;
  preview_url: string;
  frame_size: {
    width: number;
    height: number;
  };
  captured_at: string;
};

type CameraSetupPreviewQueryData = CameraSetupPreviewPayload & {
  preview_blob: Blob | null;
};

export type CameraSetupPreview = CameraSetupPreviewPayload & {
  preview_src: string | null;
};

export function useCameraSetupPreview(
  cameraId: string | null | undefined,
  enabled = true,
) {
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const query = useQuery<CameraSetupPreviewQueryData>({
    enabled: Boolean(cameraId) && enabled,
    queryKey: ["camera-setup-preview", cameraId ?? "none"],
    queryFn: async () => {
      const accessToken = await resolveAccessToken();
      const authHeaders = accessToken
        ? {
            Authorization: `Bearer ${accessToken}`,
          }
        : undefined;

      const metadataResponse = await fetch(
        `${frontendConfig.apiBaseUrl}/api/v1/cameras/${cameraId}/setup-preview`,
        {
          headers: authHeaders,
        },
      );

      if (!metadataResponse.ok) {
        let detail: unknown;
        try {
          detail = await metadataResponse.json();
        } catch {
          detail = await metadataResponse.text();
        }
        throw toApiError(detail, "Failed to load camera setup preview.");
      }

      const payload = (await metadataResponse.json()) as CameraSetupPreviewPayload;
      if (typeof window === "undefined" || typeof window.URL.createObjectURL !== "function") {
        return {
          ...payload,
          preview_blob: null,
        };
      }

      try {
        const imageResponse = await fetch(
          new URL(payload.preview_url, frontendConfig.apiBaseUrl).toString(),
          {
            headers: authHeaders,
          },
        );
        if (!imageResponse.ok) {
          return {
            ...payload,
            preview_blob: null,
          };
        }
        return {
          ...payload,
          preview_blob: await imageResponse.blob(),
        };
      } catch {
        return {
          ...payload,
          preview_blob: null,
        };
      }
    },
    retry: false,
  });

  useEffect(() => {
    if (!query.data?.preview_blob || typeof window === "undefined") {
      setPreviewSrc(null);
      return;
    }

    const objectUrl = window.URL.createObjectURL(query.data.preview_blob);
    setPreviewSrc(objectUrl);
    return () => {
      window.URL.revokeObjectURL(objectUrl);
    };
  }, [query.data]);

  return {
    ...query,
    data: query.data
      ? ({
          camera_id: query.data.camera_id,
          preview_url: query.data.preview_url,
          frame_size: query.data.frame_size,
          captured_at: query.data.captured_at,
          preview_src: previewSrc,
        } satisfies CameraSetupPreview)
      : undefined,
  };
}
