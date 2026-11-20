"""Bước bổ sung sau make_sample_from_spec.py: tạo 2 fact theo TUẦN (spec chỉ hỗ trợ ngày/tháng).
- fact_capacity:   mỗi người × mỗi tuần (giờ năng lực, giờ vắng)
- fact_allocation: mỗi người × dự án × tuần (giờ đã xếp)
Đồng thời thêm cột tuần (KW) vào dim_date và thông tin thời gian vào dim_project.
Chạy: python3 build_weekly_facts.py out
"""
import sys, os
import numpy as np, pandas as pd

out = sys.argv[1]
name = "ressourcenplanung"
xlsx = os.path.join(out, name + ".xlsx")
T = pd.read_excel(xlsx, sheet_name=None)
rng = np.random.default_rng(11)

CUR = pd.Timestamp("2026-11-16")          # tuần hiện tại của dữ liệu mẫu: KW 47/2026
H = 16                                    # tầm nhìn 16 tuần

# ---------- dim_date: thêm cột tuần ----------
dd = T["dim_date"]; dd["Date"] = pd.to_datetime(dd["Date"])
iso = dd["Date"].dt.isocalendar()
dd["Week_Start"] = dd["Date"] - pd.to_timedelta(dd["Date"].dt.weekday, unit="D")
dd["ISO_Year"] = iso.year.astype(int)
dd["KW"] = iso.week.astype(int)
dd["YearWeek"] = dd["ISO_Year"] * 100 + dd["KW"]
dd["KW_Label"] = "KW " + dd["KW"].astype(str)
weeks = sorted(dd["Week_Start"].unique())
rel = {w: int((pd.Timestamp(w) - CUR).days // 7) for w in weeks}

# ---------- dim_project: đội phụ trách, tuần bắt đầu/kết thúc ----------
dp = T["dim_project"]; team = T["dim_team"]; per = T["dim_person"]
dp["Lead_Team"] = [team["Team"].iloc[i % 4] for i in range(len(dp))]
starts, ends = [], []
for i in range(len(dp)):
    if dp.loc[i, "Project"] == "Zenit Support":
        s, e = weeks[0], weeks[-1]
    else:
        si = int(rng.integers(0, 20)); ln = int(rng.integers(14, 32))
        s, e = weeks[si], weeks[min(len(weeks) - 1, si + ln)]
    starts.append(pd.Timestamp(s)); ends.append(pd.Timestamp(e) + pd.Timedelta(days=6))
dp["Start_Date"], dp["End_Date"] = starts, ends

def active(w):
    w = pd.Timestamp(w)
    return dp[(dp["Start_Date"] <= w) & (dp["End_Date"] >= w)]

# ---------- mức tải theo khoảng cách tới tuần hiện tại ----------
def load(r):
    if r < 0:
        return rng.normal(0.93, 0.07)            # quá khứ: gần đủ tải
    return max(0.12, 0.86 - 0.024 * r) * rng.normal(1, 0.06)   # tương lai: kế hoạch thưa dần

pm = dict(zip(per["Person_ID"], np.clip(rng.normal(1, 0.14, len(per)), 0.72, 1.25)))

# Tuần hiện tại: ép theo phân bố mục tiêu (frei / <8h frei / überplant / abwesend)
ids = list(rng.permutation(per["Person_ID"]))
cur_cat = {ids[0]: "abw"}
cur_cat.update({p: "over" for p in ids[1:4]})
cur_cat.update({p: "lt8" for p in ids[4:12]})
cur_cat.update({p: "frei" for p in ids[12:]})

cap_rows, alloc_rows = [], []
for w in weeks:
    r = rel[w]; act = active(w)
    for _, p in per.iterrows():
        pid, cap = p["Person_ID"], int(p["Weekly_Capacity"])
        if r == 0:
            absent = cur_cat[pid] == "abw"
        else:
            absent = rng.random() < 0.04
        absence = cap if absent else 0
        cap_rows.append((pd.Timestamp(w), pid, cap, absence))
        if absent:
            continue
        if r == 0:
            c = cur_cat[pid]
            f = {"over": rng.uniform(1.10, 1.22), "lt8": None, "frei": rng.uniform(0.45, 0.75)}[c]
            hours = cap * f if f else cap - rng.choice([0, 2, 4, 6])
        else:
            hours = cap * load(r) * pm[pid]
        hours = int(round(hours / 2) * 2)
        if hours <= 0 or act.empty:
            continue
        tname = team.set_index("Team_ID").loc[p["Team_ID"], "Team"]
        own = act[act["Lead_Team"] == tname]
        pool = own if (not own.empty and p["Role"] == "Entwickler") else act
        k = 1 if p["Role"] == "Entwickler" and rng.random() < 0.85 else min(len(pool), 2 if p["Role"] == "Entwickler" else int(rng.integers(2, 4)))
        k = max(1, min(k, len(pool)))
        # giữ dự án chính ổn định theo người (seed theo người) để heatmap trông thật
        order = pool.sample(frac=1, random_state=int(pid[1:])).Project_ID.tolist()
        chosen = order[:k]
        split = rng.dirichlet(np.ones(k) * 3) * hours
        split = np.round(split / 2) * 2
        split[0] += hours - split.sum()
        for prj, h in zip(chosen, split):
            if h > 0:
                alloc_rows.append((pd.Timestamp(w), pid, prj, int(h)))

fc = pd.DataFrame(cap_rows, columns=["Date", "Person_ID", "Capacity_h", "Absence_h"])
fa = pd.DataFrame(alloc_rows, columns=["Date", "Person_ID", "Project_ID", "Planned_h"])
fa.insert(0, "Alloc_ID", [f"A{i+1:05d}" for i in range(len(fa))])
dp["Budget_h"] = dp["Project_ID"].map(fa.groupby("Project_ID")["Planned_h"].sum()).fillna(0).mul(1.1).round(-1).astype(int)

T["dim_date"], T["dim_project"] = dd, dp
T["fact_capacity"], T["fact_allocation"] = fc, fa
with pd.ExcelWriter(xlsx, engine="openpyxl") as xw:
    for n, df in T.items():
        for c in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[c]):
                df[c] = pd.to_datetime(df[c]).dt.date
        df.to_excel(xw, sheet_name=n[:31], index=False)
        df.to_csv(os.path.join(out, n + ".csv"), index=False, encoding="utf-8-sig")
for n, df in T.items():
    print(f"{n:18s} {len(df):5d} dòng | {', '.join(df.columns)}")
