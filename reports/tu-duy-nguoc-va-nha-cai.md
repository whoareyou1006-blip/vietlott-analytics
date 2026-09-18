# Kiểm chứng "tư duy ngược" và giả thuyết "nhà cái né số đông"

**Ngày:** 2026-09-12 · **Dữ liệu:** 1.397 kỳ Power 6/55 (2017-08-01 → 2026-09-12)

## Câu hỏi

1. Nếu mô hình gợi ý sai, **làm ngược lại** (chọn số lạnh, chọn ngược mô hình) có thắng không?
2. Có phải **nhà cái né những số đông người chọn** (ngày sinh 1–31, số nóng) để tránh phải trả nhiều?

## Phần 1 — Backtest 300 kỳ: tư duy ngược vs mô hình vs ngẫu nhiên

Walk-forward: mỗi kỳ chỉ dùng dữ liệu **trước** kỳ đó. Tất cả chiến lược đều áp cùng ràng buộc cấu trúc.

| Chiến lược | TB số trúng/kỳ | ≥2 số | Phân phối 0/1/2/3 |
|---|---|---|---|
| Mô hình Cân bằng | 0.713 | 16.0% | 141 / 111 / 42 / 5 |
| **NGƯỢC mô hình** | **0.650** | 12.3% | 144 / 119 / 35 / 2 |
| **Số lạnh (gan + freq thấp)** | **0.650** | 11.3% | 146 / 120 / 29 / 3 |
| **Ngược số nóng (30 kỳ)** | **0.577** | 11.7% | 162 / 103 / 35 / 0 |
| Ngẫu nhiên | 0.667 | 13.7% | 148 / 111 / 34 / 7 |

**Kết luận:** Các chiến lược "làm ngược" **không tốt hơn ngẫu nhiên** — thậm chí "ngược số nóng" còn tệ nhất (0.577). Sai số chuẩn ~0.05 số/kỳ với N=300, nên mọi chênh lệch <0.1 đều là **nhiễu thống kê**, không phải lợi thế thật.

> Lưu ý: lần chạy này mô hình đạt 0.713 (cao nhất), lần trước chỉ 0.640 — chính sự thay đổi giữa các lần chạy đã chứng minh "người thắng" chỉ là ngẫu nhiên.

## Phần 2 — Kiểm tra giả thuyết "nhà cái né số đông"

### 2a. Số 1–31 (ngày sinh, người chơi hay chọn) vs 32–55

| Nhóm | Thực tế | Kỳ vọng | Lệch |
|---|---|---|---|
| 1–31 | 4.655 | 4.724,4 | −69,4 |
| 32–55 | 3.727 | 3.657,6 | +69,4 |

Chi-square = **2,336** (ngưỡng 3,84 ở mức ý nghĩa 5%) → **KHÔNG lệch bất thường**. Nhà cái không né số ngày sinh.

### 2b. Số vừa ra kỳ trước có bị né kỳ sau?

| | Thực tế | Kỳ vọng |
|---|---|---|
| Số nóng lặp lại | 916 | 913,7 |

Lệch +2,3 → **số nóng không bị né**.

### 2c. Số gan lâu có "đến lượt" nhiều hơn?

| Nhóm | Tỷ lệ xuất hiện |
|---|---|
| Gan cao | 11,00% |
| Gan thấp | 10,80% |
| Kỳ vọng ngẫu nhiên | 10,91% |

→ **Số gan không có lợi thế.**

## Vì sao nhà cái không cần can thiệp

1. **Lợi nhuận nằm ở cơ cấu giải, không ở con số.** Vietlott trả thưởng ~55% doanh thu; phần còn lại là chi phí và lợi nhuận — cố định bất kể số nào ra.
2. **Quay bằng máy bóng vật lý**, tường thuật trực tiếp, có giám sát độc lập.
3. **Không biết vé của bạn cho đến khi bán xong**, và kể cả biết cũng không cần can thiệp.
4. Can thiệp để né số đông là **gian lận hình sự**, rủi ro cực lớn mà lợi ích bằng không.

## Kết luận cốt lõi

- **Tư duy ngược không hiệu quả.** Mô hình trượt kỳ này không làm cho "số ngược lại" dễ ra kỳ sau — đây là **ngụy biện con bạc** (gambler's fallacy).
- **Không có bằng chứng nhà cái can thiệp.** Kết quả phù hợp hoàn hảo với quay số ngẫu nhiên công bằng.
- **Mọi chiến lược (xuôi hay ngược) đều không đổi được xác suất.** Mỗi kỳ độc lập. Cách duy nhất tăng cơ hội là **mua nhiều vé hơn** (hoặc vé bao để nhân giải khi trúng).
