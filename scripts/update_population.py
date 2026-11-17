#!/usr/bin/env python3
"""Import verified annual Lulea population from SCB PxWeb v1, without dependencies."""
import json
import pathlib
import urllib.request
from datetime import datetime, timezone

BASE = "https://api.scb.se/OV0104/v1/doris/sv/ssd/BE/BE0101/BE0101A/"
TABLES = ["BefolkningNy", "BefolkningCKM"]
OUT = pathlib.Path("docs/data/population.json")

def request(url, payload=None):
    headers = {"User-Agent": "Lulea-statistik-Bostadsforsorjning/1.0", "Accept": "application/json"}
    if payload is not None:
        payload = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=payload, headers=headers), timeout=45) as response:
        return json.load(response)

def fetch_table(name):
    url = BASE + name
    metadata = request(url)
    variables = metadata["variables"]
    selectors = []
    for v in variables:
        code = v["code"]
        if code == "Region":
            assert "2580" in v["values"], "Lulea municipality code missing"
            vals = ["2580"]
        elif code == "Tid":
            vals = [x for x in v["values"] if x.isdigit() and len(x) == 4]
        elif code == "ContentsCode":
            matches = [key for key, label in zip(v["values"], v["valueTexts"]) if label.strip().casefold() == "folkmängd"]
            if len(matches) != 1:
                raise ValueError(f"Folkmangd measure ambiguous in {name}: {v['valueTexts']}")
            vals = matches
        elif v.get("elimination") is True:
            # PxWeb v1 automatically aggregates omitted eliminable dimensions.
            # Civilstand and Kon have no explicit total code; omitting them is
            # essential. For Alder SCB selects its supplied aggregate ("tot").
            # This avoids retrieving many disaggregated cells and, in CKM
            # tables, adding perturbations from separately protected cells.
            continue
        else:
            raise ValueError(f"Mandatory SCB dimension needs explicit handling: {code}")
        selectors.append({"code": code, "selection": {"filter": "item", "values": vals}})
    result = request(url, {"query": selectors, "response": {"format": "json"}})
    output = {}
    for row in result["data"]:
        # The returned keys are in requested dimension order.
        year = next((int(k) for k in row["key"] if len(k) == 4 and k.isdigit()), None)
        if year is None:
            raise ValueError(f"No year in returned data from {name}")
        value = row["values"][0]
        if not str(value).strip().isdigit():
            raise ValueError(f"Missing/invalid annual population {year}: {value}")
        number = int(value)
        if not 50000 <= number <= 120000:
            raise ValueError(f"Implausible municipality population {year}: {number}")
        if year in output:
            raise ValueError(f"Duplicate population year {year} in {name}")
        output[year] = number
    if len(output) < 1:
        raise ValueError(f"No data returned from {name}")
    return output

def main():
    old = fetch_table(TABLES[0])
    new = fetch_table(TABLES[1])
    merged = dict(old)
    for year, population in new.items():
        if year in merged and merged[year] != population:
            raise ValueError(f"Overlapping population mismatch for {year}")
        merged[year] = population
    years = sorted(merged)
    if years[-1] < 2025 or 2024 not in merged:
        raise ValueError(f"Expected annual 2024 and 2025 observations, got {years[-5:]}")
    rows = [
        {"year": year, "population": merged[year],
         "change": merged[year] - merged[year - 1] if year - 1 in merged else None}
        for year in years
    ]
    payload = {
        "municipality": "2580", "name": "Luleå",
        "reference": "Folkmängd den 31 december respektive år",
        "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_urls": [BASE + name for name in TABLES],
        "method_note": "Från 2025 använder SCB Cell Key Method (CKM). Små slumpmässiga skillnader mot andra publicerade del- och totalvärden kan förekomma.",
        "data": rows
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(rows)} annual observations, latest {years[-1]}: {merged[years[-1]]}")

if __name__ == "__main__":
    main()
