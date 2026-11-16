# CP4 — Đánh giá Test và tổng hợp

CP4 chỉ mở Test sau khi hai cấu hình đã được chốt trên Dev ở CP3. Gold answer và
gold locator không được truyền vào retrieval hay agent. Mỗi trace giữ query, kết
quả tool, context, answer, citation, token usage, latency và lỗi.

## Base Test

Hai cấu hình được chạy trên cùng 9 câu Test để so sánh sau khi chốt:

| Cấu hình | Hit@1 | Evidence Hit@3 | Context evidence | Agent đạt | Abstention đúng | Median tổng |
|---|---:|---:|---:|---:|---:|---:|
| Dense baseline | 5/6 | 6/6 | 6/6 | 9/9 | 3/3 | 9.693 ms |
| BM25 đã chọn | 5/6 | 6/6 | 6/6 | 9/9 | 3/3 | 6.701 ms |

BM25 giữ chất lượng bằng dense trên tập nhỏ này nhưng có tổng thời gian trung vị
thấp hơn. Không có lỗi hệ thống sau retry. Lần gọi lỗi `B25` ban đầu được giữ
trong nhật ký chạy, sau đó chạy lại đúng cùng cấu hình; trace cuối có 18/18 kết
quả và `errors = 0`.

## Advanced Test

Cấu hình đã khóa là hybrid RRF, query tiếng Anh do model local dịch, `top_k=10`
và context packing theo locator. Kết quả được đọc và chấm từng câu theo PDF gốc:

| Nhóm | Đạt / tổng | Tỷ lệ | Nhận xét |
|---|---:|---:|---|
| Bảng | 5/6 | 83,3% | A21 từ chối nhầm |
| Ảnh, sơ đồ | 5/5 | 100% | Đọc đúng locator và số liệu |
| Biểu đồ | 4/5 | 80% | A34 nhầm mức tăng 5,6 với tỷ trọng 10,0 |
| Multi-hop | 0/4 | 0% | Thiếu một hop hoặc từ chối khi evidence phân tán |
| Text | 2/4 | 50% | A41 và A43 từ chối nhầm |
| Thiếu bằng chứng | 6/6 | 100% | Từ chối đúng, không thêm khẳng định |
| **Toàn bộ** | **22/30** | **73,3%** | Không đạt ngưỡng bonus 27/30 |

Kết quả này không đủ điều kiện nhận 15 điểm Advanced theo rubric. Điểm mạnh là
ảnh/sơ đồ và abstention; điểm nghẽn là context multi-hop và recall ở các đoạn
text phân tán. Test đã mở nên không tiếp tục chỉnh pipeline rồi báo lại trên cùng
Test. Một vòng cải thiện hợp lệ cần tạo test mới hoặc giữ kết quả này làm đánh
giá cuối và chỉ phân tích lỗi.

## Tái lập

```powershell
$env:PYTHONIOENCODING="utf-8"
python scripts/run_cp4_base_test.py
python scripts/run_cp4_advanced_test.py
python scripts/summarize_cp4.py
python scripts/validate_cp4.py
```

Các runner có resume theo `query_id`/cấu hình. API gateway chỉ trả token usage,
không trả giá USD, vì vậy chi phí dịch vụ để `null` thay vì tự ước lượng. Gemini
chỉ là đường retry tùy chọn khi gateway chính lỗi; trace cuối A24 dùng provider
chính và toàn bộ artifact cuối không trộn provider.

Artifact: `artifacts/cp4/base_test/` và `artifacts/cp4/advanced_test/`.
