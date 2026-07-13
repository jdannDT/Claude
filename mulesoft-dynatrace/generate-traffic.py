#!/usr/bin/env python3
"""
MuleSoft log traffic generator → Dynatrace Logs Ingest API

Generates realistic log events for all four MuleSoft log types:
  - CloudHub app logs (Log4j2 JSON)
  - Flex Gateway access logs
  - Flex Gateway runtime logs
  - Anypoint audit logs

Usage:
  # Dry run — print to stdout only
  python3 generate-traffic.py

  # Send to Dynatrace
  DT_ENV=abc12345 DT_TOKEN=dt0c01.xxx python3 generate-traffic.py --send

  # Continuous load test
  python3 generate-traffic.py --send --rate 10 --duration 60
"""

import argparse
import json
import random
import time
import uuid
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import URLError

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
APPS       = ["payment-service", "order-api", "inventory-sync", "customer-portal", "notification-hub"]
FLOWS      = ["mainFlow", "errorHandler", "processOrderFlow", "validatePaymentFlow", "retryFlow"]
APIS       = ["Orders API", "Payments API", "Inventory API", "Customer API"]
METHODS    = ["GET", "POST", "PUT", "DELETE", "PATCH"]
PATHS      = ["/api/v1/orders", "/api/v1/orders/{id}", "/api/v1/payments",
              "/api/v1/customers", "/api/v1/inventory/items", "/health", "/metrics"]
ENVS       = ["Production", "Staging", "Development"]
ORGS       = ["org-acme-prod", "org-acme-nonprod"]
USERS      = ["jsmith", "alopez", "mchen", "rdesai", "automated-deploy"]
AUDIT_ACTS = ["Deploy", "Undeploy", "Restart", "UpdateConfig", "CreateApplication", "DeleteApplication"]
OBJ_TYPES  = ["Application", "API", "Environment", "Organization", "Policy"]
LOGGERS    = [
    "org.mule.runtime.core.internal.processor.LoggerMessageProcessor",
    "org.mule.runtime.module.artifact.activation.internal.deployable.AbstractDeployableProjectModel",
    "com.mulesoft.modules.batch.engine.DefaultBatchEngine",
    "org.mule.runtime.core.api.retry.policy.RetryPolicyTemplate",
    "io.github.resilience4j.circuitbreaker.internal.CircuitBreakerStateMachine",
]
MESSAGES = {
    "INFO":  ["Request received", "Response sent", "Message processed successfully",
               "Flow execution completed", "Batch job started", "Connection acquired from pool"],
    "WARN":  ["Retry attempt 1 of 3", "Connection pool near capacity",
               "Response time exceeded threshold", "Circuit breaker half-open"],
    "ERROR": ["NullPointerException in flow execution", "Connection refused: downstream timeout",
               "CONNECTIVITY:CONNECTIVITY failed to establish connection",
               "HTTP:BAD_REQUEST Invalid payload schema", "Unable to acquire connection from pool"],
    "DEBUG": ["Entering flow", "Attribute set", "Transformer applied", "Router evaluated"],
}

# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def ts_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

def correlation_id():
    return str(uuid.uuid4())

def app_log(env=None, app=None, error_spike=False):
    env  = env  or random.choice(ENVS)
    app  = app  or random.choice(APPS)
    flow = random.choice(FLOWS)
    weights = [0.02, 0.08, 0.85, 0.05] if not error_spike else [0.25, 0.25, 0.40, 0.10]
    level = random.choices(["ERROR", "WARN", "INFO", "DEBUG"], weights=weights)[0]
    return {
        "timestamp":      ts_now(),
        "level":          level,
        "loggerName":     random.choice(LOGGERS),
        "threadName":     f"[MuleRuntime].uber.{random.randint(1,8):02d}",
        "correlationId":  correlation_id(),
        "processorPath":  f"{flow}/processors/{random.randint(0,5)}",
        "appName":        app,
        "environment":    env,
        "organizationId": random.choice(ORGS),
        "message":        random.choice(MESSAGES[level]),
    }

def gateway_access_log(env=None, api=None, error_spike=False):
    env    = env or random.choice(ENVS)
    api    = api or random.choice(APIS)
    method = random.choice(METHODS)
    path   = random.choice(PATHS)
    weights = [0.60, 0.15, 0.08, 0.05, 0.04, 0.04, 0.02, 0.02] if not error_spike \
              else [0.30, 0.10, 0.15, 0.08, 0.08, 0.15, 0.08, 0.06]
    status = random.choices([200, 201, 400, 404, 429, 500, 502, 503], weights=weights)[0]
    dur    = max(1, random.lognormvariate(3.5, 0.8))  # ~33ms median
    upstream_dur = max(1, dur - random.uniform(2, 10))
    violations = random.choices([0, 1, 2], weights=[0.92, 0.06, 0.02])[0]
    return {
        "timestamp":             ts_now(),
        "method":                method,
        "path":                  path,
        "status":                status,
        "bytes_sent":            random.randint(200, 50000),
        "duration_ms":           round(dur, 2),
        "upstream_duration_ms":  round(upstream_dur, 2),
        "upstream_status":       status if status < 500 else random.choice([500, 502, 503, 504]),
        "client_ip":             f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
        "api_id":                str(uuid.uuid4())[:8],
        "api_name":              api,
        "api_version":           "v1",
        "policy_violations":     violations,
        "correlation_id":        correlation_id(),
    }

def gateway_runtime_log(env=None):
    env   = env or random.choice(ENVS)
    level = random.choices(["ERROR", "WARN", "INFO"], weights=[0.05, 0.15, 0.80])[0]
    msg   = random.choice(MESSAGES[level])
    ts    = ts_now()
    return {
        "timestamp": ts,
        "content":   f"{ts} {level:<5} [{random.choice(LOGGERS)}] {msg}",
        "log.source": "flex-gateway",
        "mule.environment": env,
    }

def audit_log(env=None):
    env     = env or random.choice(ENVS)
    action  = random.choice(AUDIT_ACTS)
    success = random.choices([True, False], weights=[0.92, 0.08])[0]
    return {
        "requestId":      str(uuid.uuid4()),
        "userId":         f"usr-{random.randint(1000,9999)}",
        "userName":       random.choice(USERS),
        "organizationId": random.choice(ORGS),
        "environmentId":  f"env-{env.lower()[:4]}-{random.randint(100,999)}",
        "objectType":     random.choice(OBJ_TYPES),
        "objectId":       str(uuid.uuid4())[:8],
        "objectName":     random.choice(APPS),
        "action":         action,
        "timestamp":      ts_now(),
        "success":        success,
        "properties": {
            "status": "STARTED" if success else "FAILED",
            "region": random.choice(["us-east-1", "eu-west-1", "ap-southeast-1"]),
        },
    }

# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

def batch_for_ingest(records: list[dict], log_source_hint: str) -> list[dict]:
    """Wrap records in Dynatrace log ingest envelope."""
    out = []
    for r in records:
        entry = {
            "timestamp": r.get("timestamp", ts_now()),
            "content":   json.dumps(r),
            "log.source": log_source_hint,
        }
        # promote a few top-level attributes DT can use for filtering without parsing
        for k in ("mule.environment", "mule.app", "appName", "api_name", "environment"):
            if k in r:
                entry["mule.environment"] = r.get("environment") or r.get("mule.environment", "")
                break
        out.append(entry)
    return out

def send_to_dynatrace(url: str, token: str, records: list[dict]):
    payload = json.dumps(records).encode()
    req = Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Api-Token {token}",
            "Content-Type":  "application/json; charset=UTF-8",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            return resp.status, resp.read().decode()
    except URLError as e:
        return None, str(e)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="MuleSoft log traffic generator")
    p.add_argument("--send",     action="store_true", help="POST to Dynatrace (requires DT_ENV + DT_TOKEN env vars)")
    p.add_argument("--rate",     type=int, default=5,  help="Events per second (default: 5)")
    p.add_argument("--duration", type=int, default=30, help="Run duration in seconds (default: 30, 0=unlimited)")
    p.add_argument("--spike",    action="store_true",  help="Inject error spike at midpoint")
    p.add_argument("--env",      default=None, help="Lock to one environment")
    p.add_argument("--app",      default=None, help="Lock to one application")
    p.add_argument("--api",      default=None, help="Lock to one API name")
    return p.parse_args()

def main():
    import os
    args = parse_args()

    dt_env   = os.environ.get("DT_ENV", "")
    dt_token = os.environ.get("DT_TOKEN", "")
    ingest_url = f"https://{dt_env}.live.dynatrace.com/api/v2/logs/ingest" if dt_env else ""

    if args.send and not (dt_env and dt_token):
        print("ERROR: Set DT_ENV and DT_TOKEN environment variables to send data.")
        raise SystemExit(1)

    print(f"{'Sending' if args.send else 'Dry-run'} | rate={args.rate}/s | duration={'∞' if args.duration == 0 else args.duration}s")
    if args.send:
        print(f"  → {ingest_url}")
    print()

    start    = time.time()
    total    = 0
    interval = 1.0 / args.rate

    try:
        while True:
            elapsed     = time.time() - start
            error_spike = args.spike and args.duration and (args.duration * 0.4 < elapsed < args.duration * 0.6)

            # Weight log types realistically: gateway access heaviest, audit lightest
            log_type = random.choices(
                ["app", "gw_access", "gw_runtime", "audit"],
                weights=[0.35, 0.45, 0.12, 0.08]
            )[0]

            if log_type == "app":
                record = app_log(env=args.env, app=args.app, error_spike=error_spike)
                source = "cloudhub-app"
            elif log_type == "gw_access":
                record = gateway_access_log(env=args.env, api=args.api, error_spike=error_spike)
                source = "flex-gateway"
            elif log_type == "gw_runtime":
                record = gateway_runtime_log(env=args.env)
                source = "flex-gateway"
            else:
                record = audit_log(env=args.env)
                source = "anypoint-audit"

            total += 1
            ts = record.get("timestamp", ts_now())

            if args.send:
                wrapped = batch_for_ingest([record], source)
                status, body = send_to_dynatrace(ingest_url, dt_token, wrapped)
                status_str = str(status) if status else "ERR"
            else:
                status_str = "DRY"

            # Print one-liner summary
            if log_type == "app":
                label = f"APP  [{record['level']:<5}] {record['appName']} / {record['processorPath'].split('/')[0]}"
            elif log_type == "gw_access":
                label = f"GW   [{record['status']}] {record['method']:<6} {record['path']} {record['duration_ms']:.0f}ms"
            elif log_type == "gw_runtime":
                lvl = record["content"].split()[1] if record.get("content") else "???"
                label = f"GWRT [{lvl:<5}] {record['content'].split(']')[-1].strip()[:60]}"
            else:
                label = f"AUDT [{record['action']:<18}] {record['userName']} success={record['success']}"

            spike_tag = " [SPIKE]" if error_spike else ""
            print(f"[{ts}] {status_str} {label}{spike_tag}")

            if args.duration and elapsed >= args.duration:
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        pass

    print(f"\nDone. Sent {total} records in {time.time()-start:.1f}s.")

if __name__ == "__main__":
    main()
