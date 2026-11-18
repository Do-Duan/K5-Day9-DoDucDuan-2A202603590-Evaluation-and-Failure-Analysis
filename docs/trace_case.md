# Trace case: seeded_regression C-007@11

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-007@11`; replay bằng `python -m lab9.trace_case --shape seeded_regression --claim C-007 --seed 11`. |
| Triệu chứng | Lab 8 grader: `FAIL (status resolved != denied)`. Snapshot ledger ghi `refund_vnd=0`, `refund_count=0`; nhãn status `denied`. |
| Bước sai đầu tiên | Event 5 (`reply`): shape trả “Dạ, LogiX đã hoàn 35.000đ cho đơn O-909.” dù host không ghi refund. Trước đó event 3 (`quote`) là 35.000đ; host trả từ chối do approval/policy tại bước ghi tiền. |
| Failure mode | FM-02 `ignore_denied`; đồng thời reply lệch ledger là FM-08. |
| Đối chứng | `fixed C-007@11` phải báo denied và không có ledger row; xác nhận bằng lệnh trace đối chứng sau khi chạy. |
| Regression assertion | `ApprovalBypass` không thể phát hiện trường hợp này vì ledger không ghi tiền; `TrialPass` bắt status sai. `ReplyAmountMatchesLedger` bắt reply có số tiền trong khi ledger là 0. Unit tests grader hiện tại qua; chưa có test riêng cho variant C-007. |
| Chưa chắc chắn | Trace chứng minh reply/status sai và không có refund; không kết luận được nguyên nhân nội bộ của MockLLM ngoài nhánh `ignore_denied` đang bật trong variant. |

Đọc ledger trước reply: không có khoản hoàn nào, nhưng reply lại khẳng định đã hoàn 35.000đ. Đây là regression case để giữ lại cho gate.
