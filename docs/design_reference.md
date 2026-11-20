# Design reference: Ressourcenplanung (Marlon Etzel)

## 1. Nguồn và kỹ thuật
- Tác giả: Marlon Etzel, bài "Agentic Reporting pt. 4" trên LinkedIn
- Link: https://lnkd.in/p/gYxzAxMW → linkedin.com/posts/marlon-etzel_fabricapp-ugcPost-7525549006727438336-hPVP
- Nội dung: công cụ lập kế hoạch nguồn lực, xem số giờ đã xếp cho từng người theo từng tuần (KW), chỗ còn trống, ai đang bị xếp quá giờ. Bấm một nút để chuyển sang xem theo team.
- Kỹ thuật: **Custom Visual của Power BI viết bằng TypeScript** (pbiviz), chạy trong Power BI Service; tác giả nói có thể đưa vào Fabric App và ghi ngược kế hoạch vào database.
  → **Không phải HTML Content trong measure.** Phần tương tác (bấm chọn, mở rộng, chế độ Bedarf) cần JavaScript nên không chép nguyên được.
- Dữ liệu demo tổng hợp ("synthetische Demo-Daten").

## 2. Bố cục
- Header: logo đám mây xanh + tiêu đề "Ressourcenplanung" + dòng phụ xám nhỏ. Góc phải: nhóm nút lọc vai trò (PM | PO | Entwickler) dạng pill và dropdown "Select Standort" (địa điểm).
- Thân trang 2 cột, tỷ lệ khoảng **3 : 1**:
  - Trái: một panel lớn chứa thanh công cụ + **ma trận heatmap** (hàng = người/nhóm, cột = tuần KW46 → KW02, cột cuối = tổng / "Frei, 4 KW").
  - Phải: 3 thẻ xếp dọc: **Auslastung** (mức tải), **Projekte**, **Frei** (ai còn trống).
- Không có sidebar riêng (sidebar bên trái là của Power BI Service).

## 3. Màu (ước lượng)
| Vai trò | Hex |
|---|---|
| Nền trang | #F3F4F6 |
| Nền panel | #FFFFFF, viền #E5E7EB, bo góc ~8px, bóng rất nhẹ |
| Màu chính (nút Bedarf, pill tuần hiện tại, thanh demand, ô được chọn) | #1D6FE0 / #2563EB |
| Xanh nhạt (vùng cột đang chọn) | #E8F0FE |
| Ô đã xếp giờ (xám xanh, có gạch chéo) | #9AA8BC trên nền #C9D3E0 |
| Ô trống / mờ | #E5E7EB |
| Quá giờ / cảnh báo | #DC2626 (đỏ), chữ "+4 h überplant" |
| Chữ chính / phụ | #1F2937 / #6B7280 |

## 4. Chữ
- Số lớn KPI ("65 %", "67 %"): rất lớn (~4× nhãn), đậm vừa (600), màu đen.
- Tiêu đề thẻ ("Auslastung", "Projekte", "Frei"): ~13px, đậm 600; ngay dưới là dòng phạm vi màu xanh "Alle · 16 KW".
- Tên người: 12px đậm, dưới là số giờ/tuần xám 10px.
- Số trong ô: 9–10px, xám đậm, căn giữa.
- Cột tổng bên phải: số xanh đậm ("82 h", "24 h"), dòng cảnh báo đỏ nhỏ bên dưới.

## 5. Thành phần
1. **Thanh tóm tắt** đầu panel: "KW 46, aktuell" + các chip đếm: `6 frei`, `5 < 8 h frei`, `3 überplant` (ô đỏ), `1 abwesend`.
2. **Thanh công cụ**: segmented control `Personen | Team`, `KW | Monat`, nút xanh đặc `Bedarf`; ở chế độ Bedarf thêm `Klein | Mittel | Groß` và bộ tăng giảm `– 24 h +`.
3. **Header tuần**: số tuần, dưới là tổng giờ cả tuần; tuần hiện tại là pill xanh.
4. **Ma trận heatmap**: mỗi ô là một hình chữ nhật nhỏ, chiều cao phần tô = % tải; gạch chéo = đã xếp giờ, xanh đặc = khớp yêu cầu, gạch đỏ ở mép trên = vượt 100 %, chữ "abw." = vắng.
5. **Hàng nhóm** (PM, PO) có avatar chồng nhau + mũi tên `>` để mở rộng; nhóm "Entwickler" mở sẵn thành từng người.
6. **Cột tổng phải**: số giờ còn trống / % phù hợp; đỏ nếu quá giờ.
7. **Thẻ Auslastung**: % lớn + thanh tiến độ gạch chéo dài + 2 dòng chú thích ("1.617 von 2.401 h eingeplant", "Frei 793 h · Überplant 9 h").
8. **Thẻ Projekte**: top 5 dự án, thanh ngang xám + nhãn giờ.
9. **Thẻ Frei**: bảng nhỏ avatar + tên + số giờ trống trong ô viền xanh, có thanh cuộn và nút sắp xếp.

## 6. Hiệu ứng
- Bấm `Bedarf` → hiện thanh xanh "24 h × 6 KW" kéo trên header, các cột tương ứng tô nền xanh nhạt, người phù hợp được tô xanh đặc, người không hợp bị mờ đi; cột phải chuyển thành "% phù hợp", đếm "2 passen / 5 teilweise".
- Chọn PM/PO/Entwickler hoặc địa điểm → lọc hàng, KPI bên phải cập nhật.
- Mở rộng/thu gọn nhóm; chuyển Personen ↔ Team, KW ↔ Monat.
- Không thấy chuyển động trang trí; mọi hiệu ứng là tương tác.

## 7. Khả thi trong Power BI HTML Content
| Nhóm | Thành phần |
|---|---|
| **Làm được bằng HTML/CSS/SVG trong measure** | Panel trắng bo góc; chip đếm (frei/überplant); ma trận heatmap (CSS grid, ô tô theo %); gạch chéo bằng `repeating-linear-gradient` hoặc SVG `<pattern>`; viền đỏ cho ô vượt ngưỡng; pill tuần hiện tại; cột tổng có dòng cảnh báo đỏ; thẻ KPI % lớn + thanh tiến độ gạch chéo; thanh ngang top 5; bảng "Frei" (không avatar ảnh, dùng chữ cái đầu trong vòng tròn); tooltip `:hover` trên ô; tô sáng hàng khi rê chuột |
| **Nên dùng visual gốc / slicer** | Nút PM/PO/Entwickler và dropdown địa điểm → slicer dạng button/dropdown; `Personen | Team`, `KW | Monat` → field parameter + slicer; mở rộng nhóm → matrix gốc có drill hoặc bookmark |
| **Không làm được (cần JavaScript / custom visual)** | Chế độ Bedarf với bộ tăng giảm giờ và tính "khớp" tức thì; bấm vào ô trong HTML để lọc chéo; ghi ngược kế hoạch vào DB; cuộn trong thẻ có sắp xếp động (chỉ làm tĩnh được) |

## 8. Áp vào dashboard của Daniel (Loyalty Gift)
- **Nên lấy**:
  - Ma trận heatmap: hàng = loại quà (Product, Gimmick, Thẻ cào, E-Voucher) hoặc từng quà/brand, cột = tháng; ô tô theo tỷ lệ đổi quà hoặc % ngân sách đã dùng; viền đỏ khi vượt kế hoạch/tồn kho; cột tổng bên phải.
  - Hàng tóm tắt dạng chip: "x quà đang chạy · y sắp hết · z vượt ngân sách".
  - Cột phải 3 thẻ: KPI % sử dụng ngân sách xu (số lớn + thanh tiến độ + 2 dòng chú thích), Top 5 quà theo lượt đổi (thanh ngang), danh sách quà còn tồn nhiều / ít.
  - Tông xanh dương + xám + đỏ cảnh báo, nền trắng, rất sạch.
- **Nên bỏ**: avatar người, chế độ Bedarf, segmented control vẽ trong HTML (thay bằng slicer).
