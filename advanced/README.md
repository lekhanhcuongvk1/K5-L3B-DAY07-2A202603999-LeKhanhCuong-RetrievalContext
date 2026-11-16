# Nguồn cho thử thách nâng cao

Tài liệu được chọn là **Vietnam 2035: Toward Prosperity, Creativity, Equity, and
Democracy**, do World Bank Group và Bộ Kế hoạch và Đầu tư Việt Nam xuất bản năm
2016. Bản đã khóa có 409 trang vật lý, 397 trang có text trích xuất được và chứa
text, bảng, ảnh cùng nhiều biểu đồ có số liệu.

Tác phẩm được phát hành theo CC BY 3.0 IGO. Trang 6 của PDF ghi giấy phép và mẫu
attribution; một số thành phần bên thứ ba có thể cần điều kiện riêng nên pipeline
phải giữ source/page/bounding box và không mặc định tái phân phối mọi hình ảnh.
Thông tin nguồn, checksum và attribution nằm trong
[`source_manifest.json`](source_manifest.json).

Tải và xác minh bản chính thức:

```powershell
python scripts/download_advanced_source.py
```

PDF được lưu tại `advanced/source/vietnam-2035.pdf` và bị Git ignore. Người chấm
có thể tải lại đúng bản từ URL chính thức; không cần repository bên ngoài.
