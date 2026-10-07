# Hướng dẫn Import Dữ liệu Database (Migration)

File `data_migration.sql` chứa toàn bộ dữ liệu (cùng với cấu trúc bảng) được xuất từ database `triage_db` ở môi trường local. Vì bạn đã setup database từ trước thông qua Docker, bạn có thể thực hiện theo các bước sau để cập nhật database của bạn với dữ liệu này.

## Yêu cầu

- Đã cài đặt Docker và Docker Compose.  
- Các container của project (đặc biệt là `triage_postgres`) đang chạy.

## Các bước thực hiện

### 1\. Đảm bảo container Database đang chạy

Hãy mở terminal tại thư mục gốc của project (nơi chứa file `docker-compose.yml`) và đảm bảo container `postgres` đang hoạt động:

docker ps | grep triage\_postgres

Nếu container chưa chạy, hãy khởi động bằng lệnh:

docker compose up \-d postgres

### 2\. Copy file SQL vào trong container

Chạy lệnh sau để copy file `data_migration.sql` vào trong container postgres. Lưu ý, bạn cần chạy lệnh này ở thư mục chứa file `data_migration.sql`:

docker cp data\_migration.sql triage\_postgres:/tmp/data\_migration.sql

### 3\. Thực thi file SQL để import dữ liệu

Sử dụng công cụ `psql` bên trong container để thực thi file SQL vừa copy. Lưu ý rằng lệnh này sẽ ghi đè và thay thế cấu trúc cũng như dữ liệu hiện có bằng dữ liệu mới từ file:

docker exec \-it triage\_postgres psql \-U triage\_user \-d triage\_db \-f /tmp/data\_migration.sql

### 4\. Xóa file dump trong container sau khi import xong (Tùy chọn)

docker exec triage\_postgres rm /tmp/data\_migration.sql

## Khắc phục sự cố (Troubleshooting)

- Nếu terminal hiển thị một số cảnh báo như "role does not exist" hoặc "extension vector already exists", bạn có thể an tâm bỏ qua chúng. Quá trình import dữ liệu các bảng chính vẫn sẽ diễn ra thành công.  
- Nếu bạn muốn kiểm tra dữ liệu đã vào hay chưa, có thể truy cập vào database:  
    
  docker exec \-it triage\_postgres psql \-U triage\_user \-d triage\_db  
    
  Sau đó gõ lệnh `\dt` để xem danh sách các bảng.

