# Budget do owner tạo — kiểm chứng READ-ONLY

Cập nhật preflight 21/10/2026 09:32–09:33 UTC: AWS read-only thành công; candidate 45 Add AVAILABLE, Budget 20 USD/ba alerts không Actions. [Approval B mới nhất](aws-test-deployment-approval-b.md) và [evidence](evidence/approval-b-final-preflight-readonly.json). Email legacy/0-of-1 vẫn theo xác nhận Console trước, delivery chưa xác minh. Không ghi AWS, không deploy/E2E.

## Cập nhật hiện hành — Console do người dùng xác nhận

**Cấu hình Budget: VERIFIED.** Người dùng xác nhận COST / MONTHLY / 20 USD, Healthy, bắt đầu 2026-10-01; Actual 5,42 USD (27,11%), Forecast 8,54 USD (42,70%). Đúng ba alerts: ACTUAL 80%, ACTUAL 100%, FORECASTED 100%, đều Not exceeded; không Budget Actions. Metric UnblendedCost, loại Credit/Refund và phạm vi toàn account đã được xác minh trong snapshot API trước đó.

**Recipient: Active (legacy), theo Console người dùng kiểm tra. Email verification: 0/1 verified; email delivery: DELIVERY_NOT_VERIFIED.** Không đánh đồng trạng thái legacy với email đã xác minh hoặc đã nhận thành công. Không gửi verification, không sửa Budget/notification. Thời điểm quan sát Console không được cung cấp; evidence chỉ ghi thời điểm tiếp nhận. [Evidence mới](evidence/budget-20usd-user-console-confirmation.json) bổ sung snapshot API lịch sử, không thay thế nguồn gốc của snapshot đó. Sáu Budget cũ khớp fingerprint ở lần kiểm tra trước; không kiểm tra lại AWS trong cập nhật local này.

Hồ sơ [Approval B](aws-test-deployment-approval-b.md) đã chuẩn bị, **chưa được phê duyệt**. CloudFormation deployment: NOT_EXECUTED. AWS E2E: NOT_RUN. Các trạng thái PARTIAL/unconfirmed bên dưới mô tả thời điểm API lịch sử trước xác nhận Console này.

**Overall: PARTIAL** — cấu hình Budget/cảnh báo đã xác minh; trạng thái xác minh recipient chưa có bằng chứng API. Không có thao tác tạo/sửa/xóa từ agent.

| Trạng thái | Kết quả |
|---|---|
| Budget | CREATED_BY_USER / CONFIGURED_VERIFIED |
| Notifications | CONFIGURED, đúng ba cảnh báo phần trăm |
| Recipient | Cùng một EMAIL recipient trong cả ba cảnh báo, không xuất địa chỉ |
| Subscription/activation | SUBSCRIPTION_CONFIRMATION_UNVERIFIED |
| Email delivery | DELIVERY_NOT_VERIFIED |
| Agent Budget writes | NOT_EXECUTED |
| Existing Budgets | UNCHANGED theo fingerprint đã có |
| CloudFormation deployment | NOT_EXECUTED |
| AWS E2E | NOT_RUN |

## Thời điểm và phạm vi

STS xác minh exact account kết thúc **0098** trước đọc dữ liệu. DescribeBudget đọc lúc 2026-10-21 09:14 UTC; vòng kiểm tra chính **09:16:20–09:16:28 UTC** (16:16:20–16:16:28 Việt Nam). CloudTrail read lúc **09:18:33 UTC** tìm thấy CreateBudget thành công **09:11:39 UTC** (16:11:39 Việt Nam), đúng tên. Đây là thời điểm tạo từ event, không suy ra từ LastUpdatedTime.

Không bật CloudTrail, không tạo event store/trail, không thay đổi service nào; chỉ đọc Event History có sẵn trong cửa sổ giới hạn. Raw CloudTrail và địa chỉ recipient chỉ xử lý trong bộ nhớ, không ghi ra file/log. API User Notifications Contacts cũng chỉ được đọc, không tạo/activate/resend contact.

## Cấu hình thực tế

| Trường | AWS trả về và đánh giá |
|---|---|
| Name | policy-assistant-account-monthly |
| Type / period / amount | COST / MONTHLY / 20 USD |
| Fixed | Không AutoAdjustData/PlannedBudgetLimits |
| Metric | UnblendedCost |
| Filter | NOT RECORD_TYPE IN Refund,Credit; không filter khác |
| Account scope | Toàn exact account …0098; Organizations trả AWSOrganizationsNotInUseException, xác minh account standalone; không BillingViewArn, không mở rộng consolidated billing |
| Region/service/stack/tag | Không giới hạn |
| Start | 2026-10-01 00:00 UTC |
| End AWS default | 2087-06-15 00:00 UTC; không tuyên bố vô hạn |
| HealthStatus | HEALTHY |
| Actual / forecast snapshot | 5.422 / 8.539 USD; snapshot chưa phải hóa đơn cuối tháng |
| Budget Actions | 0, đọc complete list không có next page |

Không có LINKED_ACCOUNT trong filter live; điều này tương đương toàn account vì đã xác minh standalone và không billing view khác. API proposal trước đây giữ account token để phòng consolidated billing; không cần và không được sửa Budget đang đúng scope chỉ để giống byte-for-byte file mẫu.

## Ba notification và bằng chứng phần trăm

| Notification | Threshold | Comparator | Số EMAIL recipients | State lúc đọc |
|---|---:|---|---:|---|
| ACTUAL | 80% = 16 USD | GREATER_THAN | 1 | OK |
| ACTUAL | 100% = 20 USD | GREATER_THAN | 1 | OK |
| FORECASTED | 100% = 20 USD | GREATER_THAN | 1 | OK |

DescribeNotificationsForBudget trả đúng ba type/threshold/comparator nhưng bỏ ThresholdType. Không mặc định trường bị thiếu là PERCENTAGE. Bằng chứng bổ sung:

1. CloudTrail CreateBudget thành công chứa ba notification với **ThresholdType=PERCENTAGE** rõ ràng.
2. Read-only DescribeSubscribersForNotification với PERCENTAGE nhận một subscriber cho từng notification, còn control ABSOLUTE_VALUE cùng type/threshold nhận zero; không có write hoặc sửa notification. Dữ liệu lookup chỉ là bằng chứng hỗ trợ, không dùng để suy diễn email verification.
3. Các type/threshold/comparator ở cấu hình hiện tại khớp event tạo.

CloudTrail chỉ chứng minh cấu hình đã được gửi thành công tại thời điểm tạo; đối chiếu read hiện tại và typed lookup hỗ trợ trạng thái hiện hành. Không gán mọi event cũ là trạng thái hiện tại nếu có thay đổi khác.

## Recipient: giới hạn xác minh

API Budgets trả EMAIL/Address nhưng không có trường trạng thái verification. Chỉ xử lý địa chỉ trong bộ nhớ để kiểm cả ba notification dùng cùng một recipient; không xuất địa chỉ/hash địa chỉ ra báo cáo.

ListEmailContacts được đọc complete, không có contact khớp địa chỉ Budget. Vì vậy không thể gọi GetEmailContact cho một ARN suy đoán hoặc kết luận Active. **Không có record khớp không có nghĩa recipient inactive, legacy hay pending.** API hiện đọc không đủ để chứng minh activation/verification. Cũng không có bằng chứng gửi/nhận email cảnh báo chi tiêu; NotificationState=OK không phải receipt.

Owner kiểm tra riêng trong AWS Console: Budget mới → Notifications/Recipients, quan sát **Active** hoặc **Active (legacy)** nếu AWS hiển thị. Không đưa địa chỉ vào chat/báo cáo. Nếu Pending/Inactive, hoàn tất quy trình riêng với quyền phù hợp; agent không gửi lại thư, sửa subscriber hoặc activate contact trong scope read-only này. Không tạo phí giả để kích cảnh báo.

Nguồn: [Budgets Subscriber schema](https://docs.aws.amazon.com/aws-cost-management/latest/APIReference/API_budgets_Subscriber.html), [AWS verification states](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-email-recipients.html), [EmailContact status](https://docs.aws.amazon.com/notificationscontacts/latest/APIReference/API_EmailContact.html).

## Sáu Budget cũ

Danh sách hiện có **7** Budget, chỉ thêm đúng tên mới. Cả sáu fingerprint cấu hình khớp baseline Approval A; cấu hình notification của Budget 5 USD cũng khớp. CalculatedSpend/LastUpdatedTime/HealthStatus và NotificationState động không dùng làm cấu hình bất biến.

Giới hạn: baseline không lưu địa chỉ subscriber của các Budget cũ; không khẳng định đã so lịch sử địa chỉ đó. Không truy vấn lại địa chỉ cũ hoặc thay đổi bất kỳ Budget nào để kiểm tra. Kết luận UNCHANGED giới hạn theo cấu hình/fingerprint có sẵn và các thao tác agent đã thực hiện.

## Sẵn sàng trình phê duyệt triển khai, chưa triển khai

Read-only **09:18:37 UTC**: candidate `fcaj-review-20261021-072124-24ba855e`, stack `policy-assistant-fcaj-test`, ap-southeast-1 vẫn CREATE_COMPLETE/AVAILABLE, **45 Add**, không Modify/Remove/Replace. Source fingerprint vẫn khớp. Không tải lại ZIP vì không có thay đổi source và bằng chứng integrity đã có; cấu hình/behavior runtime vẫn NOT_RUN.

**GO về cấu hình Budget và hồ sơ kỹ thuật để trình Approval B riêng.** Trước khi dựa vào email làm lớp cảnh báo vận hành, cần xác nhận trạng thái recipient riêng trong Console. Delivery vẫn có thể NOT_VERIFIED khi chưa có cảnh báo thực tế, không được ghi PASS giả. Budget không hard-cap và không tự dừng tài nguyên.

**NO-GO thực thi tự động:** Approval B, thao tác E2E và cleanup chưa được cấp. Không tạo lại Budget đã tồn tại, không sửa Budget hoặc gửi verification vì phát hiện thiếu bằng chứng.

## Evidence

- [Budget/notifications/actions/fingerprint/recipient read-only](evidence/budget-20usd-created-readonly-verification.json)
- [CloudTrail đã lọc bỏ recipient/raw event](evidence/budget-20usd-cloudtrail-readonly.json)
- [Candidate sau khi Budget được tạo](evidence/aws-candidate-after-budget-readonly.json)
- [Inspection đầu tiên](evidence/budget-20usd-user-created-inspection.json)

Thông tin chi phí trước đây và kịch bản 15.1697 USD vẫn là hai loại dữ liệu khác nhau; Budget creation không biến kịch bản đó thành AWS forecast hoặc cho phép chi 20 USD.
