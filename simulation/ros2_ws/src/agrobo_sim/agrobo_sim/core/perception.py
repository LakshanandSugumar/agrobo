"""Calibrated perception error models (stand-ins for the deployed edge networks).

Each model maps ground truth inside a sensor frame to detections, using recall /
precision / regression-noise curves of the shape we measure on real validation
sets. Swap the constants in config/perception.yaml for measured values from the
YOLO11-seg / ripeness-regressor validation runs; the ROS interface stays the same.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def _sigmoid(z):
    return 1.0 / (1.0 + math.exp(-z))


@dataclass
class WeedDetectorModel:
    """YOLO11n-seg crop/weed segmentation on UAV RGB+NIR (GSD ~4 mm at 8 m)."""
    max_recall: float = 0.96
    size50_cm: float = 1.2           # weed size at which recall is 50 % of max
    size_slope_cm: float = 0.5
    fp_per_plant: float = 0.006      # crop leaves mislabelled as weed, per plant per pass
    loc_sigma_m: float = 0.025       # RTK + orthomosaic registration error
    canopy_occlusion: float = 0.35   # recall loss under full canopy

    def detect(self, rng, weeds, plants, canopy_cover: float):
        dets = []
        occl = 1.0 - self.canopy_occlusion * canopy_cover
        for w in weeds:
            p = self.max_recall * _sigmoid((w.size_cm - self.size50_cm) / self.size_slope_cm) * occl
            if rng.random() < p:
                conf = float(np.clip(0.55 + 0.4 * p + rng.normal(0, 0.05), 0.3, 0.99))
                dets.append(("weed", w.wid, conf, w.x + rng.normal(0, self.loc_sigma_m),
                             w.y + rng.normal(0, self.loc_sigma_m), w.size_cm * rng.normal(1.0, 0.12)))
        for pl in plants:
            if pl.stage and rng.random() < self.fp_per_plant:
                dets.append(("weed", 0, float(rng.uniform(0.35, 0.7)), pl.x + rng.normal(0, 0.06),
                             pl.y + rng.normal(0, 0.06), float(rng.uniform(1, 4))))
        return dets


@dataclass
class RipenessModel:
    """Instance segmentation + ripeness regression (RGB-D, colour + NIR index)."""
    uav_visibility: float = 0.45     # fraction of non-occluded fruit visible from above
    ugv_visibility: float = 0.92     # side-looking stereo under canopy
    occluded_visibility: float = 0.15
    ripeness_sigma_uav: float = 0.07
    ripeness_sigma_ugv: float = 0.03
    min_ripeness_reported: float = 0.30

    def detect(self, rng, fruit, sensor: str):
        """fruit: iterable of (fid, pid, ripeness, height, occluded)."""
        uav = sensor.startswith("rgb_multispectral_uav")
        vis = self.uav_visibility if uav else self.ugv_visibility
        sig = self.ripeness_sigma_uav if uav else self.ripeness_sigma_ugv
        out = []
        for fid, pid, r, h, occ in fruit:
            if r < self.min_ripeness_reported:
                continue
            if uav:
                pv = self.occluded_visibility if occ else vis
            else:
                pv = 0.7 if occ else vis
            if rng.random() < pv:
                out.append((fid, pid, float(np.clip(r + rng.normal(0, sig), 0, 1.5)),
                            float(np.clip(0.6 + rng.normal(0, 0.1), 0.3, 0.99))))
        return out


@dataclass
class ChlorosisModel:
    """NDRE-based nitrogen-stress regressor from the multispectral payload."""
    sigma: float = 0.07
    threshold: float = 0.22

    def detect(self, rng, plants):
        out = []
        for p in plants:
            if not p.stage:
                continue
            est = float(np.clip(p.n_stress + rng.normal(0, self.sigma), 0, 1))
            if est >= self.threshold:
                out.append((p.pid, est, p.x, p.y))
        return out
