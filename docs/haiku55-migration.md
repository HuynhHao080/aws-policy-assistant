# Global Claude Haiku 5.5 — cutover on 11 November 2026

The primary Policy Assistant stack calls `global.anthropic.claude-haiku-5-5` from Singapore (`ap-southeast-1`). This is the sole Bedrock model available to the application. The CloudFormation parameter accepts this profile and the API role's InvokeModel resources match the profile ARN and its two foundation model ARNs returned by Bedrock. The worker role has zero Bedrock grants. [AWS model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-5-5.html)

PDF extraction and OCR still produce text. The assistant ranks the authorized extracted text and active published policies by terms, normalizing Vietnamese accents and expanding a small shop glossary. Older PDF indexes can be read using their text fields. This removes the second model call and its token charges. Lexical ranking can miss paraphrases and cross-language matches beyond the glossary. Textract performs OCR in Singapore.

The API calls Converse with one answer-formatting tool, 900 output tokens, disabled thinking and low effort. It validates the answer length and IDs against the retrieved excerpts, then checks cited policy validity before saving history. The client makes one inference attempt per answer. Global routing can process questions and selected excerpts in AWS Regions outside Singapore. The updated privacy page was published before the model cutover. [AWS Claude tool use](https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages-tool-use.html)

| Check | Result |
|---|---|
| Bedrock control plane | Global profile ACTIVE, account model access AUTHORIZED |
| CloudFormation | UPDATE_COMPLETE, 6 Lambda code hashes matched, removed embedding parameter absent |
| IAM | API role matched 3 Haiku resources, worker role had zero Bedrock grants |
| Local verification | 335 Python passed, 11 live tests skipped, 72 frontend passed, SAM validate and build passed |
| Provider inference | Pending a user-run live answer. Cutover verification made zero inference calls |

Code SHA-256: `f227be8f4c016f145281048803bb168c7756dd92466c92e6049468950451ad32`

Template SHA-256: `d02358ac6fb9ddffb4d9431ba608bd6d87c3b69f38a7fba9d1a6abbd517e52f0`

For the demo, sign in and ask a question about a published DEMO policy. Open the citation and verify that its excerpt supports the answer. For a PDF demo, select **Hỏi từ PDF này** and check the cited page. Old conversations and dated evidence retain the model and results recorded at the time. For cost estimates, use the Global Haiku 5.5 rates for the Singapore source Region and the measured input/output token volume. [Cost inputs](fcaj/COST-ASSUMPTIONS.md)
