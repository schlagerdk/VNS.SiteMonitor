# VNS.SiteMonitor - Website Monitoring Service

A robust Python-based monitoring service for Linux servers that monitors websites and sends email alerts on failures.

## Features

- ✅ Asynchronous multi-threaded checks for optimal performance
- ✅ Support for JSON collections of websites (dynamic lists)
- ✅ Support for individual URLs
- ✅ Email notifications on failures
- ✅ Configurable check interval
- ✅ Systemd service integration with auto-restart
- ✅ Detailed logging
- ✅ Timeout handling

## System Requirements

- Linux system with systemd
- Python 3.7+
- Internet connection

## Installation

### 1. Clone repository

```bash
git clone https://github.com/schlagerdk/VNS.SiteMonitor.git
cd VNS.SiteMonitor
```

### 2. Upload to your server

```bash
scp -r * root@SERVER:/opt/sitemonitor/
```

### 3. Install on server

```bash
ssh root@SERVER
cd /opt/sitemonitor
sudo ./install.sh
```

### 4. Configure email settings

Copy the example configuration and customize it:

```bash
cp config.json.template /opt/sitemonitor/config.json
nano /opt/sitemonitor/config.json
```

Edit email settings:

```json
{
  "check_interval": 300,
  "timeout": 30,
  "concurrent_requests": 50,
  "max_retries": 3,
  "retry_delay": 2,
  "ttl_dns_cache": 10,
  "force_close": false,
  "verify_ssl": true,
  "email_notification_level": "only_failures",
  "email": {
    "from": "your-email@domain.com",
    "to": "recipient@domain.com",
    "subject": "SiteMonitor Alert: Website Failures Detected",
    "priority": "high",
    "smtp": {
      "server": "smtp.domain.com",
      "port": 587,
      "use_tls": true,
      "username": "your-smtp-username",
      "password": "your-smtp-password"
    }
  }
}
```

**Email notification levels:**
- `only_failures` - Send email only on failures (default)
- `always` - Send email after each check with complete report
- `disabled` - Disable all email notifications

### 5. Configure sites

Copy the example configuration and customize it:

```bash
cp sites.json.template /opt/sitemonitor/sites.json
nano /opt/sitemonitor/sites.json
```

Configure the sites you want to monitor:

```json
{
  "sites": [
    {
      "type": "collection",
      "url": "https://example.com/api/sites",
      "description": "Sites collection from API",
      "enabled": true
    },
    {
      "type": "single",
      "url": "https://www.example.com",
      "description": "Example website",
      "enabled": true
    },
    {
      "type": "single",
      "url": "https://another-example.com",
      "enabled": false
    }
  ]
}
```

**Site types:**

- **collection**: Fetches a JSON list of URLs from the specified URL
- **single**: A single URL to be monitored

**Enabled flag:**

- `"enabled": true` - Site will be monitored
- `"enabled": false` - Site will be skipped (useful for temporarily disabling sites)

You can also use simple strings instead of objects:

```json
{
  "sites": [
    "https://google.com",
    "https://example.com"
  ]
}
```

## Usage

### Test before deployment

Run a single check cycle to test:

```bash
cd /opt/sitemonitor
python3 sitemonitor.py --once
```

### Start the service

```bash
# Enable service to start on boot
sudo systemctl enable sitemonitor

# Start the service
sudo systemctl start sitemonitor

# Check status
sudo systemctl status sitemonitor
```

### Manage the service

```bash
# Stop the service
sudo systemctl stop sitemonitor

# Restart the service
sudo systemctl restart sitemonitor

# View logs (real-time)
sudo journalctl -u sitemonitor -f

# View logs (last 100 lines)
sudo journalctl -u sitemonitor -n 100
```

### View log file

```bash
tail -f /var/log/sitemonitor.log
```

## Configuration

### config.json parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `check_interval` | int | 300 | Seconds between each check cycle |
| `timeout` | int | 30 | HTTP request timeout in seconds |
| `concurrent_requests` | int | 50 | Maximum number of concurrent requests |
| `max_retries` | int | 3 | Number of retry attempts for failed requests (especially DNS errors) |
| `retry_delay` | int | 2 | Delay in seconds between retry attempts |
| `ttl_dns_cache` | int | 10 | DNS cache TTL in seconds (lower = fresher DNS lookups) |
| `force_close` | bool | false | Force close connections after each request |
| `email_notification_level` | string | only_failures | Email notification level: `only_failures`, `always`, or `disabled` |
| `email.from` | string | - | Sender email address |
| `email.to` | string/array | - | Recipient email(s) |
| `email.subject` | string | - | Email subject (used only in only_failures mode) |
| `email.priority` | string | normal | Email priority (normal/high) |
| `email.smtp.server` | string | - | SMTP server address |
| `email.smtp.port` | int | 587 | SMTP port |
| `email.smtp.use_tls` | bool | true | Use TLS encryption |
| `email.smtp.username` | string | - | SMTP username |
| `email.smtp.password` | string | - | SMTP password |

### sites.json format

JSON collections are expected to return either:

- A list of URL strings: `["https://site1.com", "https://site2.com"]`
- An object with a `sites`, `urls`, `list`, or `data` key
- An object where values are URLs or objects with a `url` field

## Email Notifications

Email notifications can be configured with the `email_notification_level` parameter:

### Notification Levels

- **`only_failures`** (default): Send email only when failures occur
- **`always`**: Send email after each check cycle with complete overview of all sites (both OK and failures)
- **`disabled`**: Don't send any emails

### only_failures mode

You will only receive email when **failures occur**. The email contains:

- Timestamp of the failure
- List of all failed sites
- HTTP status code (if available)
- Error message (timeout, connection error, etc.)

Example email (only_failures):

```
SiteMonitor Monitoring Alert - 2026-01-01 14:30:00

Detected 2 failed site(s):

================================================================================

URL: https://example.com
Status Code: 500
Error: None
--------------------------------------------------------------------------------

URL: https://broken-site.com
Error: Connection error: Cannot connect to host
--------------------------------------------------------------------------------
```

### always mode

You will receive email after **each check cycle** with complete overview. The email contains:

- Timestamp
- Overall statistics (total, successful, failed)
- List of failed sites (if any)
- List of successful sites

Example email (always):

```
SiteMonitor Monitoring Summary - 2026-01-01 14:30:00

================================================================================
Total sites checked: 25
Successful: 23
Failed: 2
================================================================================

FAILED SITES:

❌ https://example.com
   Status Code: 500

❌ https://broken-site.com
   Error: Connection error: Cannot connect to host

--------------------------------------------------------------------------------

SUCCESSFUL SITES:

✓ https://google.com (Status: 200)
✓ https://github.com (Status: 200)
✓ https://site1.example.com (Status: 200)
...
```

## Troubleshooting

### Service won't start

```bash
# Check systemd logs
sudo journalctl -u sitemonitor -n 50

# Check if Python is installed
python3 --version

# Check if dependencies are installed
pip3 show aiohttp
```

### Email not being sent

1. Verify SMTP settings in config.json
2. Test SMTP connection manually
3. Check firewall rules
4. View logs for error messages

### Intermittent DNS errors ("Name or service not known")

If you see errors like `Cannot connect to host example.com:443 ssl:False [Name or service not known]` but the site is actually up, this is typically caused by temporary DNS resolution failures. The monitoring tool now includes automatic retry logic:

**Configuration options to help:**
- `max_retries`: Number of retry attempts (default: 3)
- `retry_delay`: Seconds to wait between retries (default: 2)
- `ttl_dns_cache`: DNS cache TTL in seconds (default: 10)

**Troubleshooting steps:**
1. Check your server's DNS configuration: `cat /etc/resolv.conf`
2. Test DNS resolution: `nslookup example.com` or `dig example.com`
3. Consider using a more reliable DNS server (e.g., 8.8.8.8, 1.1.1.1)
4. Increase `max_retries` to 5 if DNS issues persist
5. Lower `ttl_dns_cache` to 5 for faster DNS updates

**Common causes:**
- Overloaded or unreliable DNS servers
- Network connectivity issues
- DNS rate limiting
- Firewall blocking DNS queries

### Too many emails

Adjust `check_interval` in config.json to a higher value (e.g., 600 for 10 minutes)

## Performance

The service is designed for high performance:

- **Asynchronous I/O**: All HTTP requests run asynchronously
- **Concurrent requests**: Default 50 concurrent connections
- **Connection pooling**: Reuses TCP connections
- **Efficient resource usage**: Minimal CPU and memory footprint

For 100 websites with 300s interval:
- Memory: ~30-50 MB
- CPU: <1% (when idle), ~10-20% during checks

## Security

- Log files may contain sensitive URLs - set appropriate permissions
- SMTP credentials are stored in plain text - use restricted file permissions:
  ```bash
  chmod 600 /opt/sitemonitor/config.json
  ```
- Consider using environment variables for passwords

## License

Free for personal and commercial use.

## Support

For issues, check:
1. Systemd logs: `journalctl -u sitemonitor -f`
2. Application log: `/var/log/sitemonitor.log`
3. Test mode: `python3 sitemonitor.py --once`
