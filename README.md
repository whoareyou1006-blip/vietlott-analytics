# 🎰 Vietlott Power 6/55 — Analytics & Dự đoán

> 🌐 **English version:** [README.en.md](README.en.md)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/whoareyou1006-blip/vietlott-analytics)

Ứng dụng tích hợp dữ liệu Power 6/55 từ **4 nguồn** vào một database SQLite đồng nhất,
kèm engine phân tích thống kê và dự đoán 2 dãy số.

## Tính năng

- **Tích hợp 4 nguồn dữ liệu** (đồng bộ, đối chiếu chéo):
  | Nguồn | Dữ liệu |
  |---|---|
  | `vietvudanh/vietlott-data` (GitHub) | Toàn bộ lịch sử 1.396 kỳ quay (2017-08-01 → nay) |
  | `xosovietlott.org` | Bảng tần suất all-time |
  | `atrungroi.com` | Tần suất 100 kỳ, cặp số, lịch sử Jackpot |
  | `kqxs.day` (API wp-json) | Kỳ quay + giá trị Jackpot 1/2 |

- **Database SQLite đồng nhất** (`data/vietlott.db`): kỳ quay, tần suất (all-time/30/60/90 kỳ),
  số gan, số Power, cặp số, lịch sử Jackpot — truy cập mọi nơi qua API.

- **Dự đoán 2 dãy số** theo 2 chiến lược (v2):
  1. **Cân bằng** — tần suất suy giảm theo thời gian + mean-reversion, cấu trúc 3 lẻ/3 chẵn, tổng quanh 170
  2. **Nóng + Gan** — số đang nóng gần đây + số lâu chưa về, cấu trúc 4 lẻ/2 chẵn
  - Ràng buộc cấu trúc dựa trên thống kê lịch sử: lẻ/chẵn, tổng 106–228 (90% kỳ), ≥4 chục, ≤2 số liên tiếp
  - 2 dãy không trùng số (phủ 12/55 số)

- **Backtest trung thực**: 300 kỳ walk-forward (dự đoán chỉ dùng dữ liệu *trước* kỳ đó),
  so sánh với ngẫu nhiên thuần và ngẫu nhiên có cấu trúc. Kết quả: mọi chiến lược
  **ngang ngửa ngẫu nhiên** — xổ số ngẫu nhiên không có chiến lược thắng.

- **Xác suất thật** (hypergeometric): 0 số 48.2%, 1 số 39.5%, 2 số 11.0%, 3 số 1.27%,
  4 số 0.06%, 5 số 0.001%, Jackpot 1: 1/28.989.675.

- **Web dashboard** (không cần internet, không CDN): kỳ quay, biểu đồ tần suất,
  số gan, Jackpot, cặp số, kiểm chứng, nguồn dữ liệu.

- **Tự cập nhật kỳ quay mới** (v3):
  - Server tự kiểm tra kỳ quay mới **mỗi 30 phút**; khi có kỳ mới → tự cập nhật
    database + tự chạy lại dự đoán (thống kê + AI nếu đã cấu hình).
  - Nút **"🔄 Cập nhật kết quả"** trên dashboard để cập nhật thủ công bất cứ lúc nào.
  - Dashboard tự làm mới mỗi 30 giây, hiển thị kỳ mới nhất + dự đoán mới.

- **AI Mode** (v3): dự đoán 2 dãy số bằng AI qua **Google Gemini / OpenAI / Ollama**:
  - Tab **"🤖 AI Dự đoán"**: chọn nhà cung cấp, nhập API key/token, base URL, model.
  - Nút **"🔌 Kiểm tra kết nối"**: xác minh API hoạt động trước khi dùng.
  - Nút **"🤖 Dự đoán bằng AI"**: gửi bối cảnh thống kê (kỳ gần, tần suất, số gan,
    cấu trúc) cho AI, AI trả về 2 dãy số kèm lý do.
  - Cấu hình lưu tại `data/ai_config.json` (cục bộ, API key được che khi hiển thị).
  - Sau khi cập nhật kỳ mới, hệ thống **tự động chạy dự đoán AI** nếu đã cấu hình.

## Cách chạy

### Từ bản clone mới (git)

Chỉ cần **Python 3.8+** (chỉ dùng thư viện chuẩn, không cần `pip install`):

```
git clone <repo-url>
cd Vietlot

# 1. Thu thập dữ liệu từ 4 nguồn (cần internet, ~1 phút)
python scripts\fetch_data.py

# 2. Xây database SQLite
python scripts\build_db.py

# 3. Khởi động web dashboard
python app\server.py 8000
# mở http://localhost:8000
```

Hoặc gọn hơn trên Windows: chạy `start.bat` → chọn **2** (cập nhật dữ liệu) → **1** (khởi động app).

> Lưu ý: `data/` (database + dữ liệu thô) và `runtime/` (Python portable) **không nằm trong git** — chúng được tạo lại tự động bằng 2 lệnh trên. Cấu hình AI (`data/ai_config.json`, chứa API key) cũng là file cục bộ, không commit.

### Có sẵn runtime portable (máy cũ)

```
start.bat
```
Chọn:
- **1** — Khởi động app → mở trình duyệt tại http://localhost:8000
- **2** — Cập nhật dữ liệu từ 4 nguồn (cần internet)
- **3** — Chạy dự đoán + backtest ở console

Hoặc chạy trực tiếp:
```
runtime\python\python.exe app\server.py 8000
runtime\python\python.exe scripts\fetch_data.py   # thu thập dữ liệu thô
runtime\python\python.exe scripts\build_db.py     # xây database
runtime\python\python.exe scripts\predict.py      # dự đoán + backtest
```

## API

| Endpoint | Mô tả |
|---|---|
| `/api/stats` | Tổng quan (số kỳ, phạm vi, jackpot lớn nhất) |
| `/api/draws?limit=20` | Kỳ quay gần nhất |
| `/api/frequency?scope=all_time\|last_30\|last_60\|last_90\|power` | Tần suất |
| `/api/gan` | Số ngày chưa xuất hiện của từng số |
| `/api/predict` | 2 dãy số dự đoán + tín hiệu thô + cấu trúc |
| `/api/backtest?n=300` | Kết quả kiểm chứng (so sánh với ngẫu nhiên) |
| `/api/probabilities` | Xác suất thật của 1 vé 6/55 |
| `/api/jackpots` | 20 Jackpot lớn nhất lịch sử |
| `/api/pairs` | Cặp số hay về cùng |
| `/api/sources` | Thông tin 4 nguồn |
| `POST /api/update` | Cập nhật kỳ quay mới nhất (chạy nền) |
| `GET /api/update/status` | Trạng thái cập nhật + dự đoán tự động |
| `GET /api/ai/config` | Cấu hình AI (API key được che) |
| `POST /api/ai/config` | Lưu cấu hình AI (provider, api_key, base_url, model) |
| `POST /api/ai/check` | Kiểm tra kết nối API AI |
| `POST /api/ai/predict` | Dự đoán 2 dãy số bằng AI |

## Cấu trúc

```
Vietlot\
├── runtime\python\        Python portable (tùy chọn, không commit)
├── data\                  Tạo lại tự động khi chạy (không commit)
│   ├── raw\               Dữ liệu thô từ 4 nguồn (JSON)
│   ├── ai_config.json     Cấu hình AI (chứa API key - cục bộ)
│   └── vietlott.db        Database SQLite đồng nhất
├── scripts\
│   ├── fetch_data.py      Thu thập 4 nguồn
│   ├── build_db.py        Xây database
│   ├── predict.py         Engine dự đoán + backtest
│   ├── ai_provider.py     AI Mode: Gemini / OpenAI / Ollama
│   ├── auto_update.py     Tự cập nhật kỳ quay mới
│   └── verify_db.py       Xác minh dữ liệu
├── app\
│   ├── server.py          Web server + API + auto-update
│   └── static\index.html  Dashboard
├── start.bat              Khởi động 1 chạm (Windows)
└── .gitignore             Loại runtime/, data/, cache
```

## ⚠️ Lưu ý

Power 6/55 là trò chơi quay số ngẫu nhiên, mỗi kỳ độc lập. Kiểm chứng 300 kỳ cho thấy
mọi chiến lược thống kê đều ngang ngửa chọn số ngẫu nhiên. Dự đoán chỉ giúp chọn dãy số
có cấu trúc giống kết quả thực tế và tránh trùng lặp vé — **không làm tăng xác suất trúng**.
Cách duy nhất tăng cơ hội là mua nhiều vé hơn (hoặc vé bao). Chơi có trách nhiệm.