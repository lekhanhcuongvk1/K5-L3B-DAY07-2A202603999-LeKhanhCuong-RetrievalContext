# Day 7 — Agentic RAG

**Bài cá nhân · Lê Khánh Cường · 2A202603999 · L3B · Python 3.11+**

Repository này là bài nộp Day 7, tiếp nối pipeline dữ liệu tiếng Việt đã hoàn
thành ở Day 6. Phần cơ bản xây agent có retrieval, context, citation và
abstention; phần nâng cao xử lý một tài liệu thực tế từ 100 trang có text, bảng,
ảnh và biểu đồ.

Dùng embedding và vector store từ Day 6 để xây một agent biết tìm bằng chứng, trả lời có nguồn và nhận biết khi không đủ thông tin. Bạn tự chọn kiến trúc, số tool và cách tổ chức retrieval.

## Nguồn Day 6 đã khóa

- Repo nguồn: [K5-L3B-DAY06-LeKhanhCuong-2A202603999-DataIngestion](https://github.com/lekhanhcuongvk1/K5-L3B-DAY06-LeKhanhCuong-2A202603999-DataIngestion), commit `3f67d939f92734f11cfbe5ee7be025b38c2b3403`.
- Corpus: 30 bài Wikipedia tiếng Việt, 334.955 ký tự chuẩn hóa, CC BY-SA 4.0.
- Chunk dùng cho Day 7: strategy B, paragraph-aware tối đa 1.000 ký tự, 418 chunks.
- Embedding: `bkai-foundation-models/vietnamese-bi-encoder`, revision `84f9d9ada0d1a3c37557398b9ae9fcedcdf40be0`, 768 chiều, chạy local.
- Store: PostgreSQL 16 + pgvector 0.8.7 chạy độc lập trong Day 7, bảng
  `day07_base_chunks`, exact cosine search. Upsert 418/418 chunks có thể chạy lại
  mà không sinh bản ghi trùng.

Các giá trị trên là bất biến đầu vào. Nếu phải đổi corpus, model hoặc index, bài
làm sẽ ghi thành một thí nghiệm mới thay vì âm thầm thay thế baseline.

## Kế hoạch đánh giá đã khóa

- Phần cơ bản dùng benchmark Day 7 mới gồm 21 Dev và 9 Test: 24 câu có đáp án,
  6 câu thiếu evidence. Dev dùng để chọn cấu hình; Test chỉ chạy sau freeze.
- So sánh tối thiểu dense, lexical và hybrid trên cùng corpus và nhãn.
- Thử ít nhất hai cấu hình cải thiện trên Dev; lưu query, tool call, ranking,
  context, answer, citation, thời gian, chi phí và lỗi.
- Phần nâng cao dùng benchmark riêng: 20 Dev và 30 Test, trong đó Test có đủ
  24 câu có đáp án theo năm nhóm và 6 câu thiếu evidence.
- Không đưa gold answer, gold source hay evidence vào agent, query hoặc filter.

Đặc tả máy đọc được nằm tại [`config/experiment_plan.json`](config/experiment_plan.json).

> **Tùy chọn:** [Gợi ý dùng AI để lập trình](AGENT_SETUP.md) giúp bạn làm lab; phần này không bắt buộc và không tính điểm.

## Bài cần làm

![Agent tìm tài liệu trong kho Day 6 và trả lời có nguồn](assets/retrieval-pipeline.svg)

1. Kết nối dữ liệu, embedding và vector store Day 6.
2. Xây agent dùng model thật và ít nhất một khả năng truy xuất dữ liệu. Agent có thể dùng nhiều tool và nhiều lượt gọi.
3. Thử **ít nhất 3 phương pháp retrieval khác nhau**, trong đó có dense retrieval dùng vector store Day 6. Tự chọn các phương pháp còn lại; xem [gợi ý](GUIDE.md#2-thử-các-phương-pháp-retrieval).
4. Thử nhiều cấu hình, benchmark, phân tích lỗi và chọn cấu hình tốt trên **dev**; sau đó đánh giá trên **test**.

Benchmark tối thiểu có **24 câu**: dev gồm 15 câu có đáp án và 2 câu thiếu bằng chứng; test gồm 5 câu có đáp án và 2 câu thiếu bằng chứng. Xem [benchmark](BENCHMARK.md) và [rubric](RUBRIC.md).

## Thử thách nâng cao · +15 điểm

Index một tài liệu thực tế từ **100 trang** có bảng, ảnh và biểu đồ; xây agent truy xuất và trả lời các câu hỏi về nội dung đó. Hoàn thành [thử thách nâng cao](ADVANCED.md) và đạt **ít nhất 90% benchmark test** để nhận 15 điểm bonus. Phần cơ bản tối đa 85 điểm; toàn bài tối đa 100 điểm.

## Bắt đầu

1. Đọc [hướng dẫn](GUIDE.md), [rubric](RUBRIC.md) và [quy tắc](RULES.md).
2. Tạo repo cá nhân theo [cách nộp bài](SUBMISSION.md), chuẩn bị đầu ra Day 6 và model hỗ trợ tool calling.
3. Dùng hoặc thay thế [starter](starter/README.md); bạn cần kết nối model và vector store thật.
4. Chạy `python -m unittest discover -s tests -v`. Test mock chỉ kiểm tra code, không phải benchmark agent thật.

### Tái lập CP1

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts/download_models.py
docker compose -p day7_agentic_rag -f infra/docker-compose.yml up -d
python scripts/build_base_index.py
python scripts/download_advanced_source.py
python scripts/build_base_benchmark.py
python scripts/build_advanced_benchmark.py
python scripts/validate_cp1.py
```

Model và PDF được tải vào thư mục bị Git ignore; source manifest, checksum, benchmark,
code và metadata index được nộp để người chấm tái lập. CP1 chưa dùng test để chọn cấu hình.

![Các bước thử nghiệm trên dev và đánh giá trên test](assets/experiment-loop.svg)

Nộp code, cách chạy, cấu hình, benchmark, trace và [báo cáo](report/individual/MSSV_HoTen.md). Thời gian ở [checkpoints](CHECKPOINTS.md) là gợi ý, có thể điều chỉnh theo lớp và phạm vi thử nghiệm.
