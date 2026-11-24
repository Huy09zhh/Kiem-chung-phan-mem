# Công cụ sinh collection BVA Account & Auth

Collection `Green Shop - Account & Auth - BVA` (mỗi case 1 request, 56 case, 7 giá trị mỗi biến) được sinh từ các file trong thư mục này, không viết tay từng request.

| File | Việc làm |
|---|---|
| `lib.js` | Thư viện dùng chung (biến collection `bva_lib`): sinh dữ liệu theo độ dài, chuẩn bị tài khoản, kiểm chứng sau request |
| `gen.py` | Đọc danh sách 8 biến x 7 giá trị, sinh lại `Green Shop - Account & Auth - BVA.postman_collection.json` |
| `gen_yaml.py` | Sinh lại thư mục `collections/Green Shop - Account & Auth - BVA/` (định dạng YAML của Postman) từ file JSON |

## Chạy lại

```
cd postman
python bva_generator/gen.py        # ghi đè file JSON
python bva_generator/gen_yaml.py   # ghi đè thư mục YAML (cần PyYAML)
```

Sau đó import file JSON lên Postman (Replace). Muốn đổi dữ liệu thử thì sửa `lib.js` rồi chạy lại `gen.py`.

## Quy tắc đặt tên dữ liệu thử

`<tiền tố case>_<mã case>_<mã lượt chạy>_<đệm 0123456789>`, ví dụ `regusr_L076_G7L12T20Z26_0123…`. Mã lượt chạy gồm các chữ cái tăng dần, mỗi chữ theo sau là số thứ tự của chữ đó (a1b2c3d4). Số chữ cái chỉnh bằng biến collection `bva_code_letters` (mặc định 4).

## Khi chạy

- Folder 08 cần tài khoản superuser đọc hộp thư dev: mặc định lấy từ biến `bva_mailbox_admin_user` / `bva_mailbox_admin_password` (admin test cục bộ) và server chạy với `EMAIL_HOST_USER` rỗng (email lưu vào thư mục, không gửi thật).
- Server giới hạn 20 lần đăng nhập sai và 10 yêu cầu đặt lại mật khẩu mỗi IP trong 15 phút. Mỗi lần Run all dùng khoảng 16 lần đăng nhập sai, nên khởi động lại server trước mỗi lần chạy một collection.
