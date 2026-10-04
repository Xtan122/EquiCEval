# Đề xuất: Phép chiếu có lượng hóa tồn tại cho EquiCEval (M1 + M4)

> Tài liệu đề xuất (chưa đưa vào paper chuẩn `paper_brainstorm/equiceval_v3.tex`).
> Cập nhật: xử lý lớp vấn đề "hai mô hình biểu diễn cùng bài toán nhưng khác
> không gian biến do dùng biến phụ (auxiliary) khác nhau".
> Bối cảnh thực nghiệm: dataset 4 bài gốc ComplexOR (`Knapsack`,
> `AircraftAssignment`, `Diet`, `AircraftLanding`).

## 0. Nguồn tham khảo (để trích dẫn trong báo cáo)

- **SOVER** — S. Bhattacharyya, M. Baranwal. *SOVER: Formal Certification of
  Optimization Reformulations via LLM-Assisted SMT Verification*. arXiv:2609.00728
  (2026). https://arxiv.org/html/2609.00728
  - Định nghĩa then chốt: khi candidate có "auxiliary/slack variables that do not
    enter its objective", dùng **existential projection** của các biến đó, thay vì
    so trên không gian lifted. Kiểm 2 tính chất: *domain cross-feasibility* và
    *global objective-order preservation*.
- **FLARE** — H. Robbins, C. Lawless, M. Udell, E. Vitercik. *FLARE: Verifying
  MILP Reformulations with LLM-Based Theorem Proving*. arXiv:2608.25220 (2026).
  https://arxiv.org/abs/2608.25220
  - Định nghĩa **constructive reformulation** với cặp ánh xạ
    `(Φ_fwd, Φ_bwd)` giữa feasible regions + ánh xạ mục tiêu tăng nghiêm ngặt;
    sản xuất certificate machine-checkable.
- **EquivaMap** — H. Zhai, C. Lawless, E. Vitercik, L. Leqi. *EquivaMap:
  Leveraging LLMs for Automatic Equivalence Checking of Optimization
  Formulations*. ICML 2025 (PMLR v267). https://proceedings.mlr.press/v267/zhai25a.html
  - **Quasi-Karp equivalence**: tồn tại ánh xạ biến `f` bảo toàn feasibility và
    optimality. Cơ sở cho EquivaFormulation (thêm slack/valid inequalities).
- **Refai & Ahmed** — *component-level evaluation* (arXiv:2510.16943): baseline RA
  mà EquiCEval cải tiến (M0–M5).
- Nội bộ: `docs/equiceval_v3_proposed_changes.md` §1.1–1.3 (đề xuất trước, cùng
  chủ đề, ở mức khái quát).

## 1. Vấn đề

`paper_brainstorm/equiceval_v3.tex` (dòng ~219) định nghĩa so sánh hai mô hình
qua hai ánh xạ điểm `π*`, `π̂` vào không gian chung `Y`:
`P_gt = π*(F(GT)) ∩ B`, `P_llm = π̂(F(LLM)) ∩ B`.

Cách này giả định hai mô hình có cùng số biến quyết định và `π` là **song ánh**
(đổi tên / scale). Nó **vỡ** khi hai mô hình biểu diễn cùng bài toán nhưng ở
**không gian biến khác số chiều** vì dùng biến phụ khác nhau. Ba lớp quan hệ biến
dưới đây dùng thuật ngữ theo literature (không dùng ký hiệu viết tắt tự đặt):

| Quan hệ biến | Mô tả | Nguồn thuật ngữ |
|---|---|---|
| **Reference elimination** | biến reference vắng mặt ở candidate nhưng biểu diễn được qua biến candidate (vd `z_ji = 1 − z_ij` khi reference dùng cả hai hướng) | EquiCEval nội bộ (`_resolve_ref_eliminations`); liên hệ cặp ánh xạ thuận/nghịch của **FLARE** |
| **Existential projection** | biến candidate là auxiliary không vào objective, chỉ thêm bậc tự do miền khả thi | **SOVER** (auxiliary/slack variables that do not enter the objective → existential projection) |
| **Linear variable mapping** | biến của mô hình này là tổ hợp tuyến tính của mô hình kia, `x = Σ aᵢyᵢ` (không phải song ánh) | **EquivaMap** (Quasi-Karp, ánh xạ tuyến tính) / **FLARE** (constructive reformulation) |

Trường hợp reference và candidate khác **cả hai phía** tập biến phụ chỉ là tổ hợp
của hai lớp đầu, không cần lớp riêng.

### Biểu hiện quan sát được (AircraftLanding, model `gpt-oss-120B`)

Candidate LLM dùng **một `z` mỗi cặp** (gộp `order_link`), reference dùng **hai
`z` mỗi cặp** + `order_link`. EquiCEval hiện tại trả `S_map = unresolved` →
`verdict = unresolved` cho **5/6** cặp dù chúng thực sự không tương đương. Đây là
**abstain do mapping thất bại**, và khi đối chiếu ground truth nó là **bỏ sót
lỗi** (Recall 1/6).

## 2. Nguyên lý giải pháp

> **Không so hai mô hình trên không gian biến lifted. So trên không gian ngữ
> nghĩa chung `Y`, và biến phụ được xử lý bằng phép chiếu có lượng hóa tồn tại.**

Định nghĩa lại ánh xạ (mở rộng `π` từ point-map thành **quantified projection**):

- `D` = tập **biến quyết định** chung (song ánh hoặc suy diễn được). Đây là không
  gian `Y`.
- Biến phụ không vào `Y` bị **chiếu bỏ bằng `∃`**:
  ```
  P*_gt  = { y ∈ Y : ∃ aux_gt,   (y, aux_gt)  ∈ F(GT)  }
  P̂_llm = { y ∈ Y : ∃ aux_llm,  (π(y), aux_llm) ∈ F(LLM) }
  ```
- So `P*_gt` và `P̂_llm` bằng M4 (containment hai chiều) trên `Y`.

Điều kiện soundness của certificate (theo `docs/equiceval_v3_proposed_changes.md`
§1.2, đáp ứng cả SOVER/FLARE):
1. Không sao chép miền của biến gốc sang biến candidate.
2. Bảo toàn lattice cho biến nguyên/nhị phân.
3. Hộp hữu hạn `B` chỉ tạo kết luận `False` (kèm `scope=box`), không tạo `True`.
4. **Nghiệm thu kép**: (a) containment MILP hai chiều; (b) khớp hàng chuẩn hóa
   `q_c = max(‖a‖₁, |b|)` như chứng cứ độc lập không dùng solver.

Nếu không chứng minh được → giữ `unresolved` (không false positive).

## 3. Trách nhiệm module (nguyên tắc độc lập, không chồng chéo)

Mỗi thay đổi thuộc **đúng một module**:

| Module | File | Trách nhiệm DUY NHẤT | Thay đổi đề xuất |
|---|---|---|---|
| M1 | `src/equiceval/canonical_ir.py` | dựng ánh xạ + chiếu biến | `ProjectionCertificate.existential_variables`; mở rộng `build_projection_certificate` (reference elimination, existential projection); `project_ir` giữ biến tồn tại |
| M0 | `src/equiceval/precheck.py` | đọc cờ từ M1 | chỉ phản ánh `S_map` mới; không tự chiếu |
| M4 | `src/equiceval/directed_query.py` | tìm phản ví dụ trên IR đã đồng bộ | nới guard `set(vars)` để chấp nhận biến tồn tại do M1 để lại; KHÔNG tự chiếu |
| M5 | `src/equiceval/objective_discrepancy.py` | so mục tiêu | không đổi |

**Ranh giới**: toàn bộ logic "đồng bộ không gian biến" nằm ở M1. M4 chỉ tối ưu
hóa trên IR đã ở cùng không gian; nó không biết gì về biến phụ.

## 4. Phân loại & xử lý trong M1

`ProjectionCertificate` phân tầng:
1. `variable_map` — song ánh biến quyết định (như hiện tại).
2. `ref_eliminations` — **reference elimination**: `ref_var = f(cand)`. Mở rộng để:
   - chấp nhận liên kết `z_ij + z_ji = 1` (sinh `z_ji = 1 - z_ij`);
   - coi ràng buộc reference **thành tautology** sau thay thế (`0 = 0`) là match
     vacuously, không fail.
3. `existential_variables` (MỚI) — **existential projection**: biến candidate là
   auxiliary không vào mục tiêu, không bị ép bởi ràng buộc chung → đánh dấu để
   lượng hóa tồn tại khi chiếu.
4. `unsupported` — **linear variable mapping** (`x = Σaᵢyᵢ`, không phải song ánh
   1-1): giữ out-of-scope (đúng D2 tài liệu chuẩn).

Certificate chỉ `is_verified = True` khi tất cả biến reference được phủ bởi (1)+(2)
và các biến candidate còn lại thuộc (3). Nghiệm thu kép (§2.4) chạy trước khi
verify.

## 5. Điểm cần bổ sung vào `equiceval_v3.tex` (checklist, CHƯA sửa)

1. **§Khái niệm cơ bản (dòng ~219)**: định nghĩa `π` là **quantified
   projection**, không chỉ point map; nêu ba lớp quan hệ biến (reference
   elimination, existential projection, linear variable mapping).
2. **§M1**: thêm tiểu mục "Ánh xạ biến và phép chiếu" + điều kiện soundness §2.
3. **§M4**: ghi rõ M4 so trên không gian `Y` đã chiếu; biến auxiliary bị chiếu bỏ
   bằng lượng hóa tồn tại.
4. **§Bộ dữ liệu**: bổ sung phép biến đổi "gộp biến nhị phân đối xứng (MILP
   ordering)" và "thêm slack" vào danh sách tạo cặp tương đương/không tương đương.
5. **§Giới hạn**: phân biệt lớp xử lý được (reference elimination, existential
   projection) vs out-of-scope (linear variable mapping).

## 6. Kết quả trên 4 bài gốc (model `gpt-oss-120B`)

Ground truth độc lập (`expeval.label_oracle` + vá thủ công 5 cặp `None`), 24 cặp,
contract `feasible_set_and_objective_affine`.

| Chỉ số EquiCEval | Trước (M1 cũ) | Sau (M1 + projection ∃) |
|---|---|---|
| Recall (`error_recall`) | 1/6 = 0.167 | 5/6 = 0.833 |
| FPR (`false_alarm_rate`) | 0.000 | 0.000 |
| `unresolved_rate` | 0.208 | 0.042 |

Per-pair AircraftLanding (đều có ground truth `False`):

(`P1`…`P6` là nhãn prompt trong dataset, không phải tên lớp quan hệ biến.)

| Cặp | Trước | Sau | Ghi chú |
|---|---|---|---|
| P1 | unresolved | disproved | reference elimination, `order_link` tautology |
| P2 | unresolved | unresolved | khác dấu big-M **thật** → đúng khi abstain |
| P3 | disproved | disproved | đã đủ biến |
| P4 | unresolved | disproved | reference elimination |
| P5 | unresolved | disproved | reference elimination + cần budget ≥ 30s |
| P6 | unresolved | disproved | reference elimination |

Ghi chú: P5 cần `--seconds 30` (budget solver); ở 10s còn timeout (Recall 0.667).
P2 là candidate sai encoding (không phải biến thể hợp lệ) nên M1 không chiếu được —
đây là giới hạn chấp nhận được, M4/M5 không được gọi.

Kiểm chứng soundness cho existential projection (slack): cặp equivalent-with-slack
→ `certified`; cặp broken-cap → `disproved` (Δ←=1.0). Tất cả test
`tests/test_mapping_signatures.py` (18) pass.

## 7. Tiêu chí nghiệm thu (4 bài gốc) — trạng thái

- [x] 5 cặp AircraftLanding `unresolved` → `disproved` (4/5; P2 giữ abstain đúng).
- [x] FPR EquiCEval giữ 0; Recall 0.167 → 0.833.
- [x] Không false positive: test `test_linked_reference_rejects_candidate_with_broken_separation_row`,
  `test_auxiliary_in_objective_is_not_projected`.
- [x] Test ba lớp quan hệ biến + chống false positive trong `tests/test_mapping_signatures.py`.
- [x] `equiceval_v3.tex` giữ nguyên; đề xuất ở file này.
