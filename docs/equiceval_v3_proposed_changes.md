# Đề xuất bổ sung cho `paper_brainstorm/equiceval_v3.tex`

> Tài liệu này mô tả **các thay đổi cần đưa vào paper mục tiêu**. Không sửa trực
> tiếp file `.tex`; dùng như checklist khi cập nhật.
> Cập nhật 2026-09-26. Bối cảnh: xử lý EquivaFormulation `_d/_h/_k/_l` theo
> contract `feasible_set_and_objective_affine`.

## 1. Thêm tiểu mục M1: "Ánh xạ biến và phép chiếu"

Paper hiện coi ánh xạ biến `π*`, `π̂` vào không gian chung `Y` là **cho sẵn**
(dòng 219–224), chưa nói cách dựng khi biến gốc là tổ hợp nhiều biến candidate.
Ba nhóm biến thể EquivaFormulation (`_d,_h`) buộc phải bổ sung. Đề xuất thêm vào
M1:

### 1.1 Các loại tương ứng biến

| Loại | Dạng | Ví dụ |
|---|---|---|
| Đổi tên | `x = y` | `_c` |
| Đổi tỉ lệ | `x = k·y` | một phần `_i` |
| **Thay tuyến tính (nhóm)** | `x = Σ a_i·y_i` | `_d` (base-10), `_h` (`x=y1+y2`) |
| Khử biến phụ | `z` định nghĩa bởi một đẳng thức | `_f` (`zed`), `_g` (`slack`) |

### 1.2 Điều kiện an toàn của phép chiếu

Phép chiếu `reference → candidate` chỉ được chấp nhận khi:

1. **Không sao chép miền**: không gán cận/kiểu của biến gốc cho từng biến
   candidate. Cận hữu hạn của biến gốc mang theo dưới dạng **ràng buộc tuyến
   tính** trên biểu thức.
2. **Bảo toàn lattice**: nếu biến gốc nguyên/nhị phân thì mọi hệ số `a_i` phải
   nguyên và mọi biến candidate tham gia phải nguyên/nhị phân; nếu không → từ chối.
3. **Hộp hữu hạn `B`**: miền không bị chặn chỉ truy vấn trong `B`; hộp **chỉ tạo
   kết luận `False`** (kèm `scope = box`), không bao giờ tạo `True`.
4. **Nghiệm thu kép**: (a) containment MILP hai chiều; (b) **khớp hàng chuẩn hoá**
   (`q_c = max(‖a‖₁,|b|)`) như chứng cứ thứ hai độc lập không dùng solver.

### 1.3 Bổ sung vào bảng trạng thái M0

`S_map` hiện có giá trị "Không hỗ trợ". Bổ sung ghi chú: mapping nhiều–một
được xử lý bằng phép chiếu ở M1 nếu thỏa §1.2; ngược lại giữ "Không hỗ trợ".

## 2. Bổ sung M5: certificate mục tiêu hằng

Thêm vào M5: nếu mục tiêu candidate **hằng trên mọi biến tự do** và mục tiêu
reference **biến thiên** trên miền khả thi của nó, thì hai mô hình **không thể**
tương đương affine (positive affine bảo toàn tính hằng) và cũng không cùng argmin.
Certificate này **độc lập với ánh xạ biến**, dùng cho họ bài khả thi (`_k`).

## 3. Cập nhật §9.1 (D1/D2/D3)

- **D1**: nêu rõ mapping là input cho **cả** EquiCEval lẫn baseline; có mapping/
  không mapping là hai điều kiện của cùng thí nghiệm, gọi là **pipeline
  comparison**, không phải ablation thuần M1.
- **D2**: bổ sung rằng mapping nhóm **nay xử lý được** nếu thỏa §1.2; các ca
  `_j` (instance khác hoàn toàn) là **out-of-scope** (không có tương ứng biến),
  báo riêng, không tính vào Recall.
- **D3**: giữ nguyên; nhấn mạnh runner chặn lệch contract giữa file nhãn và `--contract`.

## 4. Thêm tiểu mục: tính độc lập của nhãn (chống circular labeling)

Bổ sung vào phần kiểm toán/phương pháp:

1. Oracle relabel **không gọi** M0–M5 (có test CI cấm import).
2. Nhãn `True` có **hai chứng cứ độc lập**: containment MILP + khớp hàng chuẩn hoá.
3. Nhãn `False` có **replay phản ví dụ bằng số học chính xác** trên mô hình gốc.
4. **Audit solver thứ hai** (HiGHS/SCIP/PuLP thay scipy) trên mẫu phân tầng.
5. Mapping là input chung (hợp lệ); không dùng nhãn bảng này chấm bảng khác.

## 5. Cập nhật §giới hạn

- `_j` out-of-scope: contract giả định có ánh xạ biến.
- AUROC chỉ mang tính mô tả; kém tách trên các họ mới (`_k` certificate không có
  điểm bất thường; `_l` khác miền).
- Phạm vi: kết quả trên EquivaFormulation là **điều kiện có mapping**; no-mapping
  là so sánh pipeline.

## 6. Rà soát contract mặc định

Paper đã chốt `feasible_set_and_objective_affine` là chính (dòng 424). Rà lại
mọi câu chữ còn ghi "mặc định" là `objective_value` để tránh nhầm; giá trị tuyệt
đối và argmin chỉ là **phân tích phụ** (dòng 430–433).

## 7. Số liệu cần cập nhật (khi có bộ cuối)

Điền vào bảng thực nghiệm: FPR/Recall/label coverage cho tập `Labeled`, cùng bảng
theo biến thể; ghi rõ `_j` out-of-scope và số `None` còn lại.
