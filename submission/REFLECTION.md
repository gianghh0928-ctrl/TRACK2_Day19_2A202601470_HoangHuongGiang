# Reflection — Lab 19

**Tên:** _Hoàng Hương Giang_
**Cohort:** _<A20-K2>_
**Path đã chạy:** _<lite>_

---

## Câu hỏi (≤ 200 chữ)

> Trên golden set 50 queries, mode nào thắng ở loại query nào (`exact` /
> `paraphrase` / `mixed`), và tại sao? Khi nào bạn **không** dùng hybrid
> (i.e. khi nào pure BM25 hoặc pure vector là lựa chọn đúng)?

Trên golden set 50 queries, exact thắng ở BM25 hoặc Hybrid (số điểm gần bằng nhau 96.7%), mixed thắng ở Hybrid (100.0%) còn paraphrase lại giảm chung do mô hình tiếng Anh. 
Không nên dùng Hybrid khi:
- Yêu cầu độ trễ thấp hoặc dữ liệu tra cứu dạng định danh chính xác. Trong trường hợp này nên chọn Pure BM25 vì chạy nhanh, không cần nạp mô hình AI nặng vào RAM/CPU, khi cần chính xác (số điện thoại, mã đơn hàng, ID...) thì BM25 sẽ tốt hơn. 
- Khi tìm kiếm đa ngôn ngữ hoặc câu hỏi không có từ khóa, trừu tượng thì nên dùng Pure Vector. Ví dụ người dùng hỏi bằng tiếng Việt nhưng tài liệu là tiếng Anh. 

---

## Điều ngạc nhiên nhất khi làm lab này

Thuật toán RRF tuy cài đặt đơn giản nhưng mang lại hiệu quả kết hợp rất cao (đạt 100% trên `mixed` queries) và cơ chế Point-In-Time join của Feast giúp ngăn ngừa triệt để rò rỉ dữ liệu (data leakage) trong huấn luyện mô hình.

---

## Bonus challenge

- [x] Đã làm bonus (xem `bonus/`)
- [ ] Pair work với: _<tên đồng đội nếu có>_
