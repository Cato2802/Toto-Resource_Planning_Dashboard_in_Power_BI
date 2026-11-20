"""Tạo dữ liệu mẫu (giả lập) từ một file cấu hình data_spec.json suy ra từ dashboard mẫu.

Chạy:  python3 make_sample_from_spec.py data_spec.json --out ./sample
Ra:    sample.xlsx (mỗi bảng một sheet) + mỗi bảng một file CSV.

Cấu hình (JSON):
{
  "name": "real_estate",              # tên file xlsx
  "seed": 42,
  "start": "2025-01-01", "end": "2026-10-31",
  "dims": [ {"name": "dim_property", "key": "Property_ID", "prefix": "P", "size": 42,
             "columns": {"Asset_Type": {"values": ["Commercial", "Residential"], "weights": [0.3, 0.7]},
                         "Units": {"int": [40, 400]}}} ],
  "facts": [
    {"name": "fact_lease", "grain": "transaction", "rows": 1000,
     "fks": {"dim_property": "pareto"},          # pareto: vài khóa rất nhiều dòng | uniform
     "season": {"1": 1.3, "6": 0.8},              # hệ số theo tháng (thiếu tháng nào = 1)
     "yoy": 0.10,                                 # số dòng năm sau so với năm trước (+10%)
     "columns": {"Monthly_Rent": {"lognormal": [9.5, 0.4], "round": 0}}},
    {"name": "fact_property_month", "grain": "monthly_snapshot", "entity": "dim_property",
     "columns": {"Occupancy": {"beta": [18, 2], "round": 3, "trend": 0.01}}}
  ]
}

Bộ sinh giá trị cho một cột (dùng được ở dim và fact):
  values + weights      chọn ngẫu nhiên theo tỷ trọng
  labels                danh sách cố định, dòng thứ i lấy phần tử thứ i (vòng lại nếu thiếu)
  int [lo, hi]          số nguyên đều
  uniform [lo, hi]      số thực đều
  normal [mean, sd]     phân phối chuẩn, kèm "min"/"max" để chặn
  lognormal [mu, sigma] lệch phải, hợp với tiền, doanh thu
  beta [a, b]           tỷ lệ 0..1, hợp với occupancy, % hoàn thành
  date [start, end]     ngày ngẫu nhiên
Ở bảng dim, values + weights được chia đúng tỷ lệ (không bốc ngẫu nhiên), để bảng nhỏ vẫn khớp tỷ trọng của mẫu.
Tùy chọn chung: "round" (số chữ số), "mult": "<cột khác cùng dòng>" hoặc "<dim>.<cột>" (nhân theo cột đó),
"trend": tăng trưởng mỗi năm của giá trị (chỉ ở fact), "season": true (nhân hệ số mùa vụ của fact).
"""
import argparse, json, os
import numpy as np, pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("spec")
ap.add_argument("--out", default="sample")
a = ap.parse_args()
S = json.load(open(a.spec, encoding="utf-8"))
rng = np.random.default_rng(S.get("seed", 42))

days = pd.date_range(S["start"], S["end"], freq="D")
months = pd.date_range(days.min().replace(day=1), days.max(), freq="MS")
yr0 = days.year.min()

def gen(g, n, exact=False):
    """Sinh n giá trị theo cấu hình g. exact=True: chia đúng tỷ lệ rồi xáo trộn (dùng cho bảng dim nhỏ)."""
    if "values" in g:
        w = np.array(g.get("weights", [1] * len(g["values"])), float); w = w / w.sum()
        if exact:
            k = np.floor(w * n).astype(int)
            k[np.argsort(-(w * n - k))[: n - k.sum()]] += 1
            return rng.permutation(np.repeat(np.array(g["values"], dtype=object), k))
        return rng.choice(g["values"], n, p=w)
    if "labels" in g:
        L = g["labels"]; return np.array([L[i % len(L)] for i in range(n)])
    if "int" in g:
        lo, hi = g["int"]; return rng.integers(lo, hi + 1, n)
    if "uniform" in g:
        lo, hi = g["uniform"]; v = rng.uniform(lo, hi, n)
    elif "normal" in g:
        m, s = g["normal"]; v = rng.normal(m, s, n)
    elif "lognormal" in g:
        m, s = g["lognormal"]; v = rng.lognormal(m, s, n)
    elif "beta" in g:
        x, y = g["beta"]; v = rng.beta(x, y, n)
    elif "date" in g:
        lo, hi = pd.to_datetime(g["date"]); return pd.to_datetime(rng.integers(lo.value // 10**9, hi.value // 10**9, n), unit="s").normalize()
    else:
        raise ValueError(f"Không hiểu cấu hình cột: {g}")
    if "min" in g or "max" in g:
        v = np.clip(v, g.get("min", -np.inf), g.get("max", np.inf))
    return v

def finish(df, cols, dims, season=None):
    """Áp mult, trend, season, round cho các cột số sau khi sinh."""
    for c, g in cols.items():
        v = df[c]
        if "mult" in g:
            m = g["mult"]
            if "." in m:
                dn, dc = m.split("."); d = dims[dn]
                v = v * df[d.attrs["key"]].map(d.set_index(d.attrs["key"])[dc]).to_numpy()
            else:
                v = v * df[m].to_numpy()
        if "trend" in g and "Date" in df:
            yrs = (pd.DatetimeIndex(df["Date"]).year - yr0) + (pd.DatetimeIndex(df["Date"]).month - 1) / 12
            v = v * np.power(1 + g["trend"], np.asarray(yrs, float))
        if g.get("season") and season and "Date" in df:
            v = v * pd.DatetimeIndex(df["Date"]).month.map(lambda mm: season.get(str(mm), 1.0)).to_numpy()
        if "round" in g:
            v = np.round(v.astype(float), g["round"])
            if g["round"] == 0: v = v.astype("int64")
        df[c] = v
    return df

tables = {}
# ---------- dim_date ----------
dim_date = pd.DataFrame({"Date": days})
dim_date["Year"] = days.year
dim_date["MonthNo"] = days.month
dim_date["MonthYear"] = days.strftime("%b %Y")
dim_date["YearMonth"] = days.year * 100 + days.month
dim_date["Quarter"] = "Q" + days.quarter.astype(str)
tables["dim_date"] = dim_date

# ---------- dims ----------
dims = {}
for d in S.get("dims", []):
    n = d["size"]
    df = pd.DataFrame({d["key"]: [f"{d.get('prefix', d['key'][0])}{i+1:0{max(3, len(str(n)))}d}" for i in range(n)]})
    for c, g in d.get("columns", {}).items():
        df[c] = gen(g, n, exact=True)
    df = finish(df, d.get("columns", {}), dims)
    df.attrs["key"] = d["key"]
    dims[d["name"]] = df
    tables[d["name"]] = df

# ---------- facts ----------
for f in S.get("facts", []):
    season = f.get("season", {})
    cols = f.get("columns", {})
    if f.get("grain", "transaction") == "transaction":
        n = f["rows"]
        dw = np.asarray(days.month.map(lambda mm: season.get(str(mm), 1.0)), float)
        dw = dw * np.power(1 + f.get("yoy", 0.0), np.asarray(days.year - yr0, float))
        df = pd.DataFrame({"Date": rng.choice(days, n, p=dw / dw.sum())})
        for dn, mode in f.get("fks", {}).items():
            d = dims[dn]; k = d.attrs["key"]
            w = rng.pareto(1.5, len(d)) + 1 if mode == "pareto" else np.ones(len(d))
            df[k] = rng.choice(d[k], n, p=w / w.sum())
    else:  # monthly_snapshot: mỗi thực thể × mỗi tháng một dòng
        d = dims[f["entity"]]; k = d.attrs["key"]
        df = pd.MultiIndex.from_product([months, d[k]], names=["Date", k]).to_frame(index=False)
        n = len(df)
    for c, g in cols.items():
        df[c] = gen(g, n)
    df = finish(df, cols, dims, season)
    df = df.sort_values("Date").reset_index(drop=True)
    if f.get("id"):
        df.insert(0, f["id"], [f"{f['id'][0]}{i+1:06d}" for i in range(len(df))])
    tables[f["name"]] = df

# ---------- ghi file ----------
os.makedirs(a.out, exist_ok=True)
xlsx = os.path.join(a.out, S.get("name", "sample") + ".xlsx")
with pd.ExcelWriter(xlsx, engine="openpyxl") as xw:
    for name, df in tables.items():
        df.to_excel(xw, sheet_name=name[:31], index=False)
        df.to_csv(os.path.join(a.out, name + ".csv"), index=False, encoding="utf-8-sig")

# ---------- tóm tắt để tự kiểm ----------
print("file:", xlsx)
for name, df in tables.items():
    print(f"{name:28s} {len(df):6d} dòng | {', '.join(df.columns[:8])}{' ...' if len(df.columns) > 8 else ''}")
for f in S.get("facts", []):
    df = tables[f["name"]]
    by = df.groupby(pd.DatetimeIndex(df["Date"]).year).size()
    print(f"{f['name']}: số dòng theo năm {by.to_dict()}")
    for dn in f.get("fks", {}):
        k = dims[dn].attrs["key"]; print(f"  khóa {k} khớp dim: {df[k].isin(dims[dn][k]).all()}")
