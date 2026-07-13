# MuleSoft Anypoint — Dynatrace Integration Pack

## Files

| File | What it is |
|---|---|
| `log-processing-rules.md` | 4 DPL parsing rules — copy/paste into Settings → Log Monitoring → Log processing |
| `log-metrics.md` | 7 log metric definitions for alerting and dashboard series |
| `dashboard.json` | Ready-to-import dashboard JSON |

## Log types covered

| Rule | Log source | Format |
|---|---|---|
| 1 — CloudHub App Log | CloudHub 2.0 worker stdout | Log4j2 text **or** JSON |
| 2 — Gateway Access Log | Flex / Omni Gateway | JSON (Fluent Bit HTTP output) |
| 3 — Gateway Runtime Log | Flex / Omni Gateway | Log4j2 text |
| 4 — Anypoint Audit Log | Access Management API | JSON (via HTTP ingest) |

## Import order

1. Add log processing rules (Rule 1 → 4, in order, before any generic Java rules)
2. Create log metrics (optional — needed for alerting; dashboard uses raw DQL)
3. Import dashboard: **Observe & Explore → Dashboards → Upload**

## Key extracted fields

`mule.level` · `mule.flow` · `mule.correlationId` · `mule.app` · `mule.environment`  
`mule.api.name` · `mule.api.statusCode` · `mule.api.duration_ms` · `mule.api.clientIp`  
`mule.audit.action` · `mule.audit.userName` · `mule.audit.success` · `event.type`

## Dashboard sections

- **KPI row** — app errors, API 5xx/4xx, audit failures (last 1 h)
- **Application Logs** — volume by level, error rate %, top error flows, recent error log table
- **Flex Gateway — API Traffic** — request volume by status class, p50/p95/p99 latency, error rate by API, top paths, policy violations, upstream vs. e2e latency comparison
- **Anypoint Audit** — events by action type, failed audit table, activity by user, deploy timeline

## Dashboard variables

Three dropdown filters pre-wired to all tiles:
- **Environment** (e.g., Production / Staging / Dev)
- **Application** (CloudHub app name)
- **API** (Gateway API product name)
