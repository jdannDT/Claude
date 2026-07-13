# MuleSoft Anypoint — Dynatrace Log Processing Rules

Four rules, one per log type. In Dynatrace: **Settings → Log Monitoring → Log processing → Add rule**.
Order matters — place these before any generic Java/Log4j catch-all rules.

---

## Rule 1 — CloudHub 2.0 App Logs (Log4j2 text layout)

**Name:** `MuleSoft - CloudHub App Log`

**Matcher** (applies this rule only to MuleSoft app logs):
```
log.source contains "cloudhub" OR
matchesPhrase(content, "[processor:") OR
matchesPhrase(content, "[event:")
```

**Sample log line:**
```
INFO  2024-01-15 10:23:45,123 [[MuleRuntime].uber.02: .myapp.CPU_LITE @1a2b3c] [processor: myFlow/processors/0; event: abc-123-def-456] org.mule.runtime.core.internal.processor.LoggerMessageProcessor: Payment processed for order #9981
```

**Processor pipeline (DPL):**
```
PARSE(content,
  "UPPER:mule.level SPACE+ TIMESTAMP('yyyy-MM-dd HH:mm:ss,SSS'):timestamp SPACE
   '[' LD:mule.thread ']' SPACE
   '[processor:' SPACE? LD{min:0,max:200,greedy:false}:mule.flow ';' SPACE
   'event:' SPACE? LD{min:0,max:100,greedy:false}:mule.correlationId ']' SPACE
   LD{min:0,max:300,greedy:false}:mule.logger ':' SPACE?
   LD:mule.message"
)
| FIELDS_ADD(
    log.level: mule.level,
    event.type: "mule.app.log",
    mule.flow: REPLACE_STRING(mule.flow, "/processors/", "→"),
    mule.is_error: if(mule.level == "ERROR", true, else: false)
  )
```

**Alternative: JSON layout** (if your app uses `JsonLayout` in log4j2.xml):
```
PARSE(content, "JSON:parsed")
| FIELDS_ADD(
    mule.level:          parsed[level],
    mule.logger:         parsed[loggerName],
    mule.thread:         parsed[threadName],
    mule.correlationId:  parsed[correlationId],
    mule.flow:           parsed[processorPath],
    mule.app:            parsed[appName],
    mule.environment:    parsed[environment],
    mule.message:        parsed[message],
    log.level:           parsed[level],
    event.type:          "mule.app.log"
  )
```

---

## Rule 2 — Flex / Omni Gateway Access Logs (JSON)

**Name:** `MuleSoft - Gateway Access Log`

**Matcher:**
```
log.source contains "flex-gateway" OR
matchesPhrase(content, "\"api_id\"") OR
matchesPhrase(content, "\"upstream_service_time\"")
```

**Sample log line:**
```json
{"timestamp":"2024-01-15T10:23:45.123Z","method":"GET","path":"/api/v1/orders","status":200,"bytes_sent":1842,"duration_ms":47,"client_ip":"203.0.113.5","api_id":"abcd1234","api_name":"Orders API","api_version":"v1","policy_violations":0,"correlation_id":"x-abc-123","upstream_status":200,"upstream_duration_ms":38}
```

**Processor pipeline (DPL):**
```
PARSE(content, "JSON:gw")
| FIELDS_ADD(
    mule.api.name:             gw[api_name],
    mule.api.id:               gw[api_id],
    mule.api.version:          gw[api_version],
    mule.api.method:           gw[method],
    mule.api.path:             gw[path],
    mule.api.statusCode:       toLong(gw[status]),
    mule.api.upstream.status:  toLong(gw[upstream_status]),
    mule.api.duration_ms:      toDouble(gw[duration_ms]),
    mule.api.upstream.ms:      toDouble(gw[upstream_duration_ms]),
    mule.api.bytes:            toLong(gw[bytes_sent]),
    mule.api.clientIp:         gw[client_ip],
    mule.correlationId:        gw[correlation_id],
    mule.api.policyViolations: toLong(gw[policy_violations]),
    event.type:                "mule.gateway.access",
    mule.is_error:             if(toLong(gw[status]) >= 500, true, else: false),
    mule.is_4xx:               if(toLong(gw[status]) >= 400 AND toLong(gw[status]) < 500, true, else: false),
    log.level:                 if(toLong(gw[status]) >= 500, "ERROR",
                                 else: if(toLong(gw[status]) >= 400, "WARN", else: "INFO"))
  )
```

---

## Rule 3 — Flex / Omni Gateway Runtime Logs (Log4j2 text)

**Name:** `MuleSoft - Gateway Runtime Log`

**Matcher:**
```
log.source contains "flex-gateway" AND
NOT matchesPhrase(content, "\"api_id\"")
```

**Sample log line:**
```
2024-01-15T10:23:45.123Z WARN  [io.github.resilience4j.circuitbreaker.internal.CircuitBreakerStateMachine] Circuit breaker 'Orders API' changed state from CLOSED to OPEN
```

**Processor pipeline (DPL):**
```
PARSE(content,
  "TIMESTAMP('yyyy-MM-dd\'T\'HH:mm:ss.SSS\'Z\''):timestamp SPACE
   UPPER:mule.level SPACE+
   '[' LD{min:0,max:300,greedy:false}:mule.logger ']' SPACE
   LD:mule.message"
)
| FIELDS_ADD(
    log.level:   mule.level,
    event.type:  "mule.gateway.runtime",
    mule.is_error: if(mule.level == "ERROR", true, else: false)
  )
```

---

## Rule 4 — Anypoint Platform Audit Logs (Access Management API → HTTP ingest)

**Name:** `MuleSoft - Anypoint Audit Log`

**Matcher:**
```
matchesPhrase(content, "\"objectType\"") AND
matchesPhrase(content, "\"organizationId\"")
```

**Sample log line:**
```json
{"requestId":"req-abc","userId":"usr-123","userName":"jsmith","organizationId":"org-xyz","environmentId":"env-456","objectType":"Application","objectId":"app-789","objectName":"payment-service","action":"Deploy","timestamp":"2024-01-15T10:23:45Z","success":true,"properties":{"status":"STARTED","region":"us-east-1"}}
```

**Processor pipeline (DPL):**
```
PARSE(content, "JSON:audit")
| FIELDS_ADD(
    mule.audit.requestId:    audit[requestId],
    mule.audit.userId:       audit[userId],
    mule.audit.userName:     audit[userName],
    mule.org:                audit[organizationId],
    mule.environment:        audit[environmentId],
    mule.audit.objectType:   audit[objectType],
    mule.audit.objectId:     audit[objectId],
    mule.audit.objectName:   audit[objectName],
    mule.audit.action:       audit[action],
    mule.audit.success:      audit[success],
    event.type:              "mule.audit",
    log.level:               if(audit[success] == false, "ERROR", else: "INFO"),
    mule.is_error:           if(audit[success] == false, true, else: false)
  )
```

---

## Extracted Field Reference

| DT Field | Type | Description | Source Rules |
|---|---|---|---|
| `mule.level` | string | Log level (INFO/WARN/ERROR/DEBUG) | 1, 3 |
| `mule.logger` | string | Logger class name | 1, 3 |
| `mule.thread` | string | JVM thread name | 1 |
| `mule.flow` | string | Flow/processor path | 1 |
| `mule.correlationId` | string | MuleSoft event/correlation ID | 1, 2 |
| `mule.message` | string | Human-readable log message | 1, 3 |
| `mule.app` | string | Application name | 1 (JSON) |
| `mule.environment` | string | Deployment environment | 1 (JSON), 4 |
| `mule.org` | string | Anypoint organization ID | 1 (JSON), 4 |
| `mule.is_error` | boolean | True when ERROR or HTTP ≥ 500 | 1–4 |
| `mule.is_4xx` | boolean | True when HTTP 4xx | 2 |
| `mule.api.name` | string | API product name | 2 |
| `mule.api.method` | string | HTTP method | 2 |
| `mule.api.path` | string | Request path | 2 |
| `mule.api.statusCode` | long | HTTP status | 2 |
| `mule.api.duration_ms` | double | End-to-end latency (ms) | 2 |
| `mule.api.upstream.ms` | double | Upstream backend latency (ms) | 2 |
| `mule.api.clientIp` | string | Caller IP address | 2 |
| `mule.api.policyViolations` | long | Gateway policy violation count | 2 |
| `mule.audit.action` | string | Audit action (Deploy/Undeploy/…) | 4 |
| `mule.audit.objectType` | string | Audited object type | 4 |
| `mule.audit.userName` | string | User who performed action | 4 |
| `mule.audit.success` | boolean | Audit event outcome | 4 |
| `event.type` | string | Log category (mule.*) | 1–4 |
