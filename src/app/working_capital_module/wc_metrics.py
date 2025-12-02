# calculators.py

def calc_dso(rec, revenue):
    return (rec / revenue) * 365 if revenue else None

def calc_dio(inv, cogs):
    return (inv / cogs) * 365 if cogs else None

def calc_dpo(payables, cogs):
    return (payables / cogs) * 365 if cogs else None

def calc_ccc(dso, dio, dpo):
    if None in (dso, dio, dpo):
        return None
    return dso + dio - dpo

def calc_nwc(rec, inv, pay):
    return rec + inv - pay

def calc_nwc_ratio(nwc, revenue):
    return nwc / revenue if revenue else None
