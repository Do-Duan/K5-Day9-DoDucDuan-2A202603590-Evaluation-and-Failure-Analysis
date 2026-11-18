# Eval card — LogiX-VN refund agent

## V1 baseline / PR comparison

- Baseline run: `E-swarm-20261117-b6a9`; eval-set SHA `b6a97288bc5e`; 14 items × 5 seeds; MockLLM.
- Metric spec v1; seeds 11/22/33/44/55. Judge replay: tone κ=0.757, P=0.857, R=0.800 (eligible for tone-only grading); helpful κ=0.375, P=1.000, R=0.300 (exclude from gate).
- Fixed run: `E-fixed-20261118-b6a9`; pass_rate 1.000, refund_amount_correct 1.000, reply_amount_matches_ledger 0.500 in the stored report. The stored gate blocks this report on FM-08; regenerate after the grader change that treats replies with no stated amount as no mismatch.
- Seeded regression: `E-seeded_regression-20261118-b6a9`; pass_rate 0.7143, refund_amount_correct 0.8571, reply_amount_matches_ledger 0.4286. Gate blocks on refund_amount_correct, pass_rate, and FM-08. Paired CI for pass_rate Δ=-0.271, 95% CI [-0.500, -0.071].
- FM-08 checker compares numeric VND amounts in replies against actual ledger; replies with no stated amount are not misreports.
- Gate owner: eval owner assigned by the team; waiver requires product owner approval and rationale in PR.
- Scope: simulated single-claim LogiX-VN refund/compensation. No live users or production model.
- Limitations: MockLLM, small eval sets, judge replay public data; 5 seeds cannot reliably catch defects occurring only 1/3 runs. Raise eval-set version when adding trace cases/items; re-baseline after metric/spec changes.

## M5–M7 status

- V2: 28 items/labels, check clean. Slices: money_movement, adversarial, denial; gate uses floor 0.80 plus paired CI. `pass_at_k`/`pass_hat_k` implemented, `pass_hat_5` floor 0.80.
- Public M7 traps: all four blocked; advanced tests: 12 passed. User-confirmed v2 trap invocation ended exit 0.
- A/A and mutation scorecard output still needs to be captured in the PR. The empirical A/A run was not completed in this session, so 0.80 is not claimed as empirically calibrated.
