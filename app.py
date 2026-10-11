"""Shared API logic for local HTTP server and AWS Lambda (API Gateway HTTP API v2)."""
import json
import logging
import os
import time
import uuid
from engine.intelligence import analyze
from engine.scenario import scenario
from engine.optimizer import OptimizationError, optimize

_LOCAL_RUNS = []
MAX_JSON_BYTES = 16384


def status_payload():
    configured = bool(os.environ.get("RUNS_TABLE"))
    return {
        "name":"Grid Flex", "service":"operational", "storage":"aws-dynamodb-configured-unverified" if configured else "local-ephemeral",
        "environment":"aws-lambda" if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") else "local",
        "solver":"SciPy HiGHS MILP", "data":"synthetic", "aws_lambda_runtime":bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME")),
        "cloud_integration_verified":False, # This status endpoint alone cannot prove a write/read succeeded.
        "service_version":"3.0.0",
    }


def dynamodb_table():
    import boto3
    return boto3.resource('dynamodb').Table(os.environ['RUNS_TABLE'])


def _record(entry):
    if os.environ.get('RUNS_TABLE'):
        dynamodb_table().put_item(Item={"pk":entry["id"],"created_at":entry["created_at"],"payload":json.dumps(entry,separators=(',',':')),"expires_at":int(time.time())+7*24*3600})
    else:
        _LOCAL_RUNS.insert(0, entry)
        del _LOCAL_RUNS[10:]


def _history():
    if os.environ.get('RUNS_TABLE'):
        result=dynamodb_table().scan(Limit=50)
        entries=[]
        for item in result.get('Items',[]):
            try: entries.append(json.loads(item['payload']))
            except (KeyError,ValueError,TypeError): continue
        return sorted(entries,key=lambda x:x['created_at'],reverse=True)[:10]
    return _LOCAL_RUNS[:]


def route(method,path,body=None):
    """Return HTTP status and JSON-compatible dictionary; never expose tracebacks."""
    try:
        if method=='GET' and path in ('/api/health','/health'):
            return 200,status_payload()
        if method=='GET' and path=='/api/scenario':
            return 200,scenario()
        if method=='GET' and path=='/api/history':
            return 200,{"runs":_history()}
        if method=='POST' and path in ('/api/optimize','/api/intelligence'):
            if not isinstance(body,dict):return 400,{"error":"Expected JSON object"}
            allowed={"preset","solar_scale","tariff_multiplier","initial_soc","carbon_price","demand_scale","battery_capacity","evening_grid_cap","battery_wear_cost"}
            if path=='/api/intelligence': allowed.update(("strategy","plan"))
            extra=set(body)-allowed
            if extra:return 400,{"error":"Unsupported fields: "+', '.join(sorted(extra))}
            inputs = dict(body)
            strategy = inputs.pop("strategy", "cost")
            supplied_plan = inputs.pop("plan", None)
            config=scenario(**inputs)
            if path=='/api/intelligence':
                return 200,analyze(config,strategy,supplied_plan)
            result=optimize(config)
            result['run_id']=str(uuid.uuid4())
            result['created_at']=int(time.time())
            _record({"id":result['run_id'],"created_at":result['created_at'],"preset":config['preset'],"comparison":result['comparison'],"optimized":result['optimized']['metrics'],"baseline":result['baseline']['metrics'],
                     "strategies":{name:plan["metrics"] for name,plan in result["strategy_plans"].items()},
                     "controls":body,"schema_version":3,
                     "verified":all(v["passed"] for v in result["verification"].values())})
            return 200,result
        return 404,{"error":"Unknown route"}
    except (ValueError,TypeError,OptimizationError) as exc:
        return 422,{"error":str(exc)}
    except Exception:
        logging.exception("Grid Flex request failed: %s %s",method,path)
        return 500,{"error":"Unexpected internal error; check server logs and deployment configuration"}


def lambda_handler(event,context):
    request_context=event.get('requestContext',{})
    method=request_context.get('http',{}).get('method',event.get('httpMethod','GET')).upper()
    path=event.get('rawPath',event.get('path','/'))
    body=None
    if method=='POST':
        raw=event.get('body','') or '{}'
        if len(raw.encode('utf-8'))>MAX_JSON_BYTES:
            code,payload=413,{"error":"Request exceeds 16 KB"}
            return _lambda_response(code,payload)
        try:
            if event.get('isBase64Encoded'):
                import base64
                raw=base64.b64decode(raw).decode('utf-8')
            body=json.loads(raw)
        except (ValueError,TypeError,UnicodeError):
            return _lambda_response(400,{"error":"Invalid JSON"})
    code,payload=route(method,path,body)
    return _lambda_response(code,payload)


def _lambda_response(code,payload):
    return {"statusCode":code,"headers":{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"},"body":json.dumps(payload,separators=(',',':'))}
