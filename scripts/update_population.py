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

def total_code(variable):
    """Choose only an explicit SCB aggregate; never sum CKM subgroups."""
    values = variable["values"]
    labels = variable["valueTexts"]
    # SCB also labels a published aggregate "totalt, samtliga civilstånd".
    # Accept a total only when the label starts with the standalone word
    # "totalt" (or is one of the documented aggregate synonyms), and require
    # exactly one candidate. Never infer a total from subgroups.
    def is_total(label):
        normalized = " ".join(label.casefold().split())
        return (normalized == "totalt" or normalized.startswith("totalt,")
                or normalized.startswith("totalt ") or normalized in (
                    "total", "samtliga", "samtliga åldrar", "alla åldrar",
                    "alla civilstånd", "båda könen", "summa"))
    matches = [value for value, label in zip(values, labels)
               if is_total(label)]
    if len(matches) != 1:
        raise ValueError(
            f"No unique published total for required dimension {variable['code']}: "
            f"{list(zip(values, labels))[:15]}")
    return matches[0]

def fetch_table(name):
    url = BASE + name
    metadata = request(url)
    variables = metadata["variables"]
    selectors = []
    chosen_dimensions = {}
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
            # Leave optional dimensions to SCB's published aggregate/elimination.
            continue
        elif code in ("Civilstand", "Alder", "Kon"):
            vals = [total_code(v)]
        else:
            raise ValueError(f"Mandatory SCB dimension needs explicit handling: {code}")
        selectors.append({"code": code, "selection": {"filter": "item", "values": vals}})
        if code not in ("ContentsCode", "Tid"):
            chosen_dimensions[code] = vals[0]
    result = request(url, {"query": selectors, "response": {"format": "json"}})
    # PxWeb returns dimension metadata in columns. Position of Tid can change,
    # so never infer a year from four-digit keys: municipality 2580 is also four digits.
    columns = result.get("columns", [])
    # PxWeb JSON's columns also contain type=c (the statistical measure).
    # Measures live in row["values"], not in row["key"]. Only type=d
    # dimensions and type=t time columns correspond to keys.
    dimensions = [col for col in columns if col.get("type") in ("d", "t")]
    codes = [col["code"] for col in dimensions]
    measures = [col for col in columns if col.get("type") == "c"]
    if len(measures) != 1 or codes.count("Tid") != 1 or codes.count("Region") != 1:
        raise ValueError(f"Unexpected SCB column types in {name}: {columns}")
    if len(codes) != len(set(codes)) or any(
        code not in chosen_dimensions and code != "Tid" for code in codes
    ):
        raise ValueError(f"Unexpected extra dimensions in {name}: {codes}")
    time_index, region_index = codes.index("Tid"), codes.index("Region")
    output = {}
    for row in result["data"]:
        keys = row["key"]
        if len(keys) != len(codes) or any(
            keys[i] != chosen_dimensions[code]
            for i, code in enumerate(codes) if code != "Tid"
        ):
            raise ValueError(f"Unexpected SCB dimensions or municipality in {name}: {keys}")
        time_key = keys[time_index]
        if len(time_key) != 4 or not time_key.isdigit() or not 1900 <= int(time_key) <= 2100:
            raise ValueError(f"Invalid annual time key in {name}: {time_key}")
        year = int(time_key)
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
