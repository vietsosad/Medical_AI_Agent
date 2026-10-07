"""Các nguồn dữ liệu cơ sở y tế cho @[src/services/nearby_facilities.py].

Mỗi provider chỉ dịch định dạng riêng của nguồn nó phụ trách về
``FacilityCandidate``. Việc tính khoảng cách, sắp xếp, cắt danh sách, dựng deep
link và chọn nguồn nào phục vụ lần tra cứu nào đều nằm ở module điều phối, không
nằm ở đây -- nhờ vậy thêm một nguồn mới không kéo theo thay đổi nào ở tầng API
hay tầng giao diện.
"""
