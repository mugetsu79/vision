import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Point = [number, number];

function pointLabel(point: Point) {
  return `${point[0]}, ${point[1]}`;
}

export function HomographyEditor({
  src,
  dst,
  refDistanceM,
  onChange,
}: {
  src: Point[];
  dst: Point[];
  refDistanceM: number;
  onChange: (value: { src: Point[]; dst: Point[]; refDistanceM: number }) => void;
}) {
  function updateRefDistance(value: string) {
    const parsed = Number(value);
    onChange({
      src,
      dst,
      refDistanceM: Number.isFinite(parsed) ? parsed : 0,
    });
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-[1.5rem] border border-[#243853] bg-[#09121c] p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
                Frame plane
              </p>
              <h3 className="mt-2 text-lg font-semibold text-[#f4f8ff]">Source points</h3>
            </div>
            <Button
              className="px-3 py-2"
              disabled={src.length >= 4}
              onClick={() =>
                onChange({
                  src: [...src, [src.length * 10, src.length * 10]],
                  dst,
                  refDistanceM,
                })
              }
            >
              Add source point
            </Button>
          </div>
          <div className="mt-4 flex min-h-48 items-center justify-center rounded-[1.3rem] border border-dashed border-[#37537e] bg-[radial-gradient(circle_at_top,_rgba(55,124,255,0.18),_transparent_35%),linear-gradient(180deg,#0d1725_0%,#08101a_100%)] text-center text-sm text-[#9eb2cf]">
            Frame snapshot placeholder
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {src.length === 0 ? (
              <p className="text-sm text-[#8ea4c7]">Add four source points from the camera frame.</p>
            ) : (
              src.map((point, index) => (
                <span
                  key={`src-${index}-${pointLabel(point)}`}
                  className="rounded-full border border-[#284066] bg-[#101a2a] px-3 py-1.5 text-xs font-medium text-[#d8e2f2]"
                >
                  S{index + 1}: {pointLabel(point)}
                </span>
              ))
            )}
          </div>
        </section>

        <section className="rounded-[1.5rem] border border-[#243853] bg-[#09121c] p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8ea4c7]">
                World plane
              </p>
              <h3 className="mt-2 text-lg font-semibold text-[#f4f8ff]">
                Destination points
              </h3>
            </div>
            <Button
              className="px-3 py-2"
              disabled={dst.length >= 4}
              onClick={() =>
                onChange({
                  src,
                  dst: [...dst, [dst.length * 5, dst.length * 5]],
                  refDistanceM,
                })
              }
            >
              Add destination point
            </Button>
          </div>
          <div className="mt-4 flex min-h-48 items-center justify-center rounded-[1.3rem] border border-dashed border-[#553a79] bg-[radial-gradient(circle_at_top,_rgba(128,92,255,0.2),_transparent_35%),linear-gradient(180deg,#111426_0%,#090d19_100%)] text-center text-sm text-[#b4abdc]">
            Ground-plane reference placeholder
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            {dst.length === 0 ? (
              <p className="text-sm text-[#8ea4c7]">
                Add four destination points that map to the real-world plane.
              </p>
            ) : (
              dst.map((point, index) => (
                <span
                  key={`dst-${index}-${pointLabel(point)}`}
                  className="rounded-full border border-[#3e3566] bg-[#131426] px-3 py-1.5 text-xs font-medium text-[#e7e2ff]"
                >
                  D{index + 1}: {pointLabel(point)}
                </span>
              ))
            )}
          </div>
        </section>
      </div>

      <div className="grid gap-4 rounded-[1.5rem] border border-white/8 bg-[#0b1320] p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
        <label className="grid gap-2 text-sm text-[#d8e2f2]">
          <span>Reference distance (m)</span>
          <Input
            aria-label="Reference distance (m)"
            min={0}
            step="0.1"
            type="number"
            value={refDistanceM}
            onChange={(event) => updateRefDistance(event.target.value)}
          />
        </label>
        <div className="flex gap-3">
          <Button
            className="bg-[#121b29] text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
            onClick={() => onChange({ src: [], dst, refDistanceM })}
          >
            Reset source
          </Button>
          <Button
            className="bg-[#121b29] text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
            onClick={() => onChange({ src, dst: [], refDistanceM })}
          >
            Reset destination
          </Button>
        </div>
      </div>

      <p className="rounded-[1.15rem] border border-[#284066] bg-[#0c1522] px-4 py-3 text-sm text-[#9eb2cf]">
        Source points: {src.length} / 4. Destination points: {dst.length} / 4. Argus
        uses this calibration to translate image motion into real-world distance and
        direction later in the pipeline.
      </p>
    </div>
  );
}
