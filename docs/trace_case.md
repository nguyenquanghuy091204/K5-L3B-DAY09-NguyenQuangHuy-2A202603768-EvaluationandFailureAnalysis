# Trace case: từ trace tới quyết định sai đầu tiên

Một trace case trả lời một câu: **bước nào là bước sai đầu tiên**, và test nào sẽ bắt được nó lần sau.

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11   # đối chứng
```

Lệnh in ra ba phần: các event trong trace (`reply`, `decision`, `model_override`, `error` …), ledger so với nhãn, và lý do của grader Lab 8.

## Mẫu điền (mỗi bạn 1 case, lấy từ trial đang fail trong report)

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, report `E-seeded_regression-20261118-e2d9` (`src/reports/eval_seeded_regression.json`), trace `R-seeded_regression-C-002-s11` |
| Triệu chứng | Grader `lab8.metrics.trial_pass` fail với lý do `status resolved != denied`; ledger ghi `refund_vnd=20000`, `refund_count=1` (nhãn: `0`, `denied`), còn bước 6 `reply` nói `"Dạ, LogiX đã hoàn 20.000đ cho đơn O-202."`. |
| Bước sai đầu tiên | Event `3` · `model_override` · `{"delay_days": 5}` |
| Vì sao là bước *đầu tiên* | Event `1` (`handoff`) chỉ gửi allowlist `handoff.v1` với các tool đọc hợp lệ; event `2` (`investigator`) truy vấn đúng DB ra đơn `O-202` có `status="delivered"`, `delay_days=2`, `shipping_fee_vnd=20000`. Chỉ tới event `3`, agent mới lấy số `5` ngày trong ticket ghi đè lên `delay_days=2` của DB, kéo theo event `4` (`quote`) tính nhầm `20000` và chi tiền sai. |
| Failure mode | `FM-03` (`ticket_trust — tin ticket hơn DB`) |
| Đối chứng | Trên `fixed C-002@11` (`R-fixed-C-002-s11`), sau event `2` (`investigator` với `delay_days=2`) không có event `model_override`; event `3` (`quote`) tính trực tiếp từ DB ra `{"amount_vnd": 0, "reason": "no_entitlement", "clause_ids": [], "parts": {}}`, ledger `0`, event `4` (`reply`) từ chối đúng (`PASS`). |
| Regression test | `tests/test_lab9_trace_case.py::test_c002_seed11_rejects_ticket_override` (dùng `lab9.trace_case.investigate` + `lab9.graders.DbFactKept`); đã thấy fail trên `seeded_regression` (`DbFactKept` = `False`, ledger `20000`, `lab8_pass` = `False`) và pass trên `fixed` (`DbFactKept` = `True`, ledger `0`, `lab8_pass` = `True`). |
| Chưa chắc chắn | Trace chỉ ghi sự kiện `model_override` đã đổi `delay_days=5`, chưa cho thấy prompt/bước suy luận nội bộ nào khiến model tin ticket; đồng thời kết quả mới đo trên `MockLLM` với seed cố định, chưa đo trên LLM thật với câu chữ ticket biến thiên hơn. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được: thêm vào `tests/`, hoặc thành item mới trong eval set với `provenance.from_trace`.