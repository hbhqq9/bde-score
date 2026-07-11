# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ Active |
| < 1.0   | ❌ EOL    |

## Security Architecture

BDE Score follows a defense-in-depth security model:

- **Authentication**: API Key (X-API-Key header) with bcrypt hashing (cost=12)
- **Rate Limiting**: 10 requests/minute per IP
- **Input Validation**: Market/symbol whitelist enforcement
- **Error Handling**: Generic error messages, no internal detail leakage
- **Transport**: HTTPS via Cloudflare Tunnel
- **Secrets**: .env only (chmod 600), never in code/git/logs

## Compliance

- **EU AI Act Art.50**: Transparent scoring methodology, no black-box predictions
- **Financial Disclaimer**: Technical service only. Not investment advice.

## Reporting a Vulnerability

If you discover a security vulnerability, please:

1. **DO NOT** open a public issue
2. Email: nnhbh@foxmail.com
3. Include: description, steps to reproduce, affected component
4. Expected response time: 48 hours

## Security Audit

Latest audit: [2026-07-11](distribution/security_audit_20260711.md) — Score: 98/100

## Security Constitution

This project follows a 7-iron-rule security constitution. See [SECURITY_CONSTITUTION](distribution/SECURITY_CONSTITUTION_v2.md) for details.
