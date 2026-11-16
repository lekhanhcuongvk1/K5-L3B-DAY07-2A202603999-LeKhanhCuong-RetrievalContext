# CP2 — Agent và retrieval đầu tiên

CP2 dùng model local thật `Qwen/Qwen2.5-1.5B-Instruct` để tạo query và trả lời từ
context. Model được khóa revision, tải vào cache của repository và không có mock
fallback. Agent chỉ trả lời khi citation ánh xạ tới block đã retrieval; nếu model
bỏ format nhưng sao chép nguyên văn evidence, hệ thống chỉ chấp nhận citation khi
chuỗi chuẩn hóa khớp chính xác với duy nhất một block. Các trường hợp khác abstain.

Hai phương pháp retrieval đầu tiên dùng cùng snapshot 418 chunks:

- `dense_pgvector`: query embedding tương thích index, exact cosine trên pgvector.
- `bm25`: BM25 deterministic, tokenizer Unicode, hỗ trợ cùng metadata filter.

Trace lưu query do model tạo, tool, filter, rank/score, context, raw model output,
answer, citation, latency và chi phí. Smoke chỉ dùng hai câu Dev (`B01`, `B19`),
không mở Test. Đây là kiểm tra wiring và hành vi, chưa phải benchmark so sánh đầy
đủ; phương pháp thứ ba, chạy toàn Dev và cải thiện thuộc CP3.

Chạy lại:

```powershell
python scripts/download_models.py
docker compose -p day7_agentic_rag -f infra/docker-compose.yml up -d
python scripts/run_cp2_smoke.py
python scripts/validate_cp2.py
```
