# Snapshot đầu vào Day 6

Đây là bản sao độc lập, có provenance, của đầu ra Day 6 dùng cho phần cơ bản
Day 7. Repository không đọc file, model cache hay database từ working tree Day 6.

- 30 tài liệu Wikipedia tiếng Việt, CC BY-SA 4.0.
- 418 chunks từ strategy B (paragraph-aware, tối đa 1.000 ký tự).
- `manifest.json` và `source_catalog.json` giữ nguồn và giấy phép.
- `chunks.json` dùng schema thống nhất `id/text/source_id/source/page/metadata`.

`scripts/import_day6.py` chỉ là công cụ tái tạo snapshot từ commit Day 6 đã khóa;
pipeline chạy bình thường chỉ dùng dữ liệu nằm trong repository này.
