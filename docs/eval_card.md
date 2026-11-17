# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:**
- **Phiên bản:** code (commit) … · eval set v1 (sha …) · metric_spec … · grader (commit) … · seeds 11/22/33/44/55
- **Eval set:** v1, 14 item × 5 seed, nguồn lab8_public; nhãn: labels_v1.json
- **Metric & ngưỡng:** (trích metric_spec.yaml)
- **Kết quả baseline vs PR:** bảng + paired CI
- **Judge:** tone_ok κ=…, P=…, R=…; helpful bị loại vì …
- **Trace case:** link `docs/trace_case.md`, bước sai đầu tiên, regression test
- **Gate owner:** ai xử lý khi gate exit 1
- **Phạm vi pilot:** …
- **Giới hạn / bằng chứng còn thiếu:** MockLLM, 14 item, judge replay; không đo trên người dùng thật
- **Khi nào tăng eval-set version:** …

## M5–M7 (implementation status)

- Eval set v2: 28 items, 28 labels; `python -m lab9.evalset --v2` reports 0 problems. Attack map is in `src/config/fm_map.yaml`; every attacked FM has at least 3 items after combining v1 and v2.
- Blocking slices: `money_movement`, `adversarial`, and `denial` use `pass_rate` min 0.80 plus paired no-significant-drop check. The slice gate reports its per-slice value and CI.
- Integrity checks reject non-finite metrics, missing/None graded values, evaluator failures, dropped/duplicated rows, changed item-seed sets, relabeled slices, and looser metric/slice thresholds under the same eval-set version.
- `pass_at_k` and `pass_hat_k` are implemented. `pass_hat_5` floor is 0.80; the required A/A empirical comparison could not be completed because a 140-trial v2 eval did not finish after several minutes. MockLLM is deterministic by seed, but record measured A/A output before treating this floor as empirically calibrated.
- Public trap replay using the existing v1 baseline blocked all four public traps (NaN/evaluator errors, dropped rows, cherry-picked seeds, loosened spec). v2 trap scorecard remains unverified until a valid v2 baseline/report exists.

Known limitation: baseline v2 generation (python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json) ran for several minutes without output and was stopped. No baseline v2 or mutation scorecard was generated. Do not claim end-to-end v2 gate validation until that run completes.
