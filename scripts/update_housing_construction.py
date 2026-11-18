#!/usr/bin/env python3
"""Download Lulea new-build starts and completions; retain partial latest year."""
import json
import pathlib
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

API = "https://api.scb.se/OV0104/v1/doris/sv/ssd/BO/BO0101/BO0101C/LagenhetNyKv26"
DEST = pathlib.Path("docs/data/housing_construction.json")
MEASURES = {"started": "påbörjade lägenheter i nybyggda hus",
            "completed": "färdigställda lägenheter i nybyggda hus"}
QUARTER = re.compile(r"^(\d{4})K([1-4])$")

def request(payload=None):
    headers = {"Accept": "application/json", "User-Agent": "Lulea-statistik-Bostadsforsorjning/1.0"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(API, data=data, headers=headers), timeout=45) as response:
        return json.load(response)

def detect_measure(label):
    normalized = " ".join(label.casefold().split())
    matches = [key for key, expected in MEASURES.items() if normalized == expected]
    if len(matches) != 1:
        raise ValueError(f"Unknown SCB housing measure: {label!r}")
    return matches[0]

def select_total(variable):
    matches = [code for code, name in zip(variable["values"], variable["valueTexts"])
               if " ".join(name.casefold().split()) in
               ("totalt", "total", "samtliga hustyper", "totalt, samtliga hustyper")]
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0 and variable.get("elimination") is True:
        return None
    raise ValueError(f"No unique all-building-types total: {list(zip(variable['values'], variable['valueTexts']))}")

def convert(metadata, result):
    variables = {v["code"]: v for v in metadata["variables"]}
    if not {"Region", "Tid", "ContentsCode"}.issubset(variables):
        raise ValueError("Missing required SCB metadata dimensions")
    measure_var = variables["ContentsCode"]
    chosen = {detect_measure(label): code for code, label in
              zip(measure_var["values"], measure_var["valueTexts"])
              if "lägenheter i nybyggda hus" in label.casefold()}
    if set(chosen) != set(MEASURES) or len(set(chosen.values())) != 2:
        raise ValueError(f"Expected two uniquely mapped SCB measures: {chosen}")
    columns = result["columns"]
    dimensions = [c for c in columns if c.get("type") in ("d", "t")]
    measures = [c for c in columns if c.get("type") == "c"]
    codes = [c["code"] for c in dimensions]
    if codes.count("Region") != 1 or codes.count("Tid") != 1 or len(codes) != len(set(codes)):
        raise ValueError(f"Unexpected SCB dimensions {codes}")
    if len(measures) != 2:
        raise ValueError(f"Expected two measure columns, found {measures}")
    selected = {code: metric for metric, code in chosen.items()}
    # PxWeb JSON measure columns use selected measure codes, with readable text.
    measure_keys = []
    for col in measures:
        code = col["code"]
        if code not in selected:
            raise ValueError(f"Unexpected SCB measure column: {col}")
        measure_keys.append(selected[code])
    if set(measure_keys) != set(MEASURES):
        raise ValueError("Missing/duplicate SCB measures")
    building_var = variables.get("Hustyp") or variables.get("hustyp")
    building_code = building_var["code"] if building_var else None
    selected_type = select_total(building_var) if building_var else None
    if any(c not in ("Region", "Tid", building_code) for c in codes):
        raise ValueError(f"Unexpected unaggregated housing dimension: {codes}")
    time_index = codes.index("Tid")
    region_index = codes.index("Region")
    totals = defaultdict(dict)
    for row in result["data"]:
        keys = row["key"]
        if len(keys) != len(codes) or keys[region_index] != "2580":
            raise ValueError(f"Wrong municipality/dimension keys: {keys}")
        if building_code in codes:
            if selected_type is None or keys[codes.index(building_code)] != selected_type:
                raise ValueError(f"Unexpected building type: {keys}")
        match = QUARTER.fullmatch(keys[time_index])
        if not match:
            raise ValueError(f"Not a calendar quarter: {keys[time_index]}")
        quarter = keys[time_index]
        if quarter in totals:
            raise ValueError(f"Duplicate quarter: {quarter}")
        values = row["values"]
        if len(values) != 2:
            raise ValueError(f"Missing quarterly measure for {quarter}")
        item = {}
        for metric, raw in zip(measure_keys, values):
            if not re.fullmatch(r"\d+", str(raw).strip()):
                raise ValueError(f"Missing/suppressed housing value {quarter}: {metric}={raw!r}")
            item[metric] = int(raw)
        totals[quarter] = item
    return totals

def aggregate(quarter_data):
    years = defaultdict(dict)
    for period, values in quarter_data.items():
        match = QUARTER.fullmatch(period)
        years[int(match.group(1))][int(match.group(2))] = values
    if not years:
        raise ValueError("No quarterly observations")
    latest = max(years)
    output = []
    for year in sorted(years):
        quarters = years[year]
        n = len(quarters)
        if set(quarters) != set(range(1, n + 1)):
            raise ValueError(f"Missing quarter in {year}: {sorted(quarters)}")
        if year < latest and n != 4:
            raise ValueError(f"Incomplete historic year {year}")
        output.append({"year": year, "started": sum(v["started"] for v in quarters.values()),
                       "completed": sum(v["completed"] for v in quarters.values()),
                       "partial": n != 4, "through_quarter": n})
    if not any(not item["partial"] for item in output):
        raise ValueError("No complete annual data")
    return output

def main():
    meta = request()
    variables = {v["code"]: v for v in meta["variables"]}
    required = ["Region", "ContentsCode", "Tid"]
    if any(c not in variables for c in required) or "2580" not in variables["Region"]["values"]:
        raise ValueError("Required region/measure/time metadata missing")
    measure_codes = {}
    for code, label in zip(variables["ContentsCode"]["values"], variables["ContentsCode"]["valueTexts"]):
        try:
            measure_codes[detect_measure(label)] = code
        except ValueError:
            continue
    if set(measure_codes) != set(MEASURES):
        raise ValueError(f"Both housing measures required: {measure_codes}")
    query = [
        {"code": "Region", "selection": {"filter": "item", "values": ["2580"]}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": [measure_codes[k] for k in ("started", "completed")]}},
        {"code": "Tid", "selection": {"filter": "item", "values": variables["Tid"]["values"]}},
    ]
    remaining = [v for v in meta["variables"] if v["code"] not in required]
    for variable in remaining:
        if variable["code"].casefold() == "hustyp":
            total = select_total(variable)
            if total is not None:
                query.append({"code": variable["code"], "selection": {"filter": "item", "values": [total]}})
        elif variable.get("elimination") is True:
            continue
        else:
            raise ValueError(f"Unrecognized mandatory SCB dimension: {variable['code']}")
    result = request({"query": query, "response": {"format": "json"}})
    data = aggregate(convert(meta, result))
    payload = {"municipality": "2580", "name": "Luleå", "source_url": API,
               "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "measure_labels": MEASURES,
               "method_note": "Fyra kvartal summeras för helår. Senaste året visas också när färre än fyra kvartal finns, märkt 'hittills i år'. Det värdet är inte jämförbart med helår och visas med streckad sista linjesträcka.",
               "data": data}
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(data)} years. Latest {data[-1]}")

if __name__ == "__main__":
    main()
