# Private PDF text reader

The reader opens a processed PDF's extracted text from the library or the page cited in an answer. It supports previous/next, page jumps, accent-insensitive find with highlighted matches, and copying or downloading the displayed fragments as TXT. The library filters loaded records by name and processing state.

The authenticated API reads the pinned S3 extraction version and checks the document owner and state. Each page returns up to 20,000 characters. Fragments can overlap, and blank pages can have no extracted text. The preview is cleared when the login session expires.

| Verification | Result |
|---|---|
| Python suite | 337 passed, 11 opt-in live tests skipped |
| Frontend suite | 77 passed, including search highlighting, TXT download and late-response cleanup in simulated DOM |
| SAM | Validate and build passed |
| AWS | CloudFormation UPDATE_COMPLETE and six Lambda hashes matched |
| Live HTTP | Nine checks passed with a synthetic two-page text PDF |
| Cleanup | Disposable test account removal confirmed |

The HTTP checks covered upload, submit, document readiness, anonymous rejection, pre-processing rejection, both page payloads, and an out-of-range page. The fixture used text extraction and made zero Bedrock or OCR requests. DOM checks exercised the controls with synthetic browser state. Code SHA-256 `4f9cf0c521bd3bae42d1c52e58ef87c97e773499f7d89b490f8dd43f39fffc44`.
