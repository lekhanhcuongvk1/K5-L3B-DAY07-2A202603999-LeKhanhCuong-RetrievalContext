# Báo cáo Day 7

**Học viên:** Lê Khánh Cường — **MSSV:** 2A202603999 — **Lớp:** L3B

## Dữ liệu và benchmark

- Nguồn Day 6: 30 bài Wikipedia tiếng Việt, CC BY-SA 4.0, snapshot `vi-wikipedia-computing-snapshot-2026-11-13`, 418 chunks strategy B.
- Vector store và embedding: PostgreSQL 16 + pgvector 0.8.7; `bkai-foundation-models/vietnamese-bi-encoder` revision `84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0`, 768 chiều, cosine exact search.
- Agent model, cách chạy và phân chia dev/test: sẽ được điền sau khi benchmark và provider được khóa trên Dev.
- Cách xác định câu có/thiếu evidence và tiêu chí chấm: benchmark Day 7 mới sẽ được kiểm chứng trên toàn corpus và khóa checksum trước retrieval; không đưa gold vào agent hoặc query.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline | | | dev | | | | |
| Phương pháp 2 | | | dev | | | | |
| Phương pháp 3 | | | dev | | | | |
| Cải thiện 1 | | | dev | | | | |
| Cải thiện 2 | | | dev | | | | |
| Cấu hình đã chọn | | | test | | | | |
| Baseline | | | test | | | | |

Một cấu hình có thể đồng thời là phương pháp mới và cải thiện; phần kết quả sẽ báo `n/N`, tỷ lệ, thời gian, chi phí, hai lỗi Dev và lý do chọn trước khi mở Test.

## Agent và đánh giá

- Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi: sẽ được điền từ cấu hình đã chạy thật.

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|

- Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí: sẽ được bổ sung từ artifacts thực tế.
- Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn: sẽ được phân tích sau khi chạy Dev và Test đúng quy trình.

## Thử thách nâng cao

- Tài liệu, nguồn, quyền sử dụng, số trang và phiên bản: sẽ khóa trước khi trích xuất.
- Cách xử lý text, bảng, ảnh, biểu đồ; phạm vi index và phần chưa xử lý: sẽ được ghi từ pipeline thực tế.
- Benchmark riêng gồm 20 Dev và 30 Test; Test có 24 câu có đáp án và 6 câu thiếu bằng chứng, được khóa trước thử nghiệm.

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|---|---|---|
| Bảng | | | |
| Ảnh, sơ đồ | | | |
| Biểu đồ | | | |
| Multi-hop | | | |
| Text | | | |
| Thiếu bằng chứng | | | |
| **Toàn bộ** | | | |

- Trace, nhãn và evidence từng câu; thời gian, chi phí, lỗi hệ thống: sẽ được điền từ lần chạy đã khóa.
- Giới hạn, cách tái lập và đường dẫn benchmark: sẽ được hoàn thiện trước khi nộp.
