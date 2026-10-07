"""Edge perception nodes. Each consumes /scout_uav/frames and publishes DetectionArray.

/perception_weed_classifier     -> /perception/weeds      (YOLO11n-seg crop/weed, TensorRT INT8 on Orin)
/perception_ripeness_estimator  -> /perception/fruit      (Mask R-CNN-lite + ripeness regressor head)
/perception_crop_health         -> /perception/chlorosis  (NDRE regression for N stress)

The noise models are in core/perception.py; replacing a model with a real network
means replacing `infer()` and keeping the topic contract.
"""
import numpy as np
from agrobo_interfaces.msg import Detection, DetectionArray, SensorFrame

from agrobo_sim.core.perception import ChlorosisModel, RipenessModel, WeedDetectorModel
from agrobo_sim.ros_util import RELIABLE, AgroboNode, spin


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class PerceptionBase(AgroboNode):
    out_topic = ""

    def __init__(self, name, seed):
        super().__init__(name)
        self.rng = np.random.default_rng(seed)
        self.pub = self.create_publisher(DetectionArray, self.out_topic, RELIABLE)
        self.create_subscription(SensorFrame, "/scout_uav/frames", self.on_frame, RELIABLE, callback_group=self.cbg)
        self.n_out = 0

    def on_frame(self, m):
        out = DetectionArray(source_robot=m.robot_id)
        out.header = m.header
        if not m.end_of_pass:
            out.detections = self.infer(m)
            self.n_out += len(out.detections)
        self.pub.publish(out)

    def infer(self, m):
        raise NotImplementedError


class WeedClassifier(PerceptionBase):
    out_topic = "/perception/weeds"

    def __init__(self):
        super().__init__("perception_weed_classifier", 101)
        self.model = WeedDetectorModel()

    def infer(self, m):
        weeds = [_Obj(wid=w.weed_id, x=w.x, y=w.y, size_cm=w.size_cm) for w in m.weeds]
        plants = [_Obj(stage=p.stage, x=p.x, y=p.y) for p in m.plants]
        canopy = float(np.mean([min(1.0, p.biomass_g / 900.0) for p in m.plants])) if m.plants else 0.0
        return [Detection(target_id=t, class_name=c, confidence=cf, x=x, y=y, value=v)
                for c, t, cf, x, y, v in self.model.detect(self.rng, weeds, plants, canopy)]


class RipenessEstimator(PerceptionBase):
    out_topic = "/perception/fruit"

    def __init__(self):
        super().__init__("perception_ripeness_estimator", 202)
        self.model = RipenessModel()

    def infer(self, m):
        pos = {p.plant_id: (p.x, p.y) for p in m.plants}
        fr = [(f.fruit_id, f.plant_id, f.ripeness, f.height_m, f.occluded) for f in m.fruit]
        out = []
        for fid, pid, r, conf in self.model.detect(self.rng, fr, m.sensor):
            x, y = pos.get(pid, (0.0, 0.0))
            # class_name carries the plant anchor ("fruit:<plant_id>") for twin association
            d =Detection(target_id=fid, class_name=f"fruit:{pid}", confidence=conf, x=x, y=y, value=r)
            out.append(d)
        return out


class CropHealth(PerceptionBase):
    out_topic = "/perception/chlorosis"

    def __init__(self):
        super().__init__("perception_crop_health", 303)
        self.model = ChlorosisModel()

    def infer(self, m):
        plants = [_Obj(pid=p.plant_id, stage=p.stage, n_stress=p.nitrogen_stress, x=p.x, y=p.y) for p in m.plants]
        return [Detection(target_id=pid, class_name="chlorosis", confidence=0.8, x=x, y=y, value=est)
                for pid, est, x, y in self.model.detect(self.rng, plants)]


def main_weeds(args=None):
    spin(WeedClassifier, args)


def main_ripeness(args=None):
    spin(RipenessEstimator, args)


def main_health(args=None):
    spin(CropHealth, args)
