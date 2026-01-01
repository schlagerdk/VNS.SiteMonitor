# Changelog

All notable changes to VNS.KeepAlive will be documented in this file.

## [1.0.0] - 2026-01-01

### Added
- Initial release of VNS.KeepAlive monitoring system
- Support for monitoring single sites and site collections
- Email notifications for failures and summaries
- `enabled` field in sites.json for toggling sites on/off
- `description` field used in logging and email notifications
- Async monitoring with configurable concurrent requests
- SSL verification configuration
- Build script (build.sh) for creating distribution packages
- Publish script (publish.sh) for automated deployment to HOMER
- Version tracking via VERSION file
- Systemd service configuration
- Installation script for easy setup

### Features
- Monitor websites for availability
- Fetch and monitor site collections from JSON endpoints
- Send email alerts on failures
- Send summary emails with all results
- Group results by source in emails
- Configurable timeouts and retry logic
- Comprehensive logging to file and console
