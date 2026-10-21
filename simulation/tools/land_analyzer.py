#!/usr/bin/env python3
"""Real-parcel land analyzer: any US address or lat/lon -> crop ranking + 5-yr NPV.

Feeds the prototype's Phase 1 scorer (core/strategy.py) with live public data
instead of synthetic parcels:
  geocode     US Census geocoder               geocoding.geo.census.gov
  soil        USDA NRCS Soil Data Access       sdmdataaccess.sc.egov.usda.gov
  slope       USGS 3DEP elevation (EPQS)       epqs.nationalmap.gov
  season      Open-Meteo ERA5 archive          archive-api.open-meteo.com
Water, distance to buyers, cell coverage, land price and area are not in a
free national API, so they come from flags (or listing/due-diligence data) and
are marked "assumed" in the report.

  python3 tools/land_analyzer.py --address "13450 Turner Island Rd, Dos Palos, CA" \
      --area-ha 49.6 --land-usd-ha 54000 --well-m3-h 60 --km-to-dc 90
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import statistics
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ros2_ws/src/agrobo_sim"))
from agrobo_sim.core.strategy import CROPS, npv, suitability  # noqa: E402

UA = {"User-Agent": "agrobo-land-analyzer/0.1"}
DRAINAGE = {
    "excessively drained": 0.6, "somewhat excessively drained": 0.8, "well drained": 1.0,
    "moderately well drained": 0.9, "somewhat poorly drained": 0.6, "poorly drained": 0.3,
    "very poorly drained": 0.1,
}


def _get(url: str, data: bytes | None = None, timeout: int = 30):
    headers = dict(UA)
    if data is not None:
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=timeout) as r:
        return json.loads(r.read().decode())


def geocode(address: str) -> tuple[float, float, str]:
    q = urllib.parse.urlencode(dict(address=address, benchmark="Public_AR_Current", format="json"))
    m = _get(f"https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?{q}")["result"]["addressMatches"]
    if not m:
        raise SystemExit(f"Address not found by the Census geocoder: {address!r}. Pass --lat/--lon instead.")
    return m[0]["coordinates"]["y"], m[0]["coordinates"]["x"], m[0]["matchedAddress"]


def soil(lat: float, lon: float) -> dict:
    """Dominant major component of the SSURGO map unit under the point, surface horizon."""
    sql = f"""
        SELECT TOP 1 mu.muname, c.compname, c.comppct_r, c.slope_r, c.drainagecl,
               ch.ph1to1h2o_r, ch.om_r
        FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('point({lon} {lat})') AS m
        JOIN mapunit mu ON mu.mukey = m.mukey
        JOIN component c ON c.mukey = mu.mukey AND c.majcompflag = 'Yes'
        LEFT JOIN chorizon ch ON ch.cokey = c.cokey AND ch.hzdept_r = 0
        ORDER BY c.comppct_r DESC"""
    body = json.dumps(dict(query=sql, format="JSON+COLUMNNAME")).encode()
    rows = _get("https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest", body).get("Table", [])
    if len(rows) < 2:
        raise SystemExit("No SSURGO soil map unit at this point (water, urban, or outside survey).")
    rec = dict(zip(rows[0], rows[1]))
    f = lambda k: float(rec[k]) if rec.get(k) not in (None, "") else None  # noqa: E731
    return dict(map_unit=rec["muname"], component=rec["compname"], ph=f("ph1to1h2o_r"), om_pct=f("om_r"),
                slope_pct_ssurgo=f("slope_r"), drainage_class=rec.get("drainagecl"))


def slope_3dep(lat: float, lon: float, d_m: float = 50.0) -> float:
    """Central-difference slope (%) from USGS 3DEP elevations 50 m N/S/E/W of the point."""
    dlat = d_m / 111_320.0
    dlon = d_m / (111_320.0 * math.cos(math.radians(lat)))

    def z(y, x):
        q = urllib.parse.urlencode(dict(x=x, y=y, units="Meters", wkid=4326))
        return float(_get(f"https://epqs.nationalmap.gov/v1/json?{q}")["value"])

    dzdx = (z(lat, lon + dlon) - z(lat, lon - dlon)) / (2 * d_m)
    dzdy = (z(lat + dlat, lon) - z(lat - dlat, lon)) / (2 * d_m)
    return 100.0 * math.hypot(dzdx, dzdy)


def frost_free_days(lat: float, lon: float, years: int = 5) -> tuple[float, list[int]]:
    """Median frost-free season (last spring to first fall day with Tmin <= 0 C) over recent years."""
    end = dt.date.today().year - 1
    q = urllib.parse.urlencode(dict(latitude=lat, longitude=lon, start_date=f"{end - years + 1}-01-01",
                                    end_date=f"{end}-12-31", daily="temperature_2m_min", timezone="auto"))
    d = _get(f"https://archive-api.open-meteo.com/v1/archive?{q}", timeout=60)["daily"]
    per_year = []
    for y in range(end - years + 1, end + 1):
        days = [(dt.date.fromisoformat(t), v) for t, v in zip(d["time"], d["temperature_2m_min"])
                if t.startswith(str(y)) and v is not None]
        spring = [t for t, v in days if v <= 0 and t.month <= 6]
        fall = [t for t, v in days if v <= 0 and t.month >= 7]
        last = max(spring) if spring else dt.date(y, 1, 1)
        first = min(fall) if fall else dt.date(y, 12, 31)
        per_year.append((first - last).days)
    return float(statistics.median(per_year)), per_year


def analyze(a) -> dict:
    if a.address:
        lat, lon, matched = geocode(a.address)
    else:
        lat, lon, matched = a.lat, a.lon, None
    s = soil(lat, lon)
    slope = slope_3dep(lat, lon)
    ffd, ffd_years = frost_free_days(lat, lon)
    drain = DRAINAGE.get((s["drainage_class"] or "").lower(), 0.7)
    parcel = dict(
        parcel_id=a.name or matched or f"{lat:.5f},{lon:.5f}", lat=lat, lon=lon, area_ha=a.area_ha,
        ph=s["ph"] if s["ph"] is not None else 6.5, om_pct=s["om_pct"] if s["om_pct"] is not None else 1.5,
        n_ppm=28.0, slope_pct=slope, drainage=drain, well_m3_h=a.well_m3_h, ffd=ffd,
        km_to_dc=a.km_to_dc, land_usd_ha=a.land_usd_ha, lte_coverage=a.lte_coverage,
    )
    crops = []
    for crop in CROPS:
        score, parts = suitability(parcel, crop)
        value, _ = npv(parcel, crop)
        weakest = min(parts, key=parts.get)
        crops.append(dict(crop=crop, suitability=round(score, 3), npv_5yr_usd=round(value),
                          risk_adj_npv_usd=round(value * score),
                          weakest_factor=weakest, weakest_value=round(parts[weakest], 3),
                          factors={k: round(v, 3) for k, v in parts.items()}))
    # Suitability is treated as the odds the modeled yield is actually reached on this ground.
    crops.sort(key=lambda c: c["risk_adj_npv_usd"], reverse=True)
    return dict(
        location=dict(lat=lat, lon=lon, matched_address=matched),
        measured=dict(soil=s, slope_pct_3dep=round(slope, 2), frost_free_days_median=ffd,
                      frost_free_days_by_year=ffd_years, drainage_score=drain),
        assumed=dict(area_ha=a.area_ha, land_usd_ha=a.land_usd_ha, well_m3_h=a.well_m3_h,
                     km_to_dc=a.km_to_dc, lte_coverage=a.lte_coverage, n_ppm=28.0),
        crops=crops, recommendation=crops[0]["crop"],
    )


def report_md(r: dict) -> str:
    m, s = r["measured"], r["measured"]["soil"]
    loc = r["location"]["matched_address"] or f'{r["location"]["lat"]:.5f}, {r["location"]["lon"]:.5f}'
    lines = [f"## {loc}", "",
             f"**Recommended crop: {r['recommendation']}**", "",
             f"Soil: {s['map_unit']} ({s['component']}), pH {s['ph']}, organic matter {s['om_pct']}%, "
             f"{s['drainage_class']}. Slope {m['slope_pct_3dep']}% (3DEP), SSURGO slope {s['slope_pct_ssurgo']}%. "
             f"Frost-free season {m['frost_free_days_median']:.0f} days (median of {m['frost_free_days_by_year']}).", "",
             "| Crop | Suitability (0-1) | 5-yr NPV | Risk-adjusted NPV | Weakest factor |", "|---|---|---|---|---|"]
    for c in r["crops"]:
        lines.append(f"| {c['crop']} | {c['suitability']} | ${c['npv_5yr_usd']:,} | ${c['risk_adj_npv_usd']:,} | {c['weakest_factor']} ({c['weakest_value']}) |")
    a = r["assumed"]
    lines += ["", f"Assumed, not measured: area {a['area_ha']} ha, land ${a['land_usd_ha']:,.0f}/ha, water {a['well_m3_h']} m³/h, "
              f"{a['km_to_dc']} km to buyers, cell coverage {a['lte_coverage']}. "
              "NPV is the operating case from core/strategy.py; land bought outright is a separate asset on the balance sheet.", ""]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--address")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--name")
    p.add_argument("--area-ha", type=float, default=40.0)
    p.add_argument("--land-usd-ha", type=float, default=40000.0)
    p.add_argument("--well-m3-h", type=float, default=40.0, help="Reliable irrigation supply, m3/h")
    p.add_argument("--km-to-dc", type=float, default=80.0, help="Distance to packing hub / buyers, km")
    p.add_argument("--lte-coverage", type=float, default=0.8)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    if not a.address and (a.lat is None or a.lon is None):
        p.error("give --address or both --lat and --lon")
    r = analyze(a)
    print(json.dumps(r, indent=2) if a.json else report_md(r))


if __name__ == "__main__":
    main()
