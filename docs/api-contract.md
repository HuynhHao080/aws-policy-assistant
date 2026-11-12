# Public API contract — 2026-10-30

All routes except `GET /health` require Cognito JWT authorization at API Gateway. The application uses the gateway-verified `sub`; supplying a bearer header to a direct Lambda invocation does not establish an identity. Application responses are JSON; errors contain `error` and `message`. Numbers from DynamoDB are serialized as JSON numbers.

| Method | Path | Result |
|---|---|---|
| GET | `/health` | Public Lambda liveness |
| GET | `/me` | Identity, groups, daily limits and AI configuration flag |
| GET | `/policies/{policy_id}` | Published shared policy; internal vectors/lowercase fields stripped |
| GET | `/policies?keyword=...&limit=...&next_token=...` | Bounded keyword search, 1–100 result limit, 1,000 evaluated records/request; continuation token |
| POST | `/documents/upload-session` | Optional `filename`; owned session and a five-minute presigned multipart POST form enforcing PDF content type and 1 byte–10 MiB |
| POST | `/documents/submit` | Required `doc_id`, `s3_key`; pins the uploaded S3 version and persists pending work |
| GET | `/documents?limit=...&next_token=...` | Owner-scoped newest-first pages, 1–50 records; deleted/account-job records hidden |
| GET | `/documents/{doc_id}/status` | Owner-scoped status, title, counts and error code |
| GET | `/documents/{doc_id}/download` | Five-minute URL for the sealed source version after processing |
| PATCH | `/documents/{doc_id}` | Required `title`; rename owned metadata |
| DELETE | `/documents/{doc_id}` | Queue permanent purge; returns deleting status |
| POST | `/ask` | Required `question` (1–2,000 chars), optional up to 10 owned `document_ids`; answer, grounded flag, server-validated citations and conversation ID |
| GET | `/conversations?next_token=...` | Owner-scoped history pages of 20 |
| DELETE | `/conversations/{conversation_id}` | Delete own history entry |
| POST | `/account/delete` | Required `{ "confirmation": "DELETE" }`; blocks access, queues account/data purge |
| GET | `/admin/overview` | Administrators only: global monthly counts and limits |
| GET | `/admin/audit?next_token=...` | Administrators only: audit pages of 30 |
| GET | `/admin/policies?keyword=...&limit=...&next_token=...` | Administrators only: metadata catalogue, ID/title/category search, 1–50 evaluated records per page; may return an empty page with a continuation token |
| GET | `/admin/policies/{policy_id}` | Administrators only: current snapshot, separate draft, publication state and opaque revision token; no internal vectors |
| PATCH | `/admin/policies/{policy_id}` | Administrators only: `action` save_draft/publish/archive/discard_draft, `expected_revision`, and `draft` for save_draft; conditional update and audit transaction |
| PUT | `/admin/policies/{policy_id}` | Administrators only: legacy direct publication using title/category/content/keywords; existing policy updates require expected_revision; creates embeddings and atomically publishes with audit |
| DELETE | `/admin/policies/{policy_id}` | Administrators only: atomically delete policy and record audit |

## Documents

Presigned uploads use multipart POST, not the former PUT demo flow. Append every returned `upload_fields` field to FormData, then append the file last. Do not attach the Cognito token to S3. Only `quarantine/{doc_id}/document` is client-writable; sealed originals and extraction/vector files are server-controlled.

States: `awaiting_upload → pending → processing → processed`, with `ocr_pending` for asynchronous recognition, `failed` for terminal errors, and `deleting → deleted` for removal. A processed state denotes text/OCR extraction and indexing, not a malware clearance or a guarantee about document meaning. Maximum 100 text pages or 10 scanned pages per PDF. Encrypted, malformed and over-limit files fail explicitly. Worker leases and conditional writes prevent concurrent jobs from resurrecting deleted/processed state.

A different user receives 404 for another user's document or source selection. Missing identities get 401, invalid parameters 400, insufficient state 409, a blocked deleting account 410, exhausted quota 429, invalid AI schema/citations 502 and temporary backend unavailability 503. The older policy handler can return generic 500 on database errors. Signed download URLs remain temporary bearer access and should not be shared.

## Retrieval and history

Generation sees at most five ranked excerpts. Default scope is the 20 newest metadata records belonging to the current owner; explicit source selection accepts up to 10 owned IDs. Each selected document is re-read consistently before S3 access. Shared-policy retrieval is bounded by one DynamoDB scan of up to 1,000 evaluated items and its response-size limit. New policies carry compact multilingual vectors; old sample records are hidden in production until publication.

Responses include trusted source identifiers, titles, document IDs/pages or policy IDs, and excerpts. Model output must be valid JSON and cite only supplied IDs. No supporting excerpt yields an explicit insufficient-evidence response. Valid IDs prove source membership, not semantic truth: users must verify the answer against the source. Prompt/source text is rendered as plain text in the browser.

History stores the question, answer and citations for 30 days, with eventual TTL cleanup and immediate per-entry deletion. Deleting a PDF does not rewrite prior conversations; delete those entries or the account to remove history containing earlier excerpts.

## Asynchronous reliability

Submit acknowledges persisted work, not completed OCR. DynamoDB Streams dispatches to SQS with partial batch failures. SQS retries failed records; processing is idempotent. The recovery job handles stalled work/timeouts and OCR polling. Metadata writes and processing notifications do not depend on the API synchronously succeeding at SQS SendMessage. See `production-runbook.md` for alarms, retention and limits.

## Administrator publication workflow

New clients should use GET/PATCH, not direct PUT. Create a draft using `{ "action": "save_draft", "expected_revision": null, "draft": { "title": "...", "category": "...", "content": "...", "keywords": [] } }`. A null expected revision is only valid if the ID does not yet exist. Reuse the returned opaque `revision` as `expected_revision` for later PATCH actions. Do not parse or synthesize this token; legacy records may initially return a timestamp.

Saving a draft preserves the full published snapshot, public timestamp and search vectors; draft text is neither customer-visible nor an AI source. Publish takes the saved draft, validates/indexes it and replaces the published snapshot, then removes that draft. Publishing an archived policy without a draft restores its retained snapshot. An already-published policy without a new draft cannot be published again. Archive preserves current/draft content; discard_draft removes only the working draft, leaving a never-published empty record archived. This is not a complete revision-history system.

Every successful mutation rotates the edit token. Missing/stale tokens on edits return 409; a condition is also checked inside the policy+audit transaction to catch races after the read. The legacy DELETE route performs a guarded atomic delete against the server-read revision; it does not implement a client-provided revision precondition and is not used by the new editor. There is no new bulk-delete API. Existing policy IDs/content need no migration.

The new routes use the same gateway Cognito authorizer and server administrator-group check. Catalogue pages contain summaries only; detail requires administrator access. Public policy responses strip draft_data, revision, edited_at, published_by and existing index/internal fields. Strongly consistent direct-ID reads and retrieval scans are used on the primary table. Archive does not revoke excerpts already stored in earlier conversations or PDFs.

## Support requests and explicit source scope — handover 2026-11-04

`POST /ask` additionally accepts `source_scope`: `all` (default), `policies` or `documents`. Policies-only rejects nonempty document IDs and never queries private PDFs. Documents-only requires selected owned PDF IDs and never queries shared policies. Unknown/non-string scopes fail with 400 before AI quota reservation. Returned/stored answers include `source_scope`; legacy history defaults to all in the UI.

A follow-up can include `context_conversation_id` from the signed-in customer's history. The agent reads up to 400 characters of the previous question to resolve references and retrieves current sources using the new request's scope. Missing, expired, and other accounts' history entries return 404 before inference. Malformed IDs return 400. Each follow-up creates its own history entry.


All support endpoints require gateway JWT authorization. Staff routes additionally require the administrators group.

| Method | Path | Body/result |
|---|---|---|
| GET | `/tickets?limit=20&next_token=...&status=...` | Own bounded summaries, continuation token |
| POST | `/tickets` | `subject`, `message`, exact `consent:true`; returns own full thread |
| GET | `/tickets/{ticket_id}` | Own thread including opaque revision |
| PATCH | `/tickets/{ticket_id}` | `expected_revision`, action `reply` with `message`, or action `close` |
| DELETE | `/tickets/{ticket_id}` | `expected_revision`, `confirmation:"DELETE"`; permanent owner deletion |
| GET | `/admin/tickets?status=open&limit=20&next_token=...` | Bounded staff summaries including owner_id, no message bodies |
| GET | `/admin/tickets/{owner_id}/{ticket_id}` | Explicitly shared customer/staff thread |
| PATCH | `/admin/tickets/{owner_id}/{ticket_id}` | `expected_revision`, action `update`, `status`, optional `message` |

Statuses: open/in_progress/resolved/closed. Customer reply reopens a resolved request; closed rejects customer replies. Max 180 subject characters, 1,500 per message, 20 total messages including initial message. Creation limits: 5/customer/day UTC and 200/app/month. Requests expire 90 days after creation, hidden immediately at expiry even before asynchronous DynamoDB TTL deletion. Updates never extend expiry. State-only close/staff updates remain possible at the message cap. Stale revisions return 409. List limits 1–50, default20; status filters can yield an empty page with continuation. Customer and staff cursors are not interchangeable. Staff queue is a bounded primary-table scan, not a complete ordered CRM report.

Only typed subject/message are shared, never automatic document/history attachments. Administrator support access does not grant private PDF access. Support is never queried by AI retrieval. Staff updates atomically record metadata-only audit events. Account deletion blocks access first and purges support rows before removing Cognito identity. No automatic support email or outbound notification is sent.

## Structured support triage — 2026-11-04

Support creation additionally accepts `category` (`general` default, `warranty`, `returns`, `shipping`, `order`) and `order_ref` (optional trimmed string, max80 characters, no ASCII control characters). Explicit sharing consent covers these customer-supplied fields. References are unverified customer input, not an order-system integration. Creation always sets priority `normal`; direct customer priority input is rejected. Customers cannot alter category/order_ref/priority by PATCH. Staff PATCH may set `priority` to `low`, `normal`, or `high`, with the same required revision and atomic audit transaction. State/priority-only updates do not add a message or extend retention.

Customer/staff list endpoints accept combined exact filters `category`, `priority`, and `order_ref` in addition to status. Invalid enums/types return400. Legacy records lacking metadata read as general/normal/empty reference; default-category/priority filters include these records. Filters do not change the evaluated-page bound or guarantee global sort order. Staff metadata is returned in thread/summary/export responses; no new PDF/history access is granted and references are not copied to audit logs.

`GET /me.limits.tickets_per_day` reports the configured daily support creation quota. `GET /admin/overview.usage` includes `ticket` and `request`; `.limits` includes `tickets` and `requests`. UI displays creation attempts used, not an exact open-case backlog; failed attempts may consume quota.

## Shared shop profile — 2026-11-04

All three routes require the existing gateway JWT authorizer. `/admin/shop` also requires the administrators group. Normal application request quota and account-deletion blocking apply.

| Method | Path | Result |
|---|---|---|
| GET | `/shop` | `{configured, profile, published_at}`; only published contact fields, never draft/revision/author |
| GET | `/admin/shop` | Current snapshot, separate draft, opaque revision (null initially), updated/published timestamps |
| PATCH | `/admin/shop` | Explicit `expected_revision`, action save_draft/publish/unpublish/discard_draft; draft for save_draft, exact `confirmed:true` for publish |

Fields: shop_name max100, support_email max254, support_phone max40, support_hours max240, returns_instructions/support_message max1000 each; strings trim, optional fields may be empty. Mode demo/live defaults demo. Unknown draft fields are rejected. Email/phone format is checked, not ownership/deliverability. Publication requires shop name; live additionally requires email or phone, support hours and return reception instructions. A saved draft and explicit confirmation are mandatory. Stale/missing revisions return409. Publish moves the saved draft to current; saving another draft never changes the current snapshot. Unpublish removes current; discard only removes draft.

The app-wide item `app#shop-profile` uses the existing UsageTable without TTL; it is not a customer counter and is not purged when one user deletes their account. Settings and metadata-only audit are written atomically; an account-deletion condition blocks a deleting administrator from committing changes. No new table/IAM grant or model invocation is required. Contacts remain plain display text, not model context or published policies. Account information is never automatically copied into the shared profile.

## Quality metrics and private answer feedback

Two new routes explicitly use the existing JWT authorizer:

| Method | Path | Contract |
|---|---|---|
| PATCH | `/conversations/{conversation_id}/feedback` | Verified owner only, including for admins; body explicit expected_revision (null initially), rating helpful/not_helpful/null, reason for not_helpful |
| GET | `/admin/quality?month=YYYY-MM` | Administrators only; current/previous UTC answer month, aggregate counters/rates only |

Reasons: missing_info/incorrect/citation/unclear/other. No free comment/question/PDF fields are accepted into aggregate measurements. Feedback is offered only for quality_version1 answers; old history is not backfilled. Same target/reason retries return the current snapshot without another vote; conflicting revisions return409. Changes and withdrawal apply signed counter deltas atomically with the owned history snapshot and deletion-marker guard; underflow/corrupt aggregates are rejected. History expiry is not extended. Limits50 mutation reservations/user/day UTC and5000/app/month; reservations may count failed/conflicting attempts.

Successful answer persistence atomically writes history and aggregates: answers, grounded/refused, source count, scope counts, elapsed processing milliseconds. Only validated persisted answers count, not all requests/errors or old history. Processing time ends before persistence, not browser end-to-end latency. Monthly counters contain no conversation IDs, owner IDs, questions, answers or citations. Counters expire65 days after last update; anonymous cohort totals may remain after private history/account deletion. Feedback is counted in the answer's month and can be changed while the owned conversation remains active.

DynamoDB transaction-conflict persistence retries are bounded to3 attempts using one ClientRequestToken. Conditional conflicts are never automatically retried and no retrieval/model invocation is repeated by this persistence retry. Existing request quotas/model retry behavior remain. Customer history now hides expired records immediately; filtered pages can be empty with continuation tokens.

Quality report includes available_months, started_at, counters, citation_rate, helpful_rate, average_response_ms and feedback limits. Empty denominators return null, not a perfect score. Citation presence is not factual correctness; feedback is opinion. Export is client-side JSON from the same aggregate-only response.
## Policy business-date extension

Policy drafts accept optional `effective_from` and `effective_until` as real `YYYY-MM-DD` dates, inclusive in Vietnam UTC+07. Missing fields on edits preserve the saved draft/current bounds; explicit empty strings/null clear a bound. End before start is400. Existing no-date rows remain unbounded. Draft isolation, explicit publication and revision/audit behavior remain unchanged.

Administrator detail/list DTOs include computed `validity_state`: `active`, `upcoming`, `expired`, `invalid` or `unpublished`. `GET /admin/policies?validity=all|active|upcoming|expired|invalid` filters the current published snapshot while preserving the bounded scan cursor. Empty pages can still have continuation tokens.

Public exact lookup/search and AI retrieval omit non-current or invalid-date policies. Before persistence, `/ask` consistently rechecks cited published facts/date bounds; a changed/deleted/hidden/expired source produces409 without saving history or retrying generation. New public citations may contain date bounds; internal source fingerprints are not exported. Old history remains its original snapshot.
## Support collaboration extension

Existing admin ticket PATCH routes additionally accept `{action,expected_revision}` with `claim` or `release`; `takeover` additionally requires `reason`(10–300characters), and `note` requires `note`(1–1000characters). Other fields are rejected for these actions, preventing accidental public/private mixed writes. Only the authenticated staff actor can be assigned; arbitrary target IDs are not accepted. Existing no-assignee tickets retain legacy public-update behavior. Another assignee blocks public staff updates with409until explicit takeover; collaborators may still add internal notes.

Admin DTOs expose computed `assignment`(`mine|other|unassigned`), assignment IDs/timestamps, `internal_note_count` and `staff_updated_at`; detail additionally exposes up to20internal notes and the last10assignment events. `GET /admin/tickets?assignee=all|mine|unassigned|other` combines with existing bounded filters/cursor. Customer routes reject assignment filters/private writes and omit every internal field from detail/list/export data, even when their caller also holds an admin group.

Internal writes change the opaque shared revision but preserve public `updated_at`, message count/status and the original expiry. Notes share ticket lifecycle/retention and are never AI sources. Staff account deletion does not erase contributions to tickets owned by other customers. Assignment is coordination among trusted administrators, not a new confidentiality/tenant boundary or staff-directory service.

### Extracted PDF text

`GET /documents/{doc_id}/text?page=1` returns `doc_id`, `title`, `page`, `page_count`, `chunks`, and `truncated` for a processed document owned by the authenticated caller. The page defaults to 1. Pages are bounded by the document's page count and the 100-page application limit. The response shows up to 20,000 characters of the selected page. Chunks retain extraction order and may overlap. An empty page returns an empty array. Responses use `Cache-Control: no-store`.

The API reads the pinned S3 extraction version and rechecks document and account state before returning text. Unauthenticated requests return 401, other owners receive 404, invalid pages receive 400, and documents awaiting processing return 409. The endpoint uses the application request quota.

Admin ticket responses include `customer_waiting_since`, the timestamp of the first consecutive unanswered customer message on an open or in-progress request, or null. Assignments, internal notes, and status-only changes do not count as public replies. The staff queue can sort waiting requests among the pages already loaded. Customer responses omit this field.

Customer ticket responses include `last_staff_reply_at`, the time of the latest public staff reply, or null. List responses omit message bodies.

Administrator policy details include `previous_publication` after the first replacement of a published snapshot. The field contains the previous content snapshot and its publication timestamp when available. `PATCH /admin/policies/{id}` accepts `restore_previous` with the current `expected_revision`; it creates a draft only and returns 409 if a draft already exists or no previous publication is available. Public policy responses and retrieval omit the previous snapshot.

`POST /ask` accepts optional `policy_id` with `source_scope: policies` and no document IDs. It reads only the selected published, currently effective policy, and returns 404 for unavailable policies before inference. The response and history retain `source_policy_id` and `source_policy_title`; later follow-ups can reuse that selection.

Shared-policy retrieval checks up to eight DynamoDB scan pages of 125 evaluated records each. A remaining cursor produces 503 before generation so an incomplete catalogue is not presented as a complete search. Exact policy questions do not scan the catalogue. The lexical ranking matches the central section, adjacent query terms and common paraphrases, while quoting available surrounding context. It supplies at most five excerpts. General PDF retrieval retains the latest-20 metadata lookup when no PDF is explicitly selected.

Structured answers may include `answer_parts` in the response and history. Each entry has `text`, `status` (`supported`, `missing`, or `conflicting`) and `source_ids` referencing the response's citations. The server validates each reference, requires two distinct excerpts for a conflict, and rejects citations on missing parts. Clients can still use the plain-text `answer`; the answer and citation list are derived from the validated parts when supplied.
