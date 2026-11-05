# Vietnamese typography fix — 2026-11-04

Body text used Trebuchet MS/Verdana while headings used self-hosted Noto Serif. The installed Trebuchet cmap lacks 69 characters from the Vietnamese/currency verification sample, causing mixed-font fallback. Body/form controls now use self-hosted Noto Sans variable weights100–900 with Segoe UI/sans-serif fallback. Headings retain Noto Serif; heading/control line heights were increased to give diacritics room.

The 206,952-byte WOFF2 subset includes Latin/Latin Extended, combining marks, Vietnamese precomposed characters, punctuation and currency. Both composed and decomposed Vietnamese sample coverage and variable weights400–700 were verified from actual font tables. Source SHA256, subset SHA256 and Unicode ranges are in [font-verification.json](font-verification.json). Official Noto Sans OFL is retained in source and copied into the production build.

Frontend build and all28 existing frontend tests passed. Latest CSS: app-PSDZKCHG.css; JavaScript unchanged: app-ACG7Q3OL.js. No backend code, API, data, IAM or model change. Publication/hash verification is recorded in font-artifact-verification.json. No new visual/browser acceptance is claimed because the previously declined browser-origin permission remains in effect.
