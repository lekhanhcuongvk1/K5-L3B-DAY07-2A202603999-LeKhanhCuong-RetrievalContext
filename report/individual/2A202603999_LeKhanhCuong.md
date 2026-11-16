# Báo cáo Day 7

**Học viên:** Lê Khánh Cường — **MSSV:** 2A202603999 — **Lớp:** L3B

## Dữ liệu và benchmark

- Nguồn Day 6: 30 bài Wikipedia tiếng Việt, CC BY-SA 4.0, snapshot `vi-wikipedia-computing-snapshot-2026-11-13`, 418 chunks strategy B.
- Vector store và embedding: PostgreSQL 16 + pgvector 0.8.7; `bkai-foundation-models/vietnamese-bi-encoder` revision `84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0`, 768 chiều, cosine exact search.
- Agent chính dùng `nghi/claude-sonnet-5.5` qua gateway tương thích Anthropic;
  model local Qwen chỉ dùng ở smoke/biến đổi query. Benchmark cơ bản đã được
  khóa trước retrieval: Dev 18 câu có đáp án + 3 câu thiếu evidence, Test 6 + 3;
  checksum nằm ở `benchmark/base_freeze.json`.
- Mỗi câu có đáp án được đối chiếu với evidence trong snapshot 418 chunks. Câu thiếu evidence được dò trên toàn snapshot. Gold không được đưa vào agent, query hoặc filter.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline | Dense exact, top-3, 3.600 ký tự | Baseline embedding Day 6 | dev | 12/18 | 14/18 | 14/18 | 70,566 ms; 0 USD |
| Phương pháp 2 | BM25, top-3, 3.600 ký tự | Từ hiếm/tên riêng có lợi cho lexical | dev | 13/18 | 17/18 | 17/18 | 1,147 ms; 0 USD |
| Phương pháp 3 | Hybrid RRF, top-3, 3.600 ký tự | Hợp nhất dense và lexical theo rank | dev | 13/18 | 17/18 | 17/18 | 68,146 ms; 0 USD |
| Cải thiện 1 | Hybrid RRF, top-3 | Giảm lỗi do một retriever bỏ sót | dev | 13/18 | 17/18 | 17/18 | 68,146 ms; 0 USD |
| Cải thiện 2 | Hybrid RRF, top-5, 5.000 ký tự | Nới candidate và context | dev | 13/18 | 17/18 | 17/18 | 71,166 ms; 0 USD |
| Cấu hình đã chọn | BM25, top-3, 3.600 ký tự | Đồng hạng chất lượng, latency thấp nhất trên Dev | test | 5/6 | 6/6 | 6/6 | 6.701 ms tổng; giá USD không có |
| Baseline | Dense exact, top-3, 3.600 ký tự | Đối chứng sau khi khóa | test | 5/6 | 6/6 | 6/6 | 9.693 ms tổng; giá USD không có |

Hai lỗi Dev đáng chú ý là dense bỏ sót tên riêng/từ khóa chính xác và mọi cấu
hình đều bỏ một evidence ở top-3. BM25 sửa phần lớn lỗi đầu; tăng top-k không sửa
lỗi còn lại nhưng tăng latency. Vì BM25 và hybrid cùng đạt 17/18 Evidence Hit@3,
BM25 được chọn trước khi mở Test theo tie-break latency.

Trên Base Dev, dense đạt Hit@1 `12/18`, Evidence Hit@3 `14/18`; BM25 đạt `13/18`, `17/18`; hybrid RRF đạt `13/18`, `17/18`. BM25 được chọn theo tie-break latency và khóa trước Test. Agent Claude qua gateway tương thích Anthropic đạt `20/21` sau chấm tay; lỗi B01 do evidence không vào BM25 top-3. Local Qwen có grounded-answer mean `0,444/2`, cho thấy retrieval tốt nhưng model nhỏ chưa tuân thủ citation ổn định.

## Agent và đánh giá

- CP2 dùng `Qwen/Qwen2.5-1.5B-Instruct` revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, chạy local. Model tạo query và câu trả lời; hai tool đầu tiên là exact dense pgvector và BM25. Mỗi smoke có một lượt retrieval, top-3, context tối đa 3.600 ký tự; thiếu citation hợp lệ hoặc thiếu evidence thì abstain. Lỗi được truyền ra, không có mock fallback.
- Smoke Dev gồm một câu có evidence và một câu thiếu evidence cho mỗi tool. Cả hai tool trả lời đúng `B01` với citation hỗ trợ, đồng thời từ chối đúng `B19`; đây là kiểm tra wiring CP2, chưa được dùng như benchmark đầy đủ để chọn cấu hình.

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 / Base Dev | 21/21 | 21 | 20 đạt, 1 không đạt | 20/20 | 17/18 câu có đáp án | 3/3 | 1 |
| BM25 / Base Test | 9/9 | 9 | 9 đạt | 6/6 | 6/6 câu có đáp án | 3/3 | 0 |
| Dense / Base Test | 9/9 | 9 | 9 đạt | 6/6 | 6/6 câu có đáp án | 3/3 | 0 |

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| B22–B27 | Có evidence | BM25 và dense, top-3 | Trả lời có citation trong corpus | Đạt 6/6 ở cả hai cấu hình |
| B28–B30 | Thiếu evidence | Vẫn search trước khi dừng | Từ chối, không thêm khẳng định | Đạt 3/3 ở cả hai cấu hình |

- Trace và nhãn: `artifacts/cp4/base_test/`; lệnh chạy và chi tiết latency nằm ở
  `docs/CP4.md`. Gateway trả token usage nhưng không trả giá USD nên chi phí để
  `null`, không tự suy đoán.
- Trên Test, BM25 và dense cùng đạt 9/9. Tập Test nhỏ nên kết quả chỉ chứng minh
  pipeline xử lý đúng bộ benchmark đã khóa, không khẳng định ưu thế tổng quát.

## Thử thách nâng cao

- Tài liệu đã khóa: *Vietnam 2035: Toward Prosperity, Creativity, Equity, and Democracy*, World Bank và Bộ Kế hoạch và Đầu tư, 2016, DOI `10.1596/978-1-4648-0824-1`, 409 trang vật lý, CC BY 3.0 IGO. URL, SHA-256 và attribution nằm ở `advanced/source_manifest.json`.
- PDF được trích theo layout thành block có trang, loại block, bounding box và
  locator ổn định. Text, bảng, caption và nội dung biểu đồ/ảnh có text extractable
  được index chung; query tiếng Việt được dịch local sang tiếng Anh trước hybrid
  retrieval. Pipeline chưa dùng vision/OCR cho 12 trang không có text extractable,
  nên không tuyên bố bao phủ nội dung trực quan ở các trang đó.
- Benchmark riêng đã khóa gồm 20 Dev (17 có đáp án, 3 thiếu evidence) và 30 Test (24 có đáp án, 6 thiếu evidence). Test có đúng 6 câu bảng, 5 ảnh/sơ đồ, 5 biểu đồ, 4 multi-hop và 4 text; từng gold locator có trang, vùng, bounding box và đoạn trích từ PDF gốc.
- Index Advanced bao phủ 397/409 trang, 1.076 chunks; 12 trang không có text extractable được ghi rõ. Cấu hình hybrid + dịch query bảo toàn locator + context theo layout đạt Evidence Hit@3 `16/17`, complete context `16/17`; agent đạt `19/20` Dev sau chấm tay. Gateway chỉ trả token usage, không trả giá USD nên chi phí được để `null`, không tự ước lượng.

| Nhóm test | Đạt / tổng | Tỷ lệ | Lỗi / nhận xét |
|---|---|---|---|
| Bảng | 5/6 | 83,3% | A21 từ chối nhầm |
| Ảnh, sơ đồ | 5/5 | 100% | Locator và số liệu đúng |
| Biểu đồ | 4/5 | 80% | A34 nhầm mức tăng với tỷ trọng |
| Multi-hop | 0/4 | 0% | Thiếu một hop hoặc từ chối nhầm |
| Text | 2/4 | 50% | A41, A43 từ chối nhầm |
| Thiếu bằng chứng | 6/6 | 100% | Từ chối đúng cả sáu câu |
| **Toàn bộ** | **22/30** | **73,3%** | Chưa đạt ngưỡng bonus 27/30 |

- Trace, review từng câu và summary nằm tại `artifacts/cp4/advanced_test/`. Không
  còn lỗi hệ thống trong artifact cuối; 179.358 input token, 6.815 output token,
  median tổng 12.784 ms. Gateway không cung cấp giá USD.
- Điểm yếu tập trung ở multi-hop và recall text. Vì Test đã mở, pipeline không
  được chỉnh rồi báo lại trên cùng bộ Test. Lệnh tái lập, giới hạn và mô tả retry
  nằm trong `docs/CP4.md`; benchmark gốc ở `advanced/benchmark/questions.json`.
