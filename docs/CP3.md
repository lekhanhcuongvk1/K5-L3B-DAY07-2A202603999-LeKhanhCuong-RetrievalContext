# CP3 — So sánh Dev, cải thiện và khóa cấu hình

CP3 chỉ dùng Dev; Test chưa được mở. Ba phương pháp retrieval cơ bản được so sánh
trên cùng 18 câu có đáp án, cùng snapshot 418 chunks và cùng gold:

| Cấu hình | Hit@1 | Evidence Hit@3 | Context evidence | Median retrieval |
|---|---:|---:|---:|---:|
| Dense pgvector | 12/18 | 14/18 | 14/18 | 70,566 ms |
| BM25 | 13/18 | 17/18 | 17/18 | 1,147 ms |
| Hybrid RRF | 13/18 | 17/18 | 17/18 | 68,146 ms |
| Hybrid RRF, top-5 | 13/18 | 17/18 | 17/18 | 71,166 ms |

Theo tiêu chí đã công bố (context evidence, Hit@3, Hit@1, rồi latency), BM25 được
khóa cho phần cơ bản. Query rewrite local bị loại vì tự thêm dữ kiện sai. Agent
Claude qua gateway tương thích Anthropic đạt 20/21 Dev sau chấm tay; câu B01 thất
bại vì BM25 top-3 không chứa chunk định nghĩa. Ba câu thiếu evidence đều abstain.

## Advanced

Toàn bộ 409 trang được xử lý: 397 trang có text, 1.076 chunks; 12 trang không có
text extractable được báo riêng. Mỗi chunk giữ trang, bounding box và modality.

Các cải thiện Dev lần lượt là hybrid RRF, dịch query sang tiếng Anh nhưng bảo toàn
locator `Figure/Table/Map`, tăng candidate/context, ưu tiên exact locator và gom
block cùng trang. Cấu hình cuối đạt Hit@1 12/17, Evidence Hit@3 16/17 và complete
context 16/17. `A12` có evidence thay thế hợp lệ ở trang 73 nhưng metric locator
chỉ công nhận trang 72. Agent đạt 19/20 sau chấm tay; `A13` có đúng 81% và 79%
nhưng thêm một kết luận nhân quả chưa được citation hỗ trợ nên bị chấm không đạt.

Gateway trả token usage nhưng không trả giá USD; báo cáo để chi phí là `null` thay
vì tự suy đoán. Một timeout A14 được ghi lại và retry một lần với quy tắc nén context.
Toàn bộ trace, raw output, review và lý do nằm trong `artifacts/cp3/`.
