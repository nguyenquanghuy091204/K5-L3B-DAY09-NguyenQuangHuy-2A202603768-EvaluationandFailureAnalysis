# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.8 | Có (`κ=0.757 ≥ 0.6`, `P=0.857 ≥ 0.8`, `R=0.8 ≥ 0.7`) | dùng |
| helpful | 100 | 0.375 | 1.0 | 0.3 | Không (`R=0.3 < 0.7`, `κ=0.375 < 0.6`) | loại |

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | `tone_ok / H-008`: `"Em đã hoàn tiền cho anh rồi nha, anh check giúp em."` | PASS | FAIL | Người đúng | Xưng `"em"` + `"nha"` quá suồng sã; judge hiểu nhầm là thân thiện. **Sửa rubric:** cấm đại từ suồng sã (`em`/`nha`/`bạn`), bắt buộc xưng `LogiX` – `anh/chị`. |
| 2 | `tone_ok / H-029`: `"Dạ, vui lòng chờ. Hệ thống đang xử lý, không cần nhắn thêm."` | PASS | FAIL | Người đúng | Có từ `"Dạ, vui lòng"` ở đầu nhưng phần sau mang giọng ra lệnh/đuổi khách (`"không cần nhắn thêm"`). **Sửa rubric:** đánh `FAIL` mọi câu mang hàm ý cấm/chặn khách phản hồi bất kể có `"Dạ"` ở đầu. |
| 3 | `tone_ok / H-042`: `"Dạ, đơn O-808 đã hoàn 120.000đ. Tiền về trong 3–5 ngày ạ."` | FAIL | PASS | Người đúng | Ngắn gọn, lịch sự, đủ ý; judge phạt nhầm vì `"thiếu xin lỗi"`. **Sửa rubric:** câu xác nhận đã hoàn tiền thành công không bắt buộc phải có lời xin lỗi. |
| 4 | `tone_ok / H-051`: `"Dạ, LogiX đã refund 90.000đ cho đơn O-202 ạ."` | FAIL | PASS | Người đúng | Chính sách CSKH LogiX cho phép dùng từ `"refund"`; judge phạt nhầm vì xen tiếng Anh. **Sửa rubric:** liệt kê rõ các thuật ngữ tiếng Anh được phép (như `refund`). |
| 5 | `tone_ok / H-070`: `"Dạ, LogiX đã hoàn 90.000đ cho đơn O-909 ạ 😂😂"` | PASS | FAIL | Người đúng | Dùng emoji cười cợt trong bối cảnh xử lý khiếu nại; judge bỏ qua. **Sửa rubric:** cấm emoji không trang trọng (`😂`, `🤣`...) trong phản hồi CSKH. |
| 6 | `tone_ok / H-081`: `"Dạ, đơn O-107 chưa đủ điều kiện hoàn theo chính sách hiện hành ạ."` | FAIL | PASS | Judge đúng (nhãn người sai) | Người gán nhãn đọc nhầm ticket dẫn tới nhãn ground truth bị lệch. **Hành động:** rà soát và hiệu chỉnh lại nhãn human của `H-081` trong bộ audit trước vòng calibrate tiếp theo. |
| 7 | `helpful / HL-015`: `"Dạ, LogiX đã hoàn 55.000đ cho đơn O-112 ạ."` | PASS | FAIL | Người đúng | Reply lịch sự nhưng báo sai số tiền (`55.000đ` so với ledger `40.000đ`). **Sửa rubric & kiến trúc:** không dùng judge văn phong để chấm độ đúng thông tin tài chính; bắt buộc tách sang code grader đối chiếu ledger (FM-08). |
| 8 | `helpful / HL-016`: `"Dạ, LogiX thành thật xin lỗi anh/chị... LogiX đã hoàn 55.000đ cho đơn O-404..."` | PASS | FAIL | Người đúng | Sai tiền (`55.000đ` vs ledger `35.000đ`) nhưng mở/kết câu xin lỗi rất dài nên judge bị thiên kiến dài/lịch sự đánh `PASS`. **Sửa rubric:** bổ sung cảnh báo verbosity/politeness bias và loại bỏ tiêu chí tiền khỏi LLM judge. |
| 9 | `helpful / HL-047`: `"Ok bạn, đơn O-515 xử lý rồi nhé."` | PASS | FAIL | Người đúng | Sai xưng hô (`"Ok bạn"` / `"nhé"`) và thiếu thông tin số tiền xử lý; judge vẫn cho `PASS`. **Sửa rubric:** bổ sung ví dụ đối chứng (`few-shot`) các mẫu câu ngắn cộc lốc/sai xưng hô là `FAIL`. |

## Kết luận
- **Tiêu chí bị loại (`helpful`) và lý do:** Không được dùng `helpful` làm gate vì không đạt ngưỡng tối thiểu (`R = 0.3 < 0.7`, `κ = 0.375 < 0.6`). Trên ma trận nhầm lẫn (`tp=9, fp=0, fn=21, tn=70`), dù `Precision = 1.0`, judge bỏ sót tới **21/30 ca lỗi thật (`FN = 21`)** — chủ yếu là các ca báo sai số tiền so với ledger (18 ca) và sai xưng hô (3 ca) nhưng viết lời xin lỗi dài, lịch sự. Vì Recall quá thấp, tỉ lệ fail quan sát của `helpful` chỉ là `0.09`, làm ẩn hơn 2/3 lỗi thật so với tỉ lệ hiệu chỉnh Rogan-Gladen thực tế là `0.30`. Ngoài ra, việc kiểm tra số tiền hoàn phải do **code grader** đối chiếu ledger thực hiện, không giao cho LLM judge.
- **Tiêu chí được giữ (`tone_ok`):** Đạt cả 3 ngưỡng FLOORS (`tp=24, fp=4, fn=6, tn=66`; `κ = 0.757`, `P = 0.857`, `R = 0.8`; tỉ lệ fail quan sát `0.28` → Rogan-Gladen hiệu chỉnh `0.30`). Có thể dùng `tone_ok` làm judge tham khảo/kiểm soát sau khi áp dụng các chỉnh sửa rubric ở trên.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật.