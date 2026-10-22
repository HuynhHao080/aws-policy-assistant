# Tạo Budget 20 USD bằng AWS Console — hướng dẫn cho lần được duyệt sau này

**Hiện trạng: PREPARED_NOT_CREATED. Không thao tác tạo/lưu trong nhiệm vụ chuẩn bị.** Mọi bước ghi dưới đây chỉ thực hiện sau phê duyệt riêng trong [phiếu duyệt](../budget-20usd-approval.md). Hướng dẫn không cấp quyền triển khai ứng dụng.

## Chuẩn bị và điểm dừng

1. Đăng nhập phiên AWS được cấp quyền. Kiểm tra đầy đủ account ID trong phiên riêng và đối chiếu với account đã được STS xác minh kết thúc **0098**; suffix riêng lẻ không đủ nếu toàn bộ ID không khớp. Không đưa ID đầy đủ hoặc thông tin đăng nhập vào báo cáo.
2. Mở **Billing and Cost Management → Budgets**. Không đổi IAM, Billing settings, Cost Explorer settings hoặc cost-allocation tags để vượt lỗi quyền. Nếu thiếu quyền, dừng và ghi BLOCKED.
3. Đọc lại danh sách: `policy-assistant-account-monthly` phải chưa tồn tại. Nếu đã có, dừng, không Update/Delete hoặc tạo tên khác tùy ý. Lưu số lượng và cấu hình các Budget cũ để đối chiếu; baseline gần nhất có **6 Budget**, trong đó có Budget COST 5 USD. Nếu số lượng thay đổi bởi người khác, giải thích trước khi tiếp tục, không áp số 6 cứng nhắc.
4. Kiểm tra phê duyệt ghi rõ tên, mức 20 USD, ba cảnh báo, kỳ bắt đầu, phạm vi account và quyền đăng ký người nhận riêng. **Chưa có phê duyệt: dừng ở đây.** Không gửi verification/test notification trong giai đoạn chuẩn bị.

## Cấu hình Budget sau khi được duyệt

1. Chọn **Create budget → Customize (advanced) → Cost budget**. Không dùng quick template có filter/notification mặc định khác đề xuất.
2. Nhập tên chính xác `policy-assistant-account-monthly`.
3. Chọn **Monthly**, hiệu lực **Recurring**, phương pháp **Fixed**, số tiền **20 USD**. Không chọn tự điều chỉnh hoặc planned monthly limits. Kỳ đề xuất bắt đầu **October 2026**, tương đương 2026-10-01 00:00 UTC; nếu tạo vào tháng sau, cần xác nhận lại kỳ. Tính cả chi phí đã ghi nhận từ đầu tháng, không reset chi phí lúc tạo Budget.
4. Phạm vi: toàn bộ dịch vụ/region trong **đúng account …0098**. Nếu console cho chọn Billing view, chỉ dùng view có phạm vi phù hợp; không tạo/chia sẻ view mới. Trong consolidated billing, thêm **Linked account** đúng account đã xác minh để tránh tính cả tổ chức. Không lọc Environment/Project, Service hoặc Singapore; CloudFront và chi phí region khác vẫn nằm trong phạm vi account.
5. Trong phần nâng cao về aggregation/cost types, chọn **Unblended costs**, không chọn blended, net-unblended hoặc amortized. **Loại Credit và Refund**: tùy giao diện, bỏ chọn Include credits/Include refunds hoặc loại hai Charge type tương ứng. Không thêm filter khác làm hẹp dịch vụ/region. Giữ Tax, Support và các charge type khác trong phạm vi khi được phân bổ cho account; không mặc định tax bằng 0 hoặc miễn support.
6. Đối chiếu cấu hình API tương đương: `Metrics=[UnblendedCost]`; `FilterExpression=LINKED_ACCOUNT(exact account) AND NOT RECORD_TYPE(Credit,Refund)`. Không kết hợp API `FilterExpression/Metrics` với `CostFilters/CostTypes`. Nếu Console diễn giải bằng trường cũ, sau tạo kiểm tra tính tương đương theo ngữ nghĩa; không sửa thêm chỉ để đổi format API.

## Ba cảnh báo và người nhận

Tạo đúng ba cảnh báo riêng; số 80/100 là **PERCENTAGE**, không nhập 16/20 vào ô phần trăm:

| Loại | Ngưỡng | So sánh | Ý nghĩa |
|---|---:|---|---|
| Actual | 80% | Greater than | Chi phí thực tế lũy kế >16 USD |
| Actual | 100% | Greater than | Chi phí thực tế lũy kế >20 USD |
| Forecasted | 100% | Greater than | Dự báo chi phí cuối kỳ >20 USD |

1. Người dùng nhập và xác nhận người nhận **chỉ trong AWS Console được cấp quyền**. Không yêu cầu gửi địa chỉ qua chat, không ghi vào JSON public, Git, log hoặc ảnh chụp. Không lấy địa chỉ từ Budget cũ theo suy đoán. Có thể dùng cùng người nhận đã được duyệt cho cả ba cảnh báo.
2. Chọn direct email; không tạo SNS topic/subscription hoặc Budget Report. Không cấu hình **Budget Actions** hoặc IAM role tự dừng/deny.
3. Đăng ký địa chỉ mới có thể làm AWS gửi email xác minh. Chỉ lưu khi phê duyệt tạo Budget bao gồm đăng ký recipient này. Người nhận mở thư xác minh từ AWS, đăng nhập đúng account đã thêm địa chỉ và hoàn thành xác nhận. Địa chỉ đã verified trong cùng account có thể Active ngay. Đây không phải luồng xác nhận SNS của ứng dụng.
4. Kiểm tra trạng thái người nhận trong AWS: **Active** hoặc trạng thái hợp lệ AWS ghi nhận. Pending/Inactive nghĩa là chưa hoàn thành; không đánh dấu thông báo hoạt động. Không dùng trả lời API có subscriber để chứng minh email đã tới.

## Review trước khi bấm Create

Đọc lại tên, 20 USD, MONTHLY/Recurring, tháng bắt đầu, account, UnblendedCost, loại Credit/Refund, ba ngưỡng đúng phần trăm, người nhận đã xác nhận riêng, không có Actions. **Chỉ bấm Create budget khi có phê duyệt riêng còn hiệu lực.** Bản hướng dẫn này không phải phê duyệt. Không thao tác Save/Edit trên bất kỳ Budget cũ nào.

## Kiểm chứng sau tạo — chỉ thực hiện ở lần được duyệt

- [ ] DescribeBudget/Console trả về đúng tên, COST, MONTHLY, 20 USD, kỳ bắt đầu/hiệu lực và account scope. Không tự suy diễn scope chỉ từ account đang đăng nhập.
- [ ] Metric/filter tương đương với đề xuất; không có Credit/Refund, tag/region/service filter ngoài scope. Kiểm tra health của Billing view nếu AWS trả về; thiếu quyền/Unhealthy phải ghi đúng.
- [ ] Có đúng ba notification: ACTUAL 80 PERCENTAGE, ACTUAL 100 PERCENTAGE, FORECASTED 100 PERCENTAGE, GREATER_THAN. Nếu AWS không trả ThresholdType, xác minh trong Console/nguồn có thẩm quyền, không mặc định là phần trăm.
- [ ] Người nhận được xác nhận riêng và Active trong account; không xuất địa chỉ. Việc nhận cảnh báo chi tiêu thật chỉ xác minh ở lần evaluation đủ điều kiện, không tạo chi phí giả để thử.
- [ ] Không có Budget Actions. Không có SNS/Report ngoài cấu hình đã duyệt.
- [ ] So sánh danh sách Budget trước/sau: chỉ thêm đúng tên mới, lý tưởng từ 6 lên 7 nếu không có thay đổi đồng thời; các Budget cũ giữ nguyên.
- [ ] Đối chiếu fingerprint cấu hình Budget cũ ở `../evidence/budget-20usd-preparation-readonly.json`. Không so CalculatedSpend/LastUpdatedTime/HealthStatus động như cấu hình; với notifications không coi NotificationState OK/ALARM là chỉnh threshold. Đối chiếu riêng mức 5 USD, kỳ, metric/filter, ngưỡng và người nhận cũ trong Console riêng; không ghi địa chỉ ra evidence.
- [ ] Đối chiếu actual/forecast với CE cùng phạm vi và thời điểm; lệch do refresh/rounding phải ghi rõ. Budget actual ban đầu có thể chưa cập nhật, không coi 0 là không tốn phí.
- [ ] Lưu UTC, kết quả VERIFIED/BLOCKED/NOT_RUN, ảnh đã che thông tin cần thiết và hạn chế. Không tự tiếp tục execute change set hay E2E.

Nếu lỗi, dừng và giữ nguyên các Budget cũ. Không delete/recreate hoặc sửa IAM để thử. Mọi sửa/xóa Budget ngoài tạo mới đã được duyệt cần quyết định riêng.

## Nguồn chính thức đã đối chiếu 2026-10-21

- [Create cost budget / Console](https://docs.aws.amazon.com/cost-management/latest/userguide/create-cost-budget.html)
- [CreateBudget API và hai bộ trường loại trừ nhau](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_CreateBudget.html)
- [Notification](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_Notification.html), [NotificationWithSubscribers](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_NotificationWithSubscribers.html)
- [Xác minh recipient](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-email-recipients.html)
