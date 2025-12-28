# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please:

1. **Do not** open a public issue
2. Email the maintainer at [addisonkevin0@gmail.com](mailto:addisonkevin0@gmail.com)
3. Include a detailed description of the vulnerability
4. Allow reasonable time for a response before disclosure

## Security Measures

This project implements the following security measures:

### API Security
- API keys stored in GCP Secret Manager (not in code)
- Workload Identity Federation for GitHub Actions (no long-lived credentials)
- Cloud Run with minimal IAM permissions

### Data Handling
- Text sanitization to prevent encoding attacks
- No user data persistence (stateless API)
- All external API calls use HTTPS

### Dependencies
- Automated dependency updates via Dependabot
- Regular security scanning via GitHub Security tab
