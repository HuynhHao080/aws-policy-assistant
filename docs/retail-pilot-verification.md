# Retail pilot verification — 2026-10-30

This records the earlier answer-refinement release. Current deployment and administrator checks are in [admin-verification.md](admin-verification.md).

Canonical source: `C:\Users\accli\Documents\Project\policy-assistant`. All edits, builds and deployments in this follow-up used this original repo. Former working copies are archived; see WORKING-LOCATION.md. The existing website/stack was updated.

## Answer-refinement release (historical)

Change set `public-final-1793345584` completed with UPDATE_COMPLETE. Lambda ZIP SHA-256: `2dbb212f3e9663a4682fd6f16a157d7aa8dcb120f5ee9c61fa990a1c38395a31`. Template SHA-256: `7bc25d4540b5980f6838394ef1fce0ac5bb8fc34628fcf57bd7f6a01e8c15f37`. Deployed API checksum, immutable ZIP checksum and local runtime module bytes matched during final regression preflight. Source-template comparison changed only six immutable function CodeUri values; IAM, accounts, data resources, quotas and model routing were unchanged. The replacement/removal guard passed.

Generation remains Japan Nova 2 Lite with low reasoning (Tokyo/Osaka destinations); embeddings, storage and OCR remain Singapore. The earlier policy section/context indexing remains in place.

## Changes and verification

- Corrected the overstatement that a handed-over order cannot be cancelled: the answer now preserves the policy's no-automatic-cancellation qualifier and directs the customer to staff/returns handling.
- Refund answers explain the stated trigger without inventing elapsed days or current approval/receipt status. Warranty exclusions now include staff verification of the actual cause.
- Nova 2 answers use a forced `emit_policy_answer` schema containing answer and supplied source IDs. This only serializes output; the application never executes model-selected operations. Unknown citations, unexpected/duplicate output blocks, extra keys, invalid answer fields and truncated responses are rejected before history is saved. The legacy Micro rollback route retains text-JSON parsing. No automatic extra inference retry was added.
- Full Python 3.12 suite: **169 passed, 11 opt-in live tests skipped**. The ten final structured-output checks also passed after the final test assertion edit. SAM validation and fresh build succeeded. The frontend was unchanged in this follow-up; its earlier 9 passing tests/build/audit remain historical evidence, not newly executed browser checks.

The schema approach follows [AWS Nova structured-output/tool guidance](https://docs.aws.amazon.com/nova/latest/nova2-userguide/using-tools.html). It improves formatting reliability, not factual certainty.

## Final live evidence

**30/30 public-policy questions completed with zero request errors**, using byte-matched deployed retrieval/answer code, live public-policy reads, embeddings and generation via CLI transport. All returned grounded answers with DEMO-SHOP citations. Manual review found all 30 core outcomes acceptable: 27 passed without a note and 3 have secondary notes. Case 15 gives an unnecessary example about faulty goods despite the customer stating no fault; case 18 omits the payment-provider display-time caveat but does not promise receipt or invent status; case 26 retains internal instructional wording. These notes are not counted as perfect answers. Evidence: `.deployment/retail-cli-20261030-143456/results.json`.

This 30-case harness excludes private PDFs by design and keeps quota/history in memory. It is not browser or authenticated HTTP testing. No prompt/model/index override was used in the final run.

**Nine authenticated HTTP questions passed** (3, 18, 23, 6, 10, 14, 24, 25, 26), including the three original regression cases. Actual JWT authorization, five published-policy reads with index fields withheld, archived-policy exclusion and persisted history were checked. The invitation-suppressed disposable identity was deleted through the application and its cleanup confirmed. No owner account, owner session or owner private PDF was changed. Evidence: `.deployment/retail-http-acceptance.json` and `.deployment/retail-test-cleanup.json`.

Public website and health endpoint returned HTTP 200. The frontend served HSTS, CSP, nosniff and no-referrer headers. Live operational readback confirmed CloudFront Deployed, the owner's verified administrator account and the confirmed SNS email subscription. This does not prove actual email alert delivery. Evidence: `.deployment/refinement-public-http.json` and `.deployment/refinement-operational-status.json`.

## Earlier runs and limits

The earlier 497fd291 release had three substantive answer-quality issues. Intermediate ca018476 fixed them and passed nine authenticated HTTP questions, but its 30-case text-JSON run had one rejected invalid response (case 9). That failure motivated the structured schema in the current release. Candidate, failed transport and superseded runs remain evidence, not additional passes. Summary: `.deployment/answer-refinement-verification.json`.

Browser-control processes failed to start; no newly automated browser navigation or visual acceptance is claimed. The earlier 39-check upload/OCR/isolation acceptance run is historical and was not fully repeated on this release. Password recovery, actual alert delivery and load/availability claims remain unverified by this follow-up.

Five retail policies are explicitly fictional DEMO material. The conflicting legacy 30-day DEMO refund policy remains reversibly archived with its backup; historical conversation excerpts and private PDFs were preserved. No real commercial policy has been approved. Complete the operator identity/contact/effective-date information and have the shop approve real terms before serving real transactions. The application has no order, inventory, payment or carrier integration; staff handle actual transaction decisions. Shared policies are global for a single-shop pilot; multiple shops need tenant isolation first.

## Cost sample and usage guide

Using the saved Tokyo pricing snapshot, this 30-question run used 84,368 input and 21,473 output tokens, estimating **USD 0.1045** for generation or **USD 6.97 for 2,000 comparable questions**. This supersedes the earlier USD 4.86 sample estimate for the shorter prompt. It excludes embeddings, infrastructure, OCR, storage, taxes and different request sizes, and is not an actual bill or hard spending cap. The USD 50 notification budget and existing quotas are unchanged.

Vietnamese operator instructions: [Hướng dẫn vận hành](HUONG-DAN-VAN-HANH.md).
