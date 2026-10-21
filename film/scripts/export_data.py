"""Export the sim numbers the film uses into data.js (read-only from agrobo-web exports)."""
import json, pathlib
SRC = pathlib.Path('/mnt/project-files/agrobo-web/web/src/data')
OUT = pathlib.Path(__file__).resolve().parents[1] / 'data.js'

season = json.load(open(SRC / 'season_twin_s7.json'))
kpi = json.load(open(SRC / 'kpi_summary.json'))['metrics']
act = json.load(open(SRC / 'activity_per_ha.json'))
strat = json.load(open(SRC / 'strategy_report.json'))
s = season['series']
area = season['kpis']['area_ha']

spot, cum, last, buyers = [], [], None, {}
total = 0.0
for x in s:
    v = x.get('spot'); last = v if v else last; spot.append(round(last or 1.6, 3))
    total += x.get('revenue', 0); cum.append(total)
    for k, kg in (x.get('byBuyer') or {}).items(): buyers[k] = buyers.get(k, 0) + kg
m = lambda k: kpi[k]['twin']['mean']
rev_ha = act['twin']['yieldKgPerHa'] * act['twin']['revenuePerKg']
data = {
    'spot': spot,
    'cumRevenueNorm': [round(c / total, 4) for c in cum],
    'buyersTPerHa': {k: round(v / area / 1000, 1) for k, v in buyers.items()},
    'revenuePerHa': round(rev_ha),
    'secondsPerFruit': round(m('Picker seconds per fruit'), 1),
    'secondsPerFruitNoTwin': round(kpi['Picker seconds per fruit']['no_twin']['mean'], 1),
    'weedControl': round(m('Weed-control efficacy (%)'), 1),
    'herbicide': m('Herbicide used (L/ha)'),
    'gradeA': round(m('Grade A share (%)'), 1),
    'bruise': round(m('Bruise rate (%)'), 2),
    'pickToCool': round(m('Mean pick-to-cool (h)'), 2),
    'opex': round(m('Agrobo OpEx ($/kg)'), 3),
    'opexConv': round(m('Conventional OpEx ($/kg)'), 2),
    'uplift': round(m('Revenue uplift vs ungraded wholesale (%)')),
    'interventions': m('Human interventions'),
    'fruitPicked': season['kpis']['kpi_2_harvest_capture_and_quality']['fruit_picked'],
    'planted': season['kpis']['phases']['establish']['planted'],
    'seasonDays': season['kpis']['season_days'],
    'prepH': round(season['kpis']['phases']['prep']['duration_h'], 1),
    'prepM': round(season['kpis']['phases']['prep']['distance_m']),
    'candidates': strat['candidates'], 'combos': strat['viable_combinations'],
    'parcel': strat['chosen']['parcel'], 'top5': strat['top5'],
    'npv': season['kpis']['phases']['sourcing']['npv_usd'],
    'suitability': round(season['kpis']['phases']['sourcing']['suitability'], 2),
}
OUT.write_text('window.SIM = ' + json.dumps(data) + ';\n')
print({k: v for k, v in data.items() if k not in ('spot', 'cumRevenueNorm')})
