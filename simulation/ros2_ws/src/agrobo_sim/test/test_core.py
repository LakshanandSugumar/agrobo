"""Fast ROS-free checks of the core models (pytest)."""
import numpy as np

from agrobo_sim.core.agronomy import Field
from agrobo_sim.core.planning import LaneMetric, boustrophedon, tsp_tour
from agrobo_sim.core.strategy import evaluate
from agrobo_sim.core.twin import FieldLedger


def grown_field(days=90):
    f = Field()
    f.clear(); f.till(); f.deploy_irrigation()
    f.transplant([p.pid for p in f.plants])
    for _ in range(days):
        f.step_day()
    return f


def test_crop_sets_and_ripens_fruit():
    f = grown_field()
    assert len(f.f_state) > 10 * len(f.plants)
    assert ((f.f_ripe >= 0.75) & (f.f_state == 0)).any()


def test_laser_kill_needs_energy():
    f = grown_field(20)
    assert not f.kill_weed(10**9, 50.0)                      # unknown target
    killed = sum(f.kill_weed(x.wid, 200.0) for x in f.live_weeds()[:50])
    assert killed >= 45


def test_ledger_forecast_crosses_ripeness():
    L = FieldLedger()
    L.ingest_fruit(1, 1, 0.5)
    for d in range(30):
        L.on_day(d + 1, 14.0)
    assert L.forecast(L.fruit[1]) > 0.75
    assert [t.fid for t in L.harvest_orders()] == [1]


def test_tsp_beats_input_order():
    rng = np.random.default_rng(0)
    pts = [(float(rng.uniform(0, 24)), float(rng.choice([1.5, 3.0, 4.5]))) for _ in range(60)]
    m = LaneMetric(1.5, 24.0)
    _, length = tsp_tour(pts, (0.0, 0.0), m)
    naive = sum(m(a, b) for a, b in zip([(0.0, 0.0)] + pts, pts))
    assert length < 0.5 * naive


def test_boustrophedon_covers_width():
    xs, ys, length = boustrophedon(24.0, 15.0, 1.5)
    assert len(set(ys)) == 10 and length > 10 * 24


def test_strategy_picks_locked_crop():
    best, _ = evaluate(20, 1, "tomato")
    assert best["crop"] == "tomato" and best["score"] > 0.35
