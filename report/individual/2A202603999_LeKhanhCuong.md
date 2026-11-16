# Báo cáo Day 7

**Học viên:** Lê Khánh Cường — **MSSV:** 2A202603999 — **Lớp:** L3B

## Dữ liệu và benchmark

- Nguồn Day 6: 30 bài Wikipedia tiếng Việt, CC BY-SA 4.0, snapshot `vi-wikipedia-computing-snapshot-2026-11-13`, 418 chunks strategy B.
- Vector store và embedding: PostgreSQL 16 + pgvector 0.8.7; `bkai-foundation-models/vietnamese-bi-encoder` revision `84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0`, 768 chiều, cosine exact search.
- Agent model sẽ được khóa ở checkpoint sau. Benchmark cơ bản đã được khóa trước retrieval: Dev 18 câu có đáp án + 3 câu thiếu evidence, Test 6 + 3; checksum nằm ở `benchmark/base_freeze.json`.
- Mỗi câu có đáp án được đối chiếu với evidence trong snapshot 418 chunks. Câu thiếu evidence được dò trên toàn snapshot. Gold không được đưa vào agent, query hoặc filter.

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

Trên Base Dev, dense đạt Hit@1 `12/18`, Evidence Hit@3 `14/18`; BM25 đạt `13/18`, `17/18`; hybrid RRF đạt `13/18`, `17/18`. BM25 được chọn theo tie-break latency và khóa trước Test. Agent Claude qua gateway tương thích Anthropic đạt `20/21` sau chấm tay; lỗi B01 do evidence không vào BM25 top-3. Local Qwen có grounded-answer mean `0,444/2`, cho thấy retrieval tốt nhưng model nhỏ chưa tuân thủ citation ổn định.

## Agent và đánh giá

- CP2 dùng `Qwen/Qwen2.5-1.5B-Instruct` revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, chạy local. Model tạo query và câu trả lời; hai tool đầu tiên là exact dense pgvector và BM25. Mỗi smoke có một lượt retrieval, top-3, context tối đa 3.600 ký tự; thiếu citation hợp lệ hoặc thiếu evidence thì abstain. Lỗi được truyền ra, không có mock fallback.
- Smoke Dev gồm một câu có evidence và một câu thiếu evidence cho mỗi tool. Cả hai tool trả lời đúng `B01` với citation hỗ trợ, đồng thời từ chối đúng `B19`; đây là kiểm tra wiring CP2, chưa được dùng như benchmark đầy đủ để chọn cấu hình.

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|

- Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí: sẽ được bổ sung từ artifacts thực tế.
- Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn: sẽ được phân tích sau khi chạy Dev và Test đúng quy trình.

## Thử thách nâng cao

- Tài liệu đã khóa: *Vietnam 2035: Toward Prosperity, Creativity, Equity, and Democracy*, World Bank và Bộ Kế hoạch và Đầu tư, 2016, DOI `10.1596/978-1-4648-0824-1`, 409 trang vật lý, CC BY 3.0 IGO. URL, SHA-256 và attribution nằm ở `advanced/source_manifest.json`.
- Cách xử lý text, bảng, ảnh, biểu đồ; phạm vi index và phần chưa xử lý: sẽ được ghi từ pipeline thực tế.
- Benchmark riêng đã khóa gồm 20 Dev (17 có đáp án, 3 thiếu evidence) và 30 Test (24 có đáp án, 6 thiếu evidence). Test có đúng 6 câu bảng, 5 ảnh/sơ đồ, 5 biểu đồ, 4 multi-hop và 4 text; từng gold locator có trang, vùng, bounding box và đoạn trích từ PDF gốc.
- Index Advanced bao phủ 397/409 trang, 1.076 chunks; 12 trang không có text extractable được ghi rõ. Cấu hình hybrid + dịch query bảo toàn locator + context theo layout đạt Evidence Hit@3 `16/17`, complete context `16/17`; agent đạt `19/20` Dev sau chấm tay. Gateway chỉ trả token usage, không trả giá USD nên chi phí được để `null`, không tự ước lượng.

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
