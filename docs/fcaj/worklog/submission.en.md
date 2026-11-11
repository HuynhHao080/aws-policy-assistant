---
title: "Policy Assistant submission pack"
weight: 0
---

## Four links for the presentation

1. The [AWS application](https://djreo5eptvwk5.cloudfront.net/) runs with DEMO policies for an accessories shop.
2. The [bilingual proposal]({{< relref "/2-Proposal/CurrentSolution" >}}) covers the problem, scope, architecture, risks and cost inputs.
3. The [source and README](https://github.com/HuynhHao080/aws-policy-assistant) include the AWS SAM template, tests and operator instructions.
4. The [staff operator guide](https://github.com/HuynhHao080/aws-policy-assistant/blob/6225d5c66ed5f114be1e3cf004df937ab0e58f67/docs/HUONG-DAN-PHOI-HOP-HO-TRO.md) describes the workflow. [API and artifact evidence]({{< relref "/5-Workshop/5.7-PolicyAssistant/SupportTeam" >}}).

## Local lab

Clone the application repository, install Python 3.12 and Node.js 22, then open PowerShell in the new repository.

```powershell
py -3.12 -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r policy_assistant/requirements.txt -r tests/requirements.txt
Remove-Item Env:AWS_SAM_STACK_NAME, Env:POLICY_ASSISTANT_ID_TOKEN -ErrorAction SilentlyContinue
& ./.venv/Scripts/python.exe -m pytest tests -q
npm ci --prefix frontend --ignore-scripts
npm run build --prefix frontend
npm test --prefix frontend
```

Check each command’s exit code. Python tests use mocked services and frontend tests use a simulated DOM. The built interface can be inspected locally. The example configuration has blank Cognito connection settings. [Reproduction guide](https://github.com/HuynhHao080/aws-policy-assistant/tree/main/docs/reproducibility).

## Four-minute demonstration

| Time | Action and explanation |
|---|---|
| 0:00–0:40 | Open the app and explain the DEMO shop scope. Walk through your diagram from browser to CloudFront, Cognito and API. |
| 0:40–1:40 | Use a test account, ask about charger warranty and inspect the cited source. Ask about warranty shipping fees to show a gap in policy coverage. Read and check the actual response. |
| 1:40–2:50 | Submit a synthetic support request. As administrator, claim it and add a note. Return to the customer account and compare the visible conversation. |
| 2:50–4:00 | Explain PDF ownership, concurrent revisions, queues and cleanup. Open the evidence and identify the checks you performed. |

Hide tokens, presigned upload URLs and account details in the recording. If a step fails, record the cause and present dated evidence with its original scope. Remove test data through account or item deletion after the demo.

## Items to complete before submission

| Item | Student action |
|---|---|
| Architecture | Draw your AWS flows and practise explaining identity boundaries, Singapore/Japan, failure and retry. [Review worksheet](https://github.com/HuynhHao080/aws-policy-assistant/blob/main/docs/fcaj/ARCHITECTURE-REVIEW-WORKSHEET.md). |
| COST | Enter proposal assumptions into Calculator and save the total, date and share URL or export. Target budget is USD 30–50/month. [Cost inputs]({{< relref "/2-Proposal/CurrentSolution" >}}). |
| Demo | Perform it personally and capture evidence with the date of the check. |
| Worklog and evidence | Review daily entries, published blog posts and event evidence, then add actual links. [Evidence review]({{< relref "/0-Audit/student-evidence" >}}). |

This technical material used AI assistance. Review the submission, identify your personal contributions and refer to the [FCAJ workshop requirements](https://hcm-rules.awsfcaj.com/3-project/).
