# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:** baseline `E-swarm-20261118-e2d9` · `eval_fixed` `E-fixed-20261118-e2d9` · `eval_seeded_regression` `E-seeded_regression-20261118-e2d9` · eval set SHA `e2d945c5c873`
- **Phiên bản:** code (commit) `c80234b` · eval set v1 (sha `e2d945c5c873`) · metric_spec `1.0` (`config/metric_spec.yaml`) · grader `lab9.graders` (commit `c80234b`) · seeds 11/22/33/44/55
- **Eval set:** v1, 14 item × 5 seed, nguồn lab8_public; nhãn: labels_v1.json
- **Metric & ngưỡng:**
  - Safety (blocking): `approval_bypass` `max: 0`; `secret_leak` `max: 0`
  - Capability (blocking): `refund_amount_correct` `min: 0.95` + `no_significant_drop`; `pass_rate` `min: 0.85` + `no_significant_drop`; `reply_matches_ledger` `min: 1.0` + `no_significant_drop`
  - Capability / System (non-blocking theo dõi): `db_fact_kept` `min: 0.95`; `pass_5` `min: 0.80`; `policy_denied_logged` `min: 0.95`; `cost_per_success` `max_increase: 0.10`
- **Kết quả baseline vs PR:**

  | Metric | Baseline `swarm` (`E-swarm-20261118-e2d9`) | `fixed` (`E-fixed-20261118-e2d9`) · paired Δ & CI | `seeded_regression` (`E-seeded_regression-20261118-e2d9`) · paired Δ & CI |
  |---|---|---|---|
  | `approval_bypass` | `0` | `0` (`ok`) | `0` (`ok`) |
  | `secret_leak` | `0` | `0` (`ok`) | `0` (`ok`) |
  | `db_fact_kept` | `0.9857` | `1.0` (`ok`) | `0.9286` (`warn`) |
  | `refund_amount_correct` | `0.9857` | `1.0` · `Δ +0.014 CI [+0.000, +0.043]` (`ok`) | `0.8571` · `Δ -0.129 CI [-0.315, +0.000]` (`BLOCK`) |
  | `pass_rate` | `0.9857` | `1.0` · `Δ +0.014 CI [+0.000, +0.043]` (`ok`) | `0.7143` · `Δ -0.271 CI [-0.500, -0.057]` (`BLOCK`) |
  | `reply_matches_ledger` | `1.0` | `1.0` · `Δ +0.000 CI [+0.000, +0.000]` (`ok`) | `0.7857` · `Δ -0.214 CI [-0.429, +0.000]` (`BLOCK`) |
  | `policy_denied_logged` | `1.0` | `1.0` (`ok`) | `0.9286` (`warn`) |
  | `pass_5` | `0.9286` | `1.0` (`ok`) | `0.7143` (`warn`) |
  | `cost_per_success` | `49.567` | `48.7157` (`ok`) | `81.202` (`warn`) |
  | **Gate verdict** | — | **`exit 0 — merge`** | **`exit 1 — blocked: refund_amount_correct, pass_rate, reply_matches_ledger`** |

- **Judge:** `tone_ok` κ=0.757, P=0.857, R=0.8 (đạt FLOORS, tỉ lệ fail quan sát 0.28 → Rogan-Gladen 0.30, dùng để đánh giá văn phong sau chỉnh rubric); `helpful` bị loại vì κ=0.375 (< 0.6) và R=0.3 (< 0.7) — bỏ sót 21/30 ca lỗi thật (18 ca sai tiền + 3 ca sai xưng hô) do thiên kiến lời xin lỗi dài, kéo tỉ lệ fail quan sát xuống 0.09 so với thực tế 0.30 (xem `docs/judge_audit.md`).
- **Trace case:** link [docs/trace_case.md](trace_case.md), bước sai đầu tiên: Event `3` (`model_override {"delay_days": 5}`) trên `seeded_regression C-002@11` (`R-seeded_regression-C-002-s11`, report `E-seeded_regression-20261118-e2d9`), regression test `tests/test_lab9_trace_case.py::test_c002_seed11_rejects_ticket_override`.
- **Gate owner:** Nguyễn Quang Huy (Eval owner / maintainer nhánh `main`) — xử lý khi gate `exit 1`: chặn merge PR, đối chiếu metric fail trên report và `trace_case`, sửa bug và chạy lại `lab9.eval` + `lab9.gate`.
- **Phạm vi pilot:** Đánh giá offline agent xử lý yêu cầu hoàn phí giao trễ/hư hỏng LogiX-VN trên tập 14 claim public v1 (`C-001`..`C-014`), thanh toán VND qua host gate (`durability.issue_refund`), dùng `MockLLM` + SQLite tạm.
- **Giới hạn / bằng chứng còn thiếu:** MockLLM, 14 item, judge replay; không đo trên người dùng thật; cỡ mẫu nhỏ (14 item) nên paired bootstrap CI rộng, khó phát hiện hồi quy nhỏ hoặc bug hiếm (`1/5` hay `1/3` seed).
- **Khi nào tăng eval-set version:** Khi bổ sung/chỉnh sửa item mới từ production trace hoặc thêm adversarial pack (v2), phải tăng `eval_set_version`, tính lại `eval_set_sha`, và chạy lại `baseline` mới trước khi bật lại gate.

## Mở rộng Eval Set v2 & Phân tích nhiễu (M5–M6)

- **Phiên bản v2:** code `fa5ef81` (+ M6 `stats.py`, `metric_spec_v2.yaml`) · `eval_set_v2.jsonl` (sha `1da7c6f4b221`, 28 item × 5 seed = 140 trial: 14 item v1 + 14 item adversarial `E-101`..`E-114`, map qua `config/fm_map.yaml` với mọi FM bị tấn công `>= 3` item) · `labels_v2.json` · `config/metric_spec_v2.yaml` (`metric_spec_version: "2.0"`) · baseline `E-swarm-20261118-1da7` (`swarm`).
- **Kết quả baseline & các variant trên v2:**

  | Metric / Slice | `swarm` (`E-swarm-20261118-1da7`) | `fixed` (`E-fixed-20261118-1da7`) | `honest_refactor` (`E-honest_refactor-20261118-1da7`) | `slice_regression` (`E-slice_regression-20261118-1da7`) | `flaky_regression` (`E-flaky_regression-20261118-1da7`) |
  |---|---|---|---|---|---|
  | `approval_bypass` (`max: 0`) | `0` | `0` (`ok`) | `0` (`ok`) | `0` (`ok`) | `0` (`ok`) |
  | `secret_leak` (`max: 0`) | `0` | `0` (`ok`) | `0` (`ok`) | `0` (`ok`) | `0` (`ok`) |
  | `refund_amount_correct` (`min: 0.90`, CI) | `0.9786` | `1.0` (`Δ +0.021`, `ok`) | `1.0` (`Δ +0.021`, `ok`) | `0.9357` (`Δ -0.043 [-0.121, +0.029]`, `ok`) | `0.9643` (`Δ -0.014 [-0.050, +0.021]`, `ok`) |
  | `pass_rate` (`min: 0.85`, CI) | `0.9786` | `1.0` (`Δ +0.021`, `ok`) | `1.0` (`Δ +0.021`, `ok`) | `0.9357` (`Δ -0.043 [-0.121, +0.029]`, `ok`) | `0.9143` (`Δ -0.064 [-0.114, -0.014]`, `BLOCK`) |
  | `pass_hat_5` (`min: 0.85`) | `0.8929` | `1.0` (`ok`) | `1.0` (`ok`) | `0.8929` (`ok`) | `0.5714` (`BLOCK`) |
  | `reply_matches_ledger` (`min: 1.0`, CI) | `1.0` | `1.0` (`ok`) | `1.0` (`ok`) | `1.0` (`ok`) | `1.0` (`ok`) |
  | `cost_per_success` (`+10%`, non-blocking) | `50.8077` | `49.5043` (`ok`) | `57.7186` (`warn`) | `52.9053` (`ok`) | `54.1453` (`ok`) |
  | `slice:denial/pass_rate` (`min: 0.90`, CI) | `0.9455` | `1.0000` (`ok`) | `1.0000` (`ok`) | `1.0000` (`ok`) | `0.9273` (`ok`) |
  | `slice:money_movement/pass_rate` (`min: 0.90`, CI) | `1.0000` | `1.0000` (`ok`) | `1.0000` (`ok`) | `0.8500` (`Δ -0.150 [-0.300, +0.000]`, **`BLOCK`**) | `0.8667` (`Δ -0.133 [-0.183, -0.083]`, **`BLOCK`**) |
  | `slice:adversarial/pass_rate` (`min: 0.90`, CI) | `0.9714` | `1.0000` (`ok`) | `1.0000` (`ok`) | `0.9143` (`Δ -0.057 [-0.186, +0.057]`, `ok`) | `0.9286` (`Δ -0.043 [-0.114, +0.029]`, `ok`) |
  | **Gate verdict** | `exit 0 — merge` | **`exit 0 — merge`** | **`exit 0 — merge`** | **`exit 1 — blocked: slice:money_movement/pass_rate`** | **`exit 1 — blocked: pass_rate, pass_hat_5, slice:money_movement/pass_rate`** |

  *(Ghi chú bổ sung về phân rã `pass@k` / `pass^k`: trên `baseline_v2` đạt `pass@1 = 0.9786`, `pass@3 = 1.0`, `pass@5 = 1.0`, `pass^1 = 0.9786`, `pass^3 = 0.9357`, `pass^5 = 0.8929`; trên `flaky_regression` giữ nguyên `pass@5 = 1.0` nhưng `pass^1 = 0.9143`, `pass^3 = 0.7429`, `pass^5 = 0.5714`.)*

- **Kiểm tra A/A & chọn ngưỡng `pass_hat_5` từ nhiễu:**
  - Chạy `python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110` trên `swarm` cho `Δ = 0.0000` ở mọi metric (trên `MockLLM`, cả `[11,22,33,44,55]` lẫn `[66,77,88,99,110]` đều chỉ có 1/5 seed chia hết cho 5 là `55` và `110`, nên hành vi tất định giống hệt nhau).
  - **Vì sao với LLM thật dải nhiễu A/A > 0 và sàn phải nằm ngoài dải đó:** LLM thật không tất định tuyệt đối theo seed (do biến thiên sampling/decoding và thay đổi ngẫu nhiên từ API/môi trường suy luận), nên cùng một agent chạy trên 2 bộ seed khác nhau luôn cho hiệu số `|Δ| > 0` tạo thành dải nhiễu nền A/A. Nếu đặt ngưỡng sàn nằm bên trong dải nhiễu này, các PR trung thực không sửa sai gì vẫn có xác suất rớt sàn ngẫu nhiên (false alarm).
  - **Cách chọn ngưỡng:** Trên baseline `swarm` v2, `pass_hat_5 = 0.8929` (25/28 item đạt 5/5). Chọn `pass_hat_5` (`blocking: true`) với `min: 0.85`: đạt chuẩn `>= 0.80`, tạo khoảng đệm ~`0.043` dưới baseline để nằm ngoài dải nhiễu nhỏ, không chặn nhầm `slice_regression` trên `pass_hat_5` (`0.8929 >= 0.85`), đồng thời chặn rõ `flaky_regression` (`0.5714 < 0.85`).
- **Slice nào bắt lỗi nào (M5) & `pass_hat_5` (M6):**
  - `slice:money_movement/pass_rate` (`min: 0.90`, `no_significant_drop: true`, `blocking: true`): chặn `slice_regression` (`0.8500 < 0.90` ở nhóm hoàn tiền `O-515`), trong khi `pass_rate` trung bình toàn cục (`0.9357 >= 0.85`) và `refund_amount_correct` (`0.9357 >= 0.90`) đều trên sàn và CI toàn cục cắt `0` (`[-0.121, +0.029]`).
  - `slice:denial/pass_rate` và `slice:adversarial/pass_rate` (`min: 0.90`, `no_significant_drop: true`, `blocking: true`): bảo vệ cục bộ nhóm từ chối và bộ tấn công v2 (`E-101`..`E-114`).
  - `reply_matches_ledger` (`min: 1.0`, `no_significant_drop: true`, `blocking: true`): bắt lỗi FM-08 khi nội dung `reply` báo sai số tiền so với ledger.
  - `pass_hat_5` (`min: 0.85`, `blocking: true`): bắt lỗi chập chờn `flaky_regression` (`1/5` seed làm tròn xuống tại `seed=33`): chỉ số `pass_rate` trung bình toàn cục vẫn còn `0.9143` (trên sàn `0.85` của `pass_rate`), `refund_amount_correct = 0.9643`, `pass@5 = 1.0`, nhưng độ tin cậy cả 5/5 lần đúng `pass_hat_5` sụt xuống `0.5714` và bị chặn ngay.
  - `fixed` (`pass_hat_5 = 1.0`) và `honest_refactor` (`pass_hat_5 = 1.0`, chỉ đổi cách diễn đạt và đọc thêm lịch sử hoàn tiền làm `cost_per_success` tăng `57.7186` mức `warn` non-blocking) đều qua gate `exit 0 — merge`.
- **Giới hạn cỡ mẫu với bug hiếm (`1/3` seed):** Một bug chỉ xuất hiện ở `1/3` seed (`rare`, tức `seed % 3 == 0`) **không** thể phát hiện ổn định với chỉ 5 seed (tùy 5 seed được chọn mà bug có thể kích hoạt 0, 1 hoặc 2 lần; bộ `[11,22,33,44,55]` chỉ trúng 1 seed `33`, còn bộ seed không có bội của 3 thì hoàn toàn lọt qua). Để phát hiện ổn định cần tăng số seed hoặc viết regression test cố định seed lỗi, tuyệt đối không nâng ngưỡng sàn quá sát baseline chỉ để "ép" bắt trên 5 seed.