# Benchmark cơ bản

`base_questions.json` là bộ câu hỏi Day 7 mới, được tạo và khóa trước khi thử
retrieval. Bộ Dev có 18 câu có đáp án và 3 câu thiếu bằng chứng; bộ Test có 6
câu có đáp án và 3 câu thiếu bằng chứng. Test được giữ kín để đánh giá sau khi
chọn cấu hình trên Dev.

Mỗi câu có đáp án trỏ đến `source_id`, `page` và đoạn evidence tồn tại trong
snapshot 418 chunks. Câu thiếu evidence được kiểm tra trên toàn snapshot, không
được đưa vào mẫu số Hit@k. `base_freeze.json` giữ checksum để phát hiện thay đổi.

Tạo lại và xác minh:

```powershell
python scripts/build_base_benchmark.py
python scripts/validate_cp1.py
```
