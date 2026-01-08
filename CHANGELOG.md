# Changelog

All notable changes to VNS.SiteMonitor will be documented in this file.

## [1.1.0] - 2026-01-08

### Added
- Automatic retry logic for failed requests (especially DNS errors)
- New configuration options:
  - `max_retries`: Number of retry attempts (default: 3)
  - `retry_delay`: Delay in seconds between retry attempts (default: 2)
  - `ttl_dns_cache`: DNS cache TTL in seconds (default: 10)
  - `force_close`: Force close connections after each request (default: false)

### Fixed
- Intermittent DNS errors ("Name or service not known") now handled with automatic retry
- DNS caching issues that could cause false failures
- Better error logging for DNS-related failures with retry information

### Improved
- More robust error handling for connection errors
- Better DNS error detection and specific retry logic for DNS failures
- Enhanced documentation with troubleshooting section for DNS issues

## [1.0.0] - 2026-01-01

### Added
- Initial release of VNS.SiteMonitor monitoring system
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
