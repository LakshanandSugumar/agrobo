import gz from "@/data/gazebo_row_follow.json";
import { C } from "@/lib/palette";

type Pt = number[];

/** Top-down plot of the Gazebo row-following test: planned lanes vs true robot path. */
export function PathPlot() {
  const way = gz.rtk.waypoints as Pt[];
  const rtk = gz.rtk.truth_sample as Pt[];
  const odom = gz.odom.truth_sample as Pt[];
  const all = [...way, ...rtk, ...odom];
  const xs = all.map((p) => p[0]), ys = all.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs) - 1, Math.max(...xs) + 1, Math.min(...ys) - 1, Math.max(...ys) + 1];
  const W = 720, H = Math.max(180, Math.round((W * (y1 - y0)) / (x1 - x0)));
  const sx = (x: number) => ((x - x0) / (x1 - x0)) * W;
  const sy = (y: number) => H - ((y - y0) / (y1 - y0)) * H;
  const path = (ps: Pt[]) => ps.map((p, i) => `${i ? "L" : "M"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join("");
  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full rounded-xl bg-[#f3f1ea]" role="img" aria-label="Robot paths in the Gazebo row-following test">
        <path d={path(way)} fill="none" stroke="#b9b5a8" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" opacity="0.5" />
        <path d={path(odom)} fill="none" stroke={C.conventional} strokeWidth="2" strokeDasharray="5 4" />
        <path d={path(rtk)} fill="none" stroke={C.agrobo} strokeWidth="2.5" />
      </svg>
      <figcaption className="mt-3 flex flex-wrap gap-5 text-[12px] text-ink-2">
        <span className="flex items-center gap-1.5"><span className="h-2.5 w-5 rounded-full bg-[#b9b5a8]/60" />Planned crop lanes</span>
        <span className="flex items-center gap-1.5"><span className="h-0.5 w-5" style={{ background: C.agrobo }} />RTK + IMU: {(gz.rtk.cross_track_rms_true_m * 100).toFixed(1)} cm RMS off-lane</span>
        <span className="flex items-center gap-1.5"><span className="h-0.5 w-5 border-t-2 border-dashed" style={{ borderColor: C.conventional }} />Wheel odometry only: {(gz.odom.cross_track_rms_true_m * 100).toFixed(0)} cm RMS</span>
      </figcaption>
    </figure>
  );
}
