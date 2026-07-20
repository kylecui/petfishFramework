# Security Policy

## Supported Versions

| Version | Supported              |
|---------|------------------------|
| 1.1.x   | ✅ Active development   |
| 1.0.x   | ⚠️ Security fixes only  |
| < 1.0   | ❌ Not supported         |

## Reporting a Vulnerability

If you discover a security vulnerability in petfishFramework:

1. **DO NOT** open a public GitHub issue.
2. Email **security@kylecui.dev** with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)
3. You will receive an acknowledgment within **48 hours**.
4. We will investigate and provide a fix timeline within **7 days**.

## Security Features

petfishFramework provides runtime access control for AI agents:

- **6 DecisionEffects**: ALLOW, DENY, REQUIRE_APPROVAL, PARTIAL_ALLOW, MASK, DEGRADE
- **Fail-closed DEGRADE**: no fallback → block, never execute original
- **Input/Output/Event masking**: prevent sensitive data leakage at all layers
- **Budget enforcement**: hard token/cost/steps limits
- **Event-sourced audit**: every action recorded for compliance

## Scope

**In scope**: Runtime permission bypass, tool execution without authorization,
audit log tampering, sensitive data leakage in events.

**Out of scope**: LLM model vulnerabilities, prompt injection (mitigated by
runtime controls but not eliminated), infrastructure security.

## Disclosure Timeline

- Day 0: Report received
- Day 1-2: Acknowledgment + initial assessment
- Day 3-7: Fix development
- Day 7-14: Fix release + public disclosure (after fix is available)
