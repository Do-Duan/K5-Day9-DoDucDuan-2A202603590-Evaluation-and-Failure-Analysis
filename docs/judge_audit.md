# Judge audit

Chạy replay công khai: `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5` và `python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5`. PASS là lớp âm; FAIL là lớp dương (cần phát hiện lỗi). FLOORS: κ≥0.6, precision≥0.8, recall≥0.7.

| Tiêu chí | n | κ | Precision | Recall | Ma trận (TP/FP/FN/TN) | Tỉ lệ FAIL quan sát → hiệu chỉnh | Đạt FLOORS? | Quyết định |
|---|---:|---:|---:|---:|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | 24 / 4 / 6 / 66 | 0.280 → 0.300 | Có | Có thể dùng làm grader mềm về tone; không dùng thay kiểm tra nghiệp vụ/safety |
| helpful | 100 | 0.375 | 1.000 | 0.300 | 9 / 0 / 21 / 70 | 0.090 → 0.300 | Không | Loại khỏi gate; recall thấp bỏ sót 21/30 lỗi người gắn nhãn |

Tỉ lệ hiệu chỉnh dùng Rogan–Gladen với sensitivity=recall và specificity=TN/(TN+FP). Đây là ước lượng trên bộ replay công khai; không thay thế mẫu đánh giá đại diện.

## ≥5 case audit thủ công

| # | Case | Judge | Người | Ai đúng? | Hành động với rubric |
|---:|---|---|---|---|---|
| 1 | H-008: “Em đã hoàn tiền… nha” | PASS | FAIL | Người | Nêu rõ cấm xưng “em” với khách và khẩu ngữ “nha”; cần rubric có ví dụ xưng hô/đăng ký |
| 2 | H-017: “bạn ơi… rồi nha” | PASS | FAIL | Người | Chấm riêng đại từ thân mật và “nha”, không để lời mở đầu lịch sự che lỗi |
| 3 | H-029: “không cần nhắn thêm” | PASS | FAIL | Người | Bổ sung tiêu chí không ra lệnh/không ngăn khách liên hệ; cảnh báo cụm mệnh lệnh |
| 4 | H-042: báo hoàn 120.000đ, ngắn gọn | FAIL | PASS | Người | Bỏ yêu cầu xin lỗi như tiêu chí bắt buộc; câu ngắn đủ thông tin vẫn đạt |
| 5 | H-051: dùng từ “refund” nhưng đủ nội dung | FAIL | PASS | Người | Chấp nhận từ vay mượn nếu đúng nghĩa và giọng lịch sự; không phạt chỉ vì tiếng Anh |
| 6 | HL-015: báo 55.000đ sai ledger | PASS | FAIL | Người | Tiền phải so với ledger bằng code, không giao cho judge văn phong/helpfulness |
| 7 | HL-028: báo 50.000đ sai ledger | PASS | FAIL | Người | Thêm quy tắc nhất quán số tiền và tách factual correctness khỏi helpfulness |
| 8 | HL-087: báo 60.000đ sai số thực tế | PASS | FAIL | Người | Chuyển kiểm tra số tiền sang grader deterministic |

## Kết luận

- `tone_ok` đạt sàn trên replay này. Chỉ sử dụng cho đánh giá tone, có giám sát; vẫn cần kiểm tra các lát cắt nhân xưng, khẩu ngữ, câu mệnh lệnh và câu ngắn.
- `helpful` không đạt: precision cao nhưng recall 0.30 và κ=0.375; không đủ tin cậy làm cổng merge. Bất đồng chủ yếu do judge bỏ qua câu trả lời sai tiền hoặc bỏ sót lỗi nội dung.
- Tiền, approval, secret và trạng thái phải do code grader kiểm tra. Không để judge ngôn ngữ quyết định tính đúng của giao dịch.
- Giới hạn: đây là judge replay trên 100 dòng công khai, không phải đánh giá mù/held-out mới; hiệu chỉnh tỷ lệ lỗi chỉ tham khảo trong cùng phân phối.
