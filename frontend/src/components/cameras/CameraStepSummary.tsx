export function CameraStepSummary({
  data,
}: {
  data: {
    name: string;
    siteName: string;
    processingMode: string;
    activeClasses: string[];
    trackerType: string;
    blurFaces: boolean;
    blurPlates: boolean;
    browserDeliveryProfile: string;
    frameSkip: number;
    fpsCap: number;
    rtspUrlMasked: string;
    boundarySummary: string;
  };
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {[
        {
          label: "Class scope",
          value:
            data.activeClasses.length > 0
              ? data.activeClasses.join(", ")
              : "All primary model classes",
        },
        { label: "Camera", value: data.name },
        { label: "Site", value: data.siteName },
        { label: "Processing", value: data.processingMode },
        { label: "Tracker", value: data.trackerType },
        { label: "Browser delivery", value: data.browserDeliveryProfile },
        { label: "Frame cadence", value: `skip ${data.frameSkip}, cap ${data.fpsCap} FPS` },
        { label: "Count boundaries", value: data.boundarySummary },
        {
          label: "Privacy",
          value: `faces ${String(data.blurFaces)}, plates ${String(data.blurPlates)}`,
        },
        { label: "RTSP", value: data.rtspUrlMasked },
      ].map((item) => (
        <div
          key={item.label}
          className="rounded-[1.2rem] border border-white/8 bg-[#0c1522] px-4 py-3"
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8ea4c7]">
            {item.label}
          </p>
          <p className="mt-2 text-sm text-[#eef4ff]">{item.value}</p>
        </div>
      ))}
    </div>
  );
}
