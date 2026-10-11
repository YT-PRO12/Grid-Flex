# Owner-run deployment

Status: locally verified source; no account connected, resources created or live AWS verification performed. The SAM CLI/container build was unavailable in the finalization environment and must be run by the owner.

## Build and deploy (project root)

Use Python 3.12, Docker, AWS CLI and AWS SAM CLI. Requirements pin the locally tested NumPy 2.3.5 and SciPy 1.17.0. SciPy includes native libraries: **build for Linux x86_64 in the SAM container**, not with Windows wheels. Lambda supplies boto3; install boto3 locally only for the optional live persistence verifier.

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
sam validate --lint --template-file aws/template.yaml
sam build --use-container --template-file aws/template.yaml
sam local start-api --template .aws-sam/build/template.yaml
```

The local SAM API needs a reachable DynamoDB table for `/api/optimize` writes. For fully offline smoke testing use `python server.py` instead. Once authenticated in the owner's intended AWS profile/region:

```powershell
aws sts get-caller-identity
sam deploy --guided --stack-name grid-flex-demo --capabilities CAPABILITY_IAM
```

Supply `AllowedOrigin` with the **exact HTTPS frontend origin**, no trailing slash (e.g. `https://your-site.example`). Use the actual `ApiBaseUrl` and `DynamoDBTable` outputs. Upload only `web/` to the owner's static HTTPS host; the backend template does not host the frontend. Open that site with `?api=ACTUAL_API_BASE_URL`. No build step is needed for the frontend.

## Runtime contract

- Python 3.12 / x86_64, 1024 MB, Lambda timeout 30 seconds. Each MILP has a five-second limit: optimization has four solves; intelligence has up to three (two when the validated current plan is supplied). Time-limited feasible solutions are labeled honestly. Cold starts, build size and deployed latency still need owner verification.
- GET `/api/health`, `/api/scenario`, `/api/history`; POST `/api/optimize`, `/api/intelligence`. API Gateway handles OPTIONS/CORS for the configured origin; direct Lambda responses need no duplicate CORS headers.
- `RUNS_TABLE` is wired by SAM. Leave it unset for ephemeral local runs. `PORT` optionally changes the local server's default 8000. No secrets belong in frontend code.
- Optimization writes one compact DynamoDB record: `pk` (run UUID), `created_at` (epoch seconds), `payload` (JSON string), `expires_at` (epoch seconds, seven-day TTL). Payload schema version 3 includes original requested controls, metrics for three strategies and verification status. Full dispatch/intelligence is returned to the caller and is not persisted. Pins are browser-session only.
- History scans at most 50 records and sorts that sample; it is not guaranteed to be the globally latest ten records. DynamoDB TTL deletion is asynchronous.
- Errors: 400 malformed JSON/unknown fields, 413 body above 16 KiB, 422 invalid controls/no feasible schedule/invalid submitted plan, 500 unexpected errors or failed persistence. Exceptions go to operational logs without returning stack traces. Conservative-plan failure is reported inside an otherwise successful intelligence response.
- Public demonstration API: rate 3 requests/sec, burst 10; no authentication. Restricted CORS is not authentication. Review compute costs and access policy before public operation.

## Owner smoke checks

```powershell
python scripts/smoke_test.py --api-url "ACTUAL_API_BASE_URL"
python -m pip install boto3
python scripts/verify_live_aws.py --api-url "ACTUAL_API_BASE_URL" --table-name "ACTUAL_TABLE_NAME" --region "ACTUAL_REGION"
```

`smoke_test.py` checks health, three objective strategies, solar stress and wear sensitivity. `verify_live_aws.py` additionally requires owner credentials and checks DynamoDB with strongly consistent GetItem. Neither script creates infrastructure. Test browser CORS from the exact frontend origin, inspect Lambda logs/latency, and confirm native-library cold starts before claiming deployment works. These live checks have **not** been performed here.
