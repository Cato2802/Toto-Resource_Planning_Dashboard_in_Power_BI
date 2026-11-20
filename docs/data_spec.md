# Data spec: Ressourcenplanung (dữ liệu giả lập)

Dựng lại dashboard mẫu "Ressourcenplanung" của Marlon Etzel (xem `design_ref_ressourcenplaner.md`).
Chủ đề giữ nguyên như mẫu: lập kế hoạch giờ làm cho nhân sự theo tuần. **Toàn bộ là dữ liệu giả**, tên người, dự án, khách hàng đều đặt mới; chỉ giữ tên thành phố Đức như mẫu.

## 1. Panel → measure → cột

| Panel trong mẫu | Số liệu hiển thị | Measure | Cột dữ liệu |
|---|---|---|---|
| Thanh tóm tắt "KW 47, aktuell" | 4 chip: frei / < 8 h frei / überplant / abwesend | `# Frei KW`, `# Unter8h KW`, `# Ueberplant KW`, `# Abwesend KW` | fact_capacity (Capacity_h, Absence_h), fact_allocation (Planned_h) |
| Header tuần | số KW, tổng giờ xếp mỗi tuần | `Planned h` | dim_date (Week_Start, KW, KW_Label) |
| Ma trận heatmap (người/team × tuần) | % tải từng ô, ô vắng, ô quá giờ | `Utilization %`, `Cell Status` | dim_person, dim_team, dim_date[Week_Start] |
| Cột tổng bên phải | giờ trống 4–16 tuần, cảnh báo đỏ "+x h überplant" | `Free h`, `Overplanned h` | như trên |
| Thẻ Auslastung | 65 %, "x von y h eingeplant", "Frei … · Überplant …" | `Utilization % 16KW`, `Planned h 16KW`, `Available h 16KW`, `Free h 16KW`, `Overplanned h 16KW` | |
| Thẻ Projekte | top 5 dự án theo giờ, thanh ngang | `Planned h 16KW`, `Project Rank 16KW` | dim_project |
| Thẻ Frei | người còn trống nhiều nhất, số giờ | `Free h 16KW`, `Person Free Rank 16KW` | dim_person |
| Nút PM / PO / Entwickler, Standort | lọc | slicer | dim_person[Role], dim_person[Standort] |
| Nút Personen ⇄ Team | đổi hàng của ma trận | `Selected View` + bảng `View_Selector` | dim_team |
| Nút KW ⇄ Monat | đổi cột của ma trận | field parameter hoặc slicer | dim_date[KW_Label] / dim_date[MonthYear] |
| Chế độ Bedarf | không dựng (cần JavaScript) | – | – |

## 2. Mô hình

| Bảng | Grain | Số dòng | Cột |
|---|---|---|---|
| dim_date | ngày, 06/07/2026 → 28/03/2027 (KW28/2026 → KW12/2027) | 266 | Date, Year, MonthNo, MonthYear, YearMonth, Quarter, Week_Start, ISO_Year, KW, YearWeek, KW_Label |
| dim_team | team | 4 | Team_ID, Team, Bereich |
| dim_person | người | 20 | Person_ID, Name, Role (3 PM, 3 PO, 14 Entwickler), Team_ID, Standort (Hamburg 8, Berlin 6, München 4, Köln 2), Weekly_Capacity (40/32/24 h) |
| dim_project | dự án | 10 | Project_ID, Project, Kunde, Priorität, Lead_Team, Start_Date, End_Date, Budget_h |
| fact_capacity | người × tuần (chụp theo tuần) | 760 | Date (thứ Hai đầu tuần), Person_ID, Capacity_h, Absence_h |
| fact_allocation | người × dự án × tuần | 1.070 | Alloc_ID, Date (thứ Hai), Person_ID, Project_ID, Planned_h |

Quan hệ (nhiều-một, lọc một chiều):
- fact_capacity[Date], fact_allocation[Date] → dim_date[Date]
- fact_capacity[Person_ID], fact_allocation[Person_ID] → dim_person[Person_ID]
- fact_allocation[Project_ID] → dim_project[Project_ID]
- dim_person[Team_ID] → dim_team[Team_ID]
- dim_project **không** nối tới dim_team (Lead_Team chỉ là cột chữ), để tránh hai đường lọc tới fact_allocation.

Mẫu không so với năm trước nên khoảng thời gian chỉ ~9 tháng: 19 tuần quá khứ + tuần hiện tại + 18 tuần kế hoạch.

## 3. Quy tắc sinh dữ liệu
- Tuần hiện tại cố định là **KW 47/2026** (bắt đầu 16/11/2026).
- Quá khứ: mỗi người được xếp khoảng 93 % giờ có mặt.
- Tương lai: kế hoạch thưa dần, mức tải bắt đầu khoảng 86 % rồi giảm 2,4 điểm mỗi tuần, nên trung bình 16 tuần khoảng 65 % như mẫu.
- Mỗi người có hệ số riêng (0,72–1,25), nên có người hay quá tải, có người hay trống.
- Vắng: khoảng 4 % số người × tuần vắng cả tuần.
- Tuần hiện tại được ép phân bố giống mẫu: 1 vắng, 3 quá giờ, phần còn lại chia thành nhóm "< 8 h frei" và "frei".
- Entwickler chủ yếu làm dự án do team mình phụ trách (85 % chỉ 1 dự án/tuần); PM và PO chia giờ cho 2–3 dự án.
- Giờ làm tròn tới bội số của 2.

Cách tạo: `make_sample_from_spec.py ressourcenplanung.spec.json` tạo các bảng dim, sau đó `build_weekly_facts.py` thêm cột tuần và 2 fact theo tuần (vì spec chỉ hỗ trợ dữ liệu theo ngày hoặc tháng).

## 4. So với mẫu

| Chỉ số | Mẫu | Dữ liệu sinh |
|---|---|---|
| Auslastung 16 KW | 65 % (một khung khác: 67 %) | 64,7 % (7.350 / 11.368 h) |
| Chip tuần hiện tại | 6 frei · 5 < 8 h · 3 überplant · 1 abwesend (15 người) | 7 frei · 9 < 8 h · 3 überplant · 1 abwesend (20 người) |
| Überplant 16 KW | 9 h | 20 h |
| Mức tải theo tuần | cao ở tuần gần, nhạt dần ở tuần xa | 84 % → 42 % trong 16 tuần |
| Top 5 dự án | 5 dự án, mỗi dự án vài trăm giờ | Kranich App 1.376 h, Iris Mobile 1.298 h, Orion Portal 988 h, Zenit Support 926 h, Delta Migration 916 h |
| Khóa và tuần | – | mọi khóa có trong dim; đủ 38/38 tuần; không trùng khóa người × tuần |
