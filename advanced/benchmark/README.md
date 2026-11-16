# Benchmark nâng cao

Bộ benchmark riêng cho *Vietnam 2035* được khóa trước khi xây pipeline retrieval.
Dev gồm 17 câu có đáp án và 3 câu thiếu evidence. Test gồm 24 câu có đáp án và
6 câu thiếu evidence, với đúng một nhóm chính cho mỗi câu: 6 bảng, 5 ảnh/sơ đồ,
5 biểu đồ, 4 multi-hop và 4 text.

Mỗi evidence dương có trang vật lý của PDF, tên vùng, bounding box theo point,
đoạn trích và các cụm dùng để kiểm chứng với bản gốc. Câu multi-hop yêu cầu đủ
tất cả vùng gold. Các probe âm được dò trên text của toàn bộ 409 trang. Gold chỉ
dành cho evaluator ngoại tuyến, không được truyền vào agent, query hoặc filter.

Tạo lại sau khi tải PDF chính thức:

```powershell
python scripts/download_advanced_source.py
python scripts/build_advanced_benchmark.py
python scripts/validate_cp1.py
```
