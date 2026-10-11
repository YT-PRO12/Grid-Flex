#!/usr/bin/env python3
"""Post-deployment end-to-end AWS verifier. Read-only apart from an API-created demo run.

Usage: python scripts/verify_live_aws.py --api-url https://XXXX.execute-api.REGION.amazonaws.com --table-name TABLE
Requires AWS credentials with sts:GetCallerIdentity and dynamodb:GetItem to prove actual persistence.
No credential, cloud deployment, or live verification is claimed by this source file.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--api-url',required=True,help='Live AWS API Gateway base URL')
    ap.add_argument('--table-name',required=True,help='Physical DynamoDB table name from CloudFormation output')
    ap.add_argument('--region',help='AWS region (optional; otherwise default profile)')
    args=ap.parse_args()
    base=args.api_url.rstrip('/')
    if not base.startswith('https://'):
        ap.error('HTTPS API URL required')
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
        session=boto3.Session(region_name=args.region)
        identity=session.client('sts').get_caller_identity()
        print('Authenticated AWS caller:',identity['Arn'].split(':')[0]+':***')
        def api(method,path,data=None):
            req=urllib.request.Request(base+path,method=method,
              headers={'Content-Type':'application/json'},data=json.dumps(data).encode() if data is not None else None)
            with urllib.request.urlopen(req,timeout=45) as response:
                return response.status,json.load(response)
        status,health=api('GET','/api/health')
        assert status==200 and health.get('environment')=='aws-lambda',f'Not running in Lambda: {health}'
        assert health.get('storage')=='aws-dynamodb-configured-unverified','DynamoDB not configured'
        print('PASS: AWS Lambda + API Gateway health confirmed')
        status,payload=api('POST','/api/optimize',{'preset':'grid-stress'})
        assert status==200 and payload['verification']['cost']['passed'], 'Optimization failed validation'
        run_id=payload['run_id']
        table=session.resource('dynamodb').Table(args.table_name)
        item=table.get_item(Key={'pk':run_id},ConsistentRead=True).get('Item')
        assert item, 'Optimization API returned success without DynamoDB persistence'
        saved=json.loads(item['payload'])
        assert saved['id']==run_id and saved['verified'], 'Persisted run invalid or mismatched'
        assert len(saved['strategies'])==3, 'Strategy plans absent in saved DynamoDB record'
        print('PASS: Live API optimization, independent physical verification, DynamoDB read-back')
        print('VERIFIED CLOUD INTEGRATION. Run ID:',run_id)
        print('Synthetic sample cost: INR',payload['optimized']['metrics']['total_cost_inr'])
        return 0
    except (Exception,) as exc:
        print('FAIL: Cloud verification incomplete:',type(exc).__name__,str(exc),file=sys.stderr)
        return 1
if __name__=='__main__':
    sys.exit(main())
