# aggregator.py

from .wc_metrics import calc_dso, calc_dio, calc_dpo, calc_ccc, calc_nwc, calc_nwc_ratio

def build_metrics(financials):
    metrics_by_year = {}

    for f in financials:
        dso = calc_dso(f.trade_receivables, f.revenue)
        dio = calc_dio(f.inventory, f.cogs)
        dpo = calc_dpo(f.trade_payables, f.cogs)
        ccc = calc_ccc(dso, dio, dpo)
        nwc = calc_nwc(f.trade_receivables, f.inventory, f.trade_payables)
        nwc_ratio = calc_nwc_ratio(nwc, f.revenue)

        metrics_by_year[f.year] = {
            "dso": dso,
            "dio": dio,
            "dpo": dpo,
            "ccc": ccc,
            "nwc": nwc,
            "nwc_ratio": nwc_ratio,
        }

    latest_year = max(metrics_by_year.keys())

    return {
        "all": metrics_by_year,
        "latest": metrics_by_year[latest_year],
        "latest_year": latest_year
    }
