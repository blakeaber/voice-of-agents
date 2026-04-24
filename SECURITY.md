# Security Policy

## Reporting a Vulnerability

If you believe you've found a security vulnerability in `voice-of-agents`,
please report it privately. **Do not open a public GitHub issue.**

**Contact:** blake.aber@gmail.com

Include in your report:

- A description of the vulnerability and the affected component
- Steps to reproduce (minimal code sample is ideal)
- The impact you believe it could have
- Any suggested fix or mitigation

## Response Timeline

- **Acknowledgment:** within 48 hours of report
- **Initial assessment:** within 7 days
- **Coordinated disclosure:** we aim to patch and publish an advisory within
  90 days of the initial report; earlier if the severity warrants

## Supported Versions

Only the latest published version on PyPI receives security fixes during the
`0.x` series. Once `1.0.0` ships, supported versions will be documented here.

## Out of Scope

- Vulnerabilities in the Claude API itself — report those to Anthropic at
  https://www.anthropic.com/security
- Vulnerabilities in direct dependencies (Pydantic, Click, Rich, etc.) —
  report those upstream and we will bump dependencies as needed
- Synthetic research output used for real decisions without real-user
  validation is a methodology choice, not a security issue; see
  `docs/MANIFESTO.md`
