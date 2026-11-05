# Policy validity and cited-source checks — 2026-11-05

Delivered on the selected primary [Policy Assistant](https://djreo5eptvwk5.cloudfront.net/), stack`policy-assistant`. Source feature commit[5498d92](https://github.com/HuynhHao080/aws-policy-assistant/commit/5498d928f005f82de2ea96ddadf9e58cef70bcd7); [GitHub CI succeeded](https://github.com/HuynhHao080/aws-policy-assistant/actions/runs/42056109331).

## Behavior

- Inclusive optional Vietnam UTC+07business dates on published policies, separate from drafts and UTC quota periods; strict calendar/order validation and compatible undated legacy rows.
- Administrator active/upcoming/expired/invalid filters, visible current/draft windows and repairable malformed legacy dates. Empty date fields explicitly remove bounds on subsequent publication; omission by older clients preserves existing bounds.
- Public exact/search/RAG eligibility checks and consistent rereads of cited policy facts before answer persistence. Changed/hidden/expired/deleted facts detected then return409with no saved answer or automatic regeneration. Isolated draft changes do not invalidate unchanged published facts. Internal fingerprints are not exposed.
- This is point-in-time validation, not an atomic policy/history lock or factual-accuracy guarantee. Historic answers remain snapshots. A runtime rollback must retain validity checks once real bounded publications exist.

## Verification actually performed

- **298Python passed,11opt-in live skipped**, including25new business-date/draft/cursor/race cases. Simulated model callbacks change a policy before final checking; these are mocked generation cases, not a real model acceptance run.
- **59frontend passed**, including5new validation/editor/filter/repair cases with synthetic DOM. Production build succeeded. No real-browser visual/mobile acceptance is claimed.
- SAM build and lint validation passed. Both original and processed CloudFormation template comparisons contain exactly6changed artifact keys. CloudFormation lists12dependent resources, but all other processed properties are identical; no new route, IAM grant, table/index, scheduler, service, model, budget or quota was added.
- Reviewed/executed change set`public-final-1793892751`; stack returned`UPDATE_COMPLETE`. Code SHA256`eac3c36873381d674db6fb9ab2161925fce3d417f997e42252eb142bc0bd72bd`; template SHA256`79e5ee37f28212e3b163a8143a110254976d7804d272ad3e46d9c1ad77635056`.
- **16live API checks passed**, using one invitation-suppressed disposable identity and3nonce-owned policy rows. Exact artifact/module checks preceded writes. The rows were upcoming(year9000), expired(year2000) or invalid and never current; no customer transaction policy was published. Permission separation, public404s, admin filters/status, impossible-date400, revision409and draft isolation were checked.
- The identity was deleted through the application account workflow; all3temporary policies were conditionally deleted and verified absent. `http_passed`, `accounts_cleaned`, `policies_cleaned` are true. No `/ask`, publish, embedding, model, OCR or PDF operation was called in this live acceptance. Operator-seeded rows/read/draft tests do not establish live generation or publication acceptance.
- Frontend republished; CloudFront invalidation`IIJS4K7YG4HI73FKTSSG7GQYG` completed. **37frontend files and6Lambda hashes match** the local release; distribution`Deployed`.

Reports: [API/cleanup flags](policy-validity-live-acceptance.json), [template review](policy-validity-template-review.json), [artifact verification](policy-validity-artifact-verification.json). Detailed ignored cleanup/operator logs remain in `.deployment/policy-validity`; they do not include passwords/JWTs. Prior accepted quality/pilot/browser reports and historical canary state are preserved separately.

## Practical use and limits

[Vietnamese operator guide](HUONG-DAN-HIEU-LUC-CHINH-SACH.md) includes a reproducible demo, UTC+07examples, filtered pagination, quota behavior and rollback compatibility. Additional final reads are bounded by at most5distinct cited policy IDs. No work/model call is scheduled at a date boundary. Publication still uses the existing embedding pipeline.

Business content remains DEMO pending real operator approval. This extension does not resolve contradictions between policies, choose historical-order eligibility, provide a full policy-version archive, guarantee factual accuracy or establish load/restore/SLA results. Student authorship, actual blogs/participation, final diagram and Calculator remain personal evidence.
