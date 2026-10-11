#!/usr/bin/env python3
"""Owner-run local or HTTPS API smoke test. No credentials needed; creates one demo run."""
import argparse
import json
from urllib.request import Request, urlopen

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--api-url',default='http://localhost:8000')
    args=parser.parse_args()
    base=args.api_url.rstrip('/')
    def call(path,body=None):
        req=Request(base+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=35) as response:return json.load(response)
    health=call('/api/health');assert health['data']=='synthetic'
    run=call('/api/optimize',{'battery_wear_cost':8})
    assert all(v['passed'] for v in run['verification'].values())
    result=call('/api/intelligence',{'battery_wear_cost':8,'strategy':'cost','plan':run['optimized']})
    assert result['current']['verification']['passed']
    assert result['current']['stress']['tested_count']==5
    assert result['battery']['verification']['passed']
    assert result['battery']['with_wear']['throughput_kwh']<result['battery']['without_wear']['throughput_kwh']
    print('PASS: health, three strategies, constraint audits, five solar stresses, battery sensitivity.')
    print('Environment:',health['environment'],'Storage:',health['storage'])
    print('This HTTP check alone does not prove DynamoDB persistence; use verify_live_aws.py after deployment.')

if __name__=='__main__':main()
