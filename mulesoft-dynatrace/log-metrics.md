# MuleSoft Anypoint — Dynatrace Log Metrics

Configure in: **Settings → Log Monitoring → Log metrics → Add metric**.
These convert parsed log attributes into time-series metrics usable in dashboards and alerting.

---

## Metric 1 — Error Count by App and Flow

**Key:** `log.mule.errors`
**Description:** Total MuleSoft application ERROR log count

**Query:**
```dql
fetch logs
| filter event.type == "mule.app.log" AND mule.is_error == true
| summarize count(), by: {mule.app, mule.flow, mule.environment}
```

**Settings:**
- Measure: `Count of log records`
- Dimensions: `mule.app`, `mule.flow`, `mule.environment`
- Filter: `event.type == "mule.app.log" AND mule.is_error == true`

---

## Metric 2 — API Request Count by Status Class

**Key:** `log.mule.api.requests`
**Description:** Gateway access log request volume with HTTP status

**Settings:**
- Measure: `Count of log records`
- Dimensions: `mule.api.name`, `mule.api.method`, `mule.api.statusCode`, `mule.environment`
- Filter: `event.type == "mule.gateway.access"`

---

## Metric 3 — API Latency (p50/p95/p99)

**Key:** `log.mule.api.duration`
**Description:** End-to-end API response time from gateway access logs

**Settings:**
- Measure: `Attribute value` → `mule.api.duration_ms`
- Aggregation: Min, Max, Average, Percentile
- Dimensions: `mule.api.name`, `mule.api.method`, `mule.environment`
- Filter: `event.type == "mule.gateway.access"`

---

## Metric 4 — API Error Rate (5xx)

**Key:** `log.mule.api.errors`
**Description:** Count of gateway requests resulting in HTTP 5xx

**Settings:**
- Measure: `Count of log records`
- Dimensions: `mule.api.name`, `mule.environment`
- Filter: `event.type == "mule.gateway.access" AND mule.is_error == true`

---

## Metric 5 — Policy Violation Count

**Key:** `log.mule.api.policy_violations`
**Description:** Count of gateway policy violations (rate limiting, auth, etc.)

**Settings:**
- Measure: `Attribute value` → `mule.api.policyViolations`
- Dimensions: `mule.api.name`, `mule.environment`
- Filter: `event.type == "mule.gateway.access" AND mule.api.policyViolations > 0`

---

## Metric 6 — Audit Actions

**Key:** `log.mule.audit.actions`
**Description:** Count of Anypoint platform audit events (deploys, config changes, etc.)

**Settings:**
- Measure: `Count of log records`
- Dimensions: `mule.audit.action`, `mule.audit.objectType`, `mule.audit.userName`, `mule.audit.success`
- Filter: `event.type == "mule.audit"`

---

## Metric 7 — Failed Audit Events

**Key:** `log.mule.audit.failures`
**Description:** Count of Anypoint audit events where success = false

**Settings:**
- Measure: `Count of log records`
- Dimensions: `mule.audit.action`, `mule.audit.userName`, `mule.org`
- Filter: `event.type == "mule.audit" AND mule.audit.success == false`
