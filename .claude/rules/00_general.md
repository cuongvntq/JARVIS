# Rules — General (Áp dụng toàn dự án)

## Phạm vi chỉnh sửa

- Chỉ chỉnh sửa các file có liên quan trực tiếp đến nhiệm vụ được giao.
- Không đổi tên file không liên quan.
- Không di chuyển thư mục khi không được yêu cầu rõ ràng.
- Không cập nhật version package khi không được yêu cầu.
- Không viết lại code đang hoạt động tốt.

## Trước khi viết code mới

- Tìm kiếm implementation hiện có trong codebase trước — dùng Grep/Glob để kiểm tra.
- Tái dùng pattern đang có (error handler, DB query, API response shape, ...).
- Không tạo abstraction mới trừ khi logic đó được dùng lại ≥3 lần.
- Prefer chỉnh sửa file hiện có hơn tạo file mới.

## Khi không chắc

- Hỏi trước khi implement — đừng tự đoán requirement.
- Không tự bịa API endpoint không có trong docs/02.
- Không tự giả định DB schema — kiểm tra docs/01 hoặc file migration hiện có.
- Nếu có 2 cách implement, hỏi user chọn thay vì tự quyết định lớn.

## Tuyệt đối không

- Không đổi tên file/folder không liên quan đến task.
- Không di chuyển thư mục khi không được yêu cầu.
- Không bump version package (pyproject.toml, package.json) khi không được yêu cầu.
- Không refactor code đang chạy tốt trong khi đang fix bug khác.
- Không thêm dependency mới mà không hỏi trước.
