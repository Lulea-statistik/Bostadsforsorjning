#!/usr/bin/env python3
"""SCB annual rent measures for Lulea; exact published measure and unit codes."""
import json
import pathlib
import re
import urllib.request
from datetime import datetime, timezone

API = "https://api.scb.se/OV0104/v1/doris/sv/ssd/BO/BO0406/BO0406E/BO0406Tab01"
OUT = pathlib.Path("docs/data/rent.json")
MEASURES = {"mean":"Medelhyra i hyreslägenhet",
            "median":"Medianhyra i hyreslägenhet",
            "mean_margin":"± Felmarginal, medelhyra",
            "median_margin":"± Felmarginal, medianhyra"}
UNITS = {"annual":"Ah_kvm", "new_monthly":"Mh_kvm"}

def request(payload=None):
    headers = {"User-Agent":"Lulea-statistik-Bostadsforsorjning/1.0","Accept":"application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"]="application/json"
    with urllib.request.urlopen(urllib.request.Request(API,data=data,headers=headers),timeout=45) as response:
        return json.load(response)

def metadata_codes(meta):
    vars = {v["code"]:v for v in meta["variables"]}
    if set(vars) != {"Region","Hyresuppg","ContentsCode","Tid"}:
        raise ValueError(f"Unexpected SCB dimensions {list(vars)}")
    if "2580" not in vars["Region"]["values"]:
        raise ValueError("Lulea code missing")
    if not set(UNITS.values()).issubset(vars["Hyresuppg"]["values"]):
        raise ValueError("Expected rent units missing")
    codes = {}
    for name,label in MEASURES.items():
        candidates=[code for code,text in zip(vars["ContentsCode"]["values"],vars["ContentsCode"]["valueTexts"])
                    if text.strip().casefold()==label.casefold()]
        if len(candidates)!=1:raise ValueError(f"Missing or duplicate SCB measure {label}")
        codes[name]=candidates[0]
    years=vars["Tid"]["values"]
    if not years or any(not re.fullmatch(r"20\d{2}",y) for y in years):
        raise ValueError("Invalid SCB year categories")
    return codes,years

def number(raw):
    s=str(raw).strip().replace(" ","").replace("\u00a0","").replace(",",".")
    if s in (".","..","-",""):return None
    if not re.fullmatch(r"\d+(?:\.\d+)?",s):
        raise ValueError(f"Unknown rent statistic marker {raw!r}")
    return float(s) if "." in s else int(s)

def convert(meta,result):
    measures,years=metadata_codes(meta)
    dims=[c["code"] for c in result["columns"] if c.get("type") in ("d","t")]
    metrics=[c["code"] for c in result["columns"] if c.get("type")=="c"]
    if len(dims)!=3 or set(dims)!={"Region","Hyresuppg","Tid"}:
        raise ValueError(f"Unexpected dimensions {dims}")
    if len(metrics)!=4 or set(metrics)!=set(measures.values()):
        raise ValueError(f"Unexpected measures {metrics}")
    metric_by_code={code:name for name,code in measures.items()}
    result_by_key={}
    for item in result["data"]:
        keys=item["key"]
        if len(keys)!=3 or keys[dims.index("Region")]!="2580":
            raise ValueError(f"Unexpected municipality keys {keys}")
        unit=keys[dims.index("Hyresuppg")]
        year=keys[dims.index("Tid")]
        if unit not in UNITS.values() or year not in years:raise ValueError(f"Unexpected category {keys}")
        key=(int(year),unit)
        if key in result_by_key:raise ValueError(f"Duplicate rent key {key}")
        if len(item["values"])!=4:raise ValueError(f"Missing measure values {key}")
        values={metric_by_code[code]:number(raw) for code,raw in zip(metrics,item["values"])}
        for metric in ("mean","median"):
            value=values[metric]
            if value is not None and not 0<value<10000:raise ValueError(f"Implausible {key}: {metric}={value}")
        result_by_key[key]=values
    output=[]
    for year in map(int,years):
        row={"year":year}
        for name,unit in UNITS.items():
            if (year,unit) not in result_by_key:raise ValueError(f"Missing {name} observation for {year}")
            row[name]=result_by_key[(year,unit)]
        output.append(row)
    if not output or all(row["annual"]["mean"] is None for row in output):
        raise ValueError("No usable mean rent observations")
    return output

def main():
    meta=request()
    measures,years=metadata_codes(meta)
    query=[{"code":"Region","selection":{"filter":"item","values":["2580"]}},
           {"code":"Hyresuppg","selection":{"filter":"item","values":list(UNITS.values())}},
           {"code":"ContentsCode","selection":{"filter":"item","values":list(measures.values())}},
           {"code":"Tid","selection":{"filter":"item","values":years}}]
    rows=convert(meta,request({"query":query,"response":{"format":"json"}}))
    payload={"municipality":"2580","name":"Luleå","source_url":API,
             "updated_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "units":{"annual":"kr/m²/år","new_monthly":"kr/m²/månad"},
             "method_note":"Årshyran omfattar hela året. Ny månadshyra avser hyran efter årets hyresändring. Hyra inklusive värme och vatten, exklusive hushållsel och garage/bilplats. Specialbostäder och specialavtal ingår inte. SCB:s felmarginaler återges separat.",
             "data":rows}
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Saved {len(rows)} rent years, latest {rows[-1]['year']}")

if __name__=="__main__":
    main()
