# EquiCEval: bản triển khai kiểm chứng ngày 12/09/2026

Ghi chú ngày 15/09: tài liệu này giữ trạng thái lịch sử ngày 12/09. Trạng thái
mã mới, phần M2/M3 đã bổ sung và lệnh chạy nằm trong
[ghi chú LaTeX](EquiCEval_src_sync_20260915.tex); bản PDF ở
`output/pdf/EquiCEval_src_sync_20260915.pdf`. Không trộn kết quả hai phiên bản.

Bản này hiện thực phần lõi của hướng cải tiến sau phản biện. Nó cung cấp kiểm
chứng theo ngân sách, phản ví dụ kiểm tra lại được và chứng cứ suy ra theo nhóm
ràng buộc. Đây là bản mẫu nghiên cứu đã qua kiểm thử, chưa phải bằng chứng đủ
để khẳng định hiệu quả trên bộ dữ liệu lớn hoặc khả năng được nhận ở hội nghị.

## Giao sinh viên chạy và theo dõi

Bản mới nhất đã chuyển sang [LaTeX](student_experiments/latex/So_tay_van_hanh.tex)
và [PDF 6 trang](../output/pdf/student_experiments/So_tay_van_hanh.pdf): cùng máy,
cùng hồ sơ cấu hình, có kiểm tra trước/sau và khóa chạy đồng thời. Các hướng dẫn
Markdown dài trước đây được giữ làm lịch sử. Chưa duyệt máy chung cho sinh viên;
hồ sơ QA trên máy phát triển không thay thế việc đó.

Bộ hướng dẫn vận hành riêng cho Nguyễn Mạnh Cường, Nguyễn Trọng Hoàng,
Nguyễn Xuân Thành và Nguyễn Thái Sơn ở
[docs/student_experiments/README.md](student_experiments/README.md).
Gói pilot có lệnh kiểm tra môi trường, chạy cố định 108 lượt, xem tiến độ và
kiểm tra đầu ra; không gọi API. Dữ liệu, phương pháp, nhãn và sửa mã vẫn do
người hướng dẫn/trợ lý nghiên cứu phụ trách. Gói thực nghiệm chính chưa phát hành.

## Cách chạy

Chạy từ thư mục gốc dự án, dùng môi trường đã có:

```sh
.venv/bin/python -m pytest tests -q --disable-warnings
.venv/bin/python -m experiments.run_verified_evaluation --output output/my_verified_run.json
.venv/bin/python -m experiments.plot_verified_evaluation --input output/my_verified_run.json --output-dir output/my_verified_figures
```

Chương trình từ chối ghi đè tệp kết quả hoặc thư mục hình đã tồn tại. Mặc định,
nó chạy 12 ca kiểm tra nhỏ với ba ngân sách 0, 1, 5 giây và ba chế độ, tổng cộng
108 lượt. Các chế độ:

| Chế độ | Cách xử lý |
|---|---|
| `direct_only` | Truy vấn bộ giải theo từng hàng; không tìm chứng cứ tổ hợp |
| `certificates` | Thử chứng cứ đại số, rồi tổ hợp không âm của các hàng, rồi truy vấn vi phạm |
| `early_stop` | Như trên, nhưng dừng tìm cực đại khi đã có phản ví dụ quyết định |

Đây là đối chứng nội bộ để kiểm tra từng thành phần. `direct_only` không được
gọi là bản tái lập Refai--Ahmed, SOVER hay FLARE.

Có thể đọc bộ dữ liệu khác bằng `--dataset path.json --limit 20`. Các nhãn cũ
`is_semantically_equivalent` và `solver_certified` không được dùng làm đáp án
đã xác minh. Chương trình chỉ tính độ chính xác cho cặp có thể xác minh bằng
bộ liệt kê độc lập hiện có; các nhãn còn lại là `null`. Phạm vi bộ liệt kê:
biến nguyên/nhị phân với cận hữu hạn, cùng tên biến, tối đa 100.000 điểm.
Nó không gọi mã chuẩn hóa, mã kiểm chứng hay bộ giải.

## Bốn tiêu chí đúng/sai đã hỗ trợ

- `feasible_set`: giữ nguyên miền nghiệm sau ánh xạ.
- `feasible_set_and_objective_affine`: cùng miền nghiệm và mục tiêu thỏa
  `reference = a·candidate+b`, `a>0`; đây là tiêu chí chính của thí nghiệm
  EquivaFormulation.
- `feasible_set_and_objective_value`: thêm yêu cầu hàm mục tiêu
  cùng giá trị trên miền giao, sau khi đưa min/max về cùng chiều. Hệ số mục tiêu
  được giữ nguyên; nhân mục tiêu với 2 không bị tự động coi là đổi đơn vị hợp lệ.
- `feasible_set_and_argmin`: chỉ yêu cầu cùng tập nghiệm tối ưu; đây là phân
  tích phụ và rộng hơn quan hệ affine dương.

Các tiêu chí có thể cho đáp án khác nhau trên cùng cặp mô hình. Mỗi nhật ký và
phần tổng hợp đều phải ghi rõ tiêu chí đang dùng.

## Đọc kết quả

| Trạng thái | Ý nghĩa |
|---|---|
| `certified` | Các nghĩa vụ cần thiết có chứng cứ suy ra được kiểm tra bằng số hữu tỉ |
| `within_tolerance` | Có cận số của bộ giải đủ nhỏ; chưa có đủ chứng cứ hữu tỉ |
| `disproved` | Có phản ví dụ hoặc khác trạng thái khả thi; xem mức bằng chứng đi kèm |
| `unresolved` | Chưa đủ bằng chứng, có thể do hết ngân sách hoặc điểm số chưa kiểm tra được |
| `unsupported` | Kiểu biến/ánh xạ/biểu diễn nằm ngoài phạm vi hiện thực |
| `within_scope` | Chỉ xác nhận bên trong hộp kiểm tra, không xác nhận toàn bộ bài toán |

`certified` có điều kiện: dữ liệu đầu vào, ánh xạ và phạm vi đã khai báo phải
đúng. Bộ kiểm tra số hữu tỉ hiểu hệ số theo chuỗi thập phân của dữ liệu đầu vào;
nó không chứng minh mô hình tham chiếu diễn đạt đúng đề bài ngôn ngữ tự nhiên.
Ánh xạ cùng tên biến được ghi thành giả thiết tường minh. Không tự xác minh
ý nghĩa biến chỉ từ dấu gạch dưới, tên gần giống hoặc mẫu hệ số.

Mỗi chiều có `lower_bound`, `upper_bound`, `status`, `obligations` và
`evidence_level`. Giá trị `discrepancy_value` là mức vi phạm đã tìm được;
khi chưa hoàn tất nó chỉ là cận dưới. Không dùng riêng giá trị đó để kết luận
không có lỗi. Giá trị chưa xác định được ghi `null` trong JSON.

Mỗi phản ví dụ được kiểm tra lại trên các hàng và cận chưa chuẩn hóa, gồm kiểm
tra tính nguyên. Chỉ những hàng bị vi phạm ở đúng điểm được trả về mới xuất
hiện trong danh sách hàng vi phạm. Điểm thập phân chưa thỏa chính xác đẳng thức
nguồn có thể bị từ chối, dẫn tới chưa kết luận; hiện chưa có bước sửa nghiệm
hữu tỉ tổng quát.

## Chứng cứ theo nhóm ràng buộc

Với nguồn Ax ≤ b và hàng đích cᵀx ≤ d, chương trình tìm trọng số λ không âm sao
cho Aᵀλ = c và bᵀλ ≤ d. Bộ giải chỉ đề xuất trọng số; hàm
`check_implication_certificate` tự kiểm tra lại các đẳng thức/bất đẳng thức
bằng số hữu tỉ, không gọi bộ giải.

`support_rows` ghi các hàng có trọng số khác 0, chẳng hạn x ≤ 1 và y ≤ 2 cùng
bảo đảm x + y ≤ 3. Đây là quan hệ nhiều-một có bằng chứng. Nó chưa phải thuật
toán tìm nhóm giải thích nhỏ nhất, chưa xác định nguyên nhân lỗi duy nhất và
chưa nối tự động từng hàng với câu trong đề bài.

Với MILP, tổ hợp hàng của miền nới lỏng LP là điều kiện đủ. Khi không tìm được,
chương trình vẫn chạy truy vấn có xét tính nguyên; không suy ra mô hình sai.
Chứng cứ MILP cần suy luận nhánh/cắt chưa được xuất theo định dạng VIPR.

## Ngân sách và khả năng tái lập

Một đối tượng ngân sách dùng chung cho kiểm tra đầu vào, truy vấn hai chiều,
tìm chứng cứ và so sánh mục tiêu. Không cấp lại toàn bộ thời gian cho mỗi hàng.
Có thể giới hạn thêm số lần gọi bằng `max_solver_calls` trong API.

Đây là hạn thời gian hợp tác: bộ giải nhận thời gian còn lại; Python dựng mô
hình, kiểm tra chứng cứ và đóng tiến trình có thể vượt nhẹ hạn. Nhật ký ghi
thời gian thực và từng lần gọi. Chưa có cơ chế hủy cứng toàn bộ tiến trình.
Ngân sách của bộ tạo/xác minh nhãn độc lập không được tính vào thời gian công
cụ chấm; nhật ký công cụ bắt đầu sau bước tạo nhãn.

Tệp kết quả lưu đầu vào mỗi cặp, đáp án và chứng cứ của bộ liệt kê, hợp đồng,
ngân sách, bằng chứng đầu ra, phiên bản Python/PuLP và SHA-256 các tệp mã liên
quan. Giá trị tối ưu do người gọi truyền vào API chỉ phục vụ mô tả, không tham
gia quyết định đúng/sai. Runner mới không tạo giá trị tối ưu từ nhãn.

Bốn tỷ lệ chính luôn kèm tử số/mẫu số: phạt oan, xác nhận nhầm, phát hiện lỗi,
xác nhận đúng mô hình tương đương. Báo riêng chính sách chỉ nhận chứng cứ hữu
tỉ và chính sách cho phép cận số; không gộp hai mức bảo đảm thành một.

## Những gì đã sửa

- Kiểm tra cả hai phía của đẳng thức.
- Hết thời gian/lỗi bộ giải không trở thành sai khác 0.
- Không chép cận tham chiếu lên mô hình cần đánh giá.
- Giữ cận dưới 0 và cận nhị phân; giữ các hệ số nhỏ thay vì âm thầm xóa.
- Kiểm tra miền bị chặn theo từng biến và cả hai hướng.
- Qua kiểm tra đầu vào không còn được gọi là đã chứng nhận mô hình đúng.
- Ghép cặp hiển thị chỉ dùng bằng chứng đại số theo hàng; không ghép vòng tròn
  bằng hai mô hình đầy đủ và không dùng tỷ lệ ghép để quyết định mô hình sai.
- Không chuẩn hóa mất độ lớn hàm mục tiêu; so sánh mục tiêu bằng truy vấn trên
  miền giao thay cho cực đại trên vài điểm mẫu.
- Tách kết luận trong hộp với kết luận toàn bộ bài toán.
- Thay runner cũ bằng runner có kiểm tra nhãn độc lập. Các hàm vẽ số minh họa
  cũ đã bị vô hiệu hóa; chương trình vẽ mới chỉ đọc nhật ký từng cặp.

## Các phần còn cần làm để viết bài báo

1. Đối chiếu FLARE/SOVER và chốt khác biệt về chẩn đoán, ngân sách, mức chứng cứ.
2. Thu đầu ra LLM thật và xác minh nhãn độc lập cho LP/ánh xạ phức tạp. Bộ thử
   nhỏ hiện tại không chứng minh chất lượng trên các trường hợp này.
3. Triển khai argmin/cross-regret nếu chọn làm đóng góp; kiểm soát nghiệm gần
   tối ưu và trạng thái chưa kết luận.
4. Tìm nhóm giải thích gọn, liên kết với yêu cầu đã xác minh và đo lợi ích cho
   người đọc. Không coi nhóm có trọng số khác 0 là nhóm tối thiểu.
5. Đánh giá chi phí trên nhiều kích thước, họ bài toán và mẫu số đủ lớn. Các
   thủ thuật lưu chứng cứ qua nhiều lần chạy và khởi động lại bộ giải chưa có.
6. Tiếp tục kiểm tra giới hạn của Δ: thêm hàng dư có thể đổi độ lớn điểm số;
   không diễn giải nó thành khoảng cách hình học hay mức thiệt hại nghiệp vụ.

Tệp kết quả kiểm tra đã chạy: `output/verified_evaluation_20260912_final.json`.
Biểu đồ từ nhật ký này: `output/verified_figures_20260912_final/measured_verification.png`.
Bản thảo đã cập nhật ở mục 9.1; bản PDF: `output/pdf/equiceval_v3.pdf`.
Kiểm tra toàn bộ thư mục `tests`: 54 ca vượt qua. Môi trường hiện có phát cảnh
báo PuLP về API sẽ thay đổi trong phiên bản tương lai; chưa nâng cấp thư viện.
Kết quả 12 ca nhỏ phục vụ kiểm thử và minh họa quy trình; các tỷ lệ tốt trên đó
không được dùng làm bảng hiệu quả chính của bài báo.
