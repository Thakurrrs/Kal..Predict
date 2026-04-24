# API Integration Specification

## Metadata
- Owner: Founder (Rasalghul)
- Reviewers: Founder (self-review)
- Approver: Founder (Rasalghul)
- Version: 1.0.0
- Last Updated: 2026-04-23
- Status: Approved

## External APIs
- Kalshi API
- NWS API
- Search/retrieval providers

## Integration Modes
- **Pre-Credential Mode (now until Saturday)**
  - Use mock `MarketDataProvider` and `ExecutionProvider` adapters.
  - Execute all integration and paper tests against simulated exchange behavior.
  - Keep Kalshi write path disabled.
- **Credential Mode (from Saturday)**
  - Enable Kalshi read integration first.
  - Run smoke tests and validation checks before any write-capable path is enabled.

## Per-API Definition
- **Kalshi API**
  - Base URL: official trade API host
  - Auth method: API key ID + RSA-PSS signing
  - Required headers: auth headers and timestamp as required by API
  - Retry policy: exponential backoff for transient read failures; no blind retry on writes
  - Timeout policy: short request timeout with bounded retry budget
  - Error handling: explicit mapping for auth, rate-limit, and validation errors
  - Credential onboarding rule: no live write operations until smoke tests pass and risk/logging validations are confirmed
- **NWS API**
  - Base URL: `https://api.weather.gov`
  - Auth method: none
  - Required headers: unique User-Agent
  - Retry policy: bounded retries for transient failures
  - Timeout policy: short timeout with fallback to last valid reading
  - Error handling: mark evidence stale when freshness threshold exceeded
- **Search/retrieval providers**
  - Auth method: API key where required
  - Required metadata capture: source, retrieval timestamp, URL, provider name
  - Error handling: degrade gracefully and continue with available evidence set

## Reliability Requirements
- Idempotency: read operations idempotent; write actions require unique request IDs.
- Circuit breaker policy: temporarily disable unstable provider after repeated failures.
- Backoff strategy: exponential backoff with jitter and hard stop on max attempts.

## Saturday Onboarding Checklist
- Validate credential loading from secure local environment.
- Confirm signed request authentication works for read endpoints.
- Confirm rate-limit and error mapping behavior with real responses.
- Confirm all decision traces and audit fields are captured with real market reads.
