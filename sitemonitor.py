#!/usr/bin/env python3
"""
VNS.SiteMonitor - Website monitoring and alerting
Monitors websites for availability and sends email alerts on failures
"""

import asyncio
import aiohttp
import json
import ssl
import smtplib
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict, Any
import sys
import os

# Try to import certifi for better SSL support
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    # Fall back to default SSL context if certifi is not available
    SSL_CONTEXT = ssl.create_default_context()

# Setup logging
log_handlers = [logging.StreamHandler(sys.stdout)]

# Try to use /var/log/sitemonitor.log if writable, otherwise use local directory
try:
    log_file = '/var/log/sitemonitor.log'
    # Test if we can write to /var/log
    if os.path.exists('/var/log') and os.access('/var/log', os.W_OK):
        log_handlers.append(logging.FileHandler(log_file))
    else:
        # Use local directory for logging
        log_file = 'sitemonitor.log'
        log_handlers.append(logging.FileHandler(log_file))
        print(f"Note: Using local log file: {os.path.abspath(log_file)}")
except Exception:
    # If file logging fails, continue with just console output
    print("Warning: Could not setup file logging, using console only")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=log_handlers
)
logger = logging.getLogger(__name__)


class SiteMonitorMonitor:
    def __init__(self, config_path: str = 'config.json', sites_path: str = 'sites.json'):
        self.config_path = Path(config_path)
        self.sites_path = Path(sites_path)
        self.config = self.load_config()
        self.sites_config = self.load_sites()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_path}")
                return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise

    def load_sites(self) -> Dict[str, Any]:
        """Load sites configuration from sites.json"""
        try:
            with open(self.sites_path, 'r') as f:
                sites = json.load(f)
                logger.info(f"Sites configuration loaded from {self.sites_path}")
                return sites
        except FileNotFoundError:
            logger.error(f"Sites file not found: {self.sites_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in sites file: {e}")
            raise

    async def fetch_url(self, session: aiohttp.ClientSession, url: str, verify_ssl: bool = True) -> Dict[str, Any]:
        """Fetch a single URL and return status information with retry logic for DNS errors"""
        max_retries = self.config.get('max_retries', 3)
        retry_delay = self.config.get('retry_delay', 2)

        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=self.config.get('timeout', 30))
                # Use SSL_CONTEXT for proper certificate verification, or False to disable
                ssl_param = SSL_CONTEXT if verify_ssl else False
                async with session.get(url, timeout=timeout, allow_redirects=True, ssl=ssl_param) as response:
                    return {
                        'url': url,
                        'status': response.status,
                        'success': 200 <= response.status < 300,
                        'error': None
                    }
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    logger.debug(f"Timeout on {url}, retrying ({attempt + 1}/{max_retries})...")
                    await asyncio.sleep(retry_delay)
                    continue
                return {
                    'url': url,
                    'status': None,
                    'success': False,
                    'error': 'Request timeout'
                }
            except aiohttp.ClientConnectorError as e:
                # DNS or connection errors - retry
                error_msg = str(e)
                if 'Name or service not known' in error_msg or 'nodename nor servname provided' in error_msg:
                    if attempt < max_retries - 1:
                        logger.warning(f"DNS error on {url}, retrying ({attempt + 1}/{max_retries}): {error_msg}")
                        await asyncio.sleep(retry_delay)
                        continue
                    logger.error(f"DNS error on {url} after {max_retries} attempts: {error_msg}")
                return {
                    'url': url,
                    'status': None,
                    'success': False,
                    'error': f'Connection error: {error_msg}'
                }
            except aiohttp.ClientError as e:
                return {
                    'url': url,
                    'status': None,
                    'success': False,
                    'error': f'Connection error: {str(e)}'
                }
            except Exception as e:
                return {
                    'url': url,
                    'status': None,
                    'success': False,
                    'error': f'Unexpected error: {str(e)}'
                }

        # Should not reach here, but just in case
        return {
            'url': url,
            'status': None,
            'success': False,
            'error': 'Max retries exceeded'
        }

    async def fetch_site_collection(self, session: aiohttp.ClientSession, collection_url: str, verify_ssl: bool = True) -> tuple[List[str], Dict[str, Any] | None]:
        """Fetch a JSON collection of sites from a URL. Returns (urls, error_info)"""
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.get('timeout', 30))
            # Use SSL_CONTEXT for proper certificate verification, or False to disable
            ssl_param = SSL_CONTEXT if verify_ssl else False
            async with session.get(collection_url, timeout=timeout, ssl=ssl_param) as response:
                if response.status == 200:
                    data = await response.json()
                    # Assume the response is either a list of URLs or a dict with URLs
                    if isinstance(data, list):
                        return data, None
                    elif isinstance(data, dict):
                        # Try common keys for site lists
                        for key in ['sites', 'urls', 'list', 'data']:
                            if key in data and isinstance(data[key], list):
                                return data[key], None
                        # If it's a dict of dicts/objects, extract URLs
                        urls = []
                        for value in data.values():
                            if isinstance(value, str) and value.startswith('http'):
                                urls.append(value)
                            elif isinstance(value, dict) and 'url' in value:
                                urls.append(value['url'])
                        return urls, None
                    return [], None
                else:
                    error_info = {
                        'url': collection_url,
                        'status': response.status,
                        'success': False,
                        'error': f'HTTP {response.status}',
                        'is_collection': True
                    }
                    logger.error(f"Failed to fetch collection from {collection_url}: HTTP {response.status}")
                    return [], error_info
        except Exception as e:
            error_info = {
                'url': collection_url,
                'status': None,
                'success': False,
                'error': str(e),
                'is_collection': True
            }
            logger.error(f"Error fetching collection from {collection_url}: {str(e)}")
            return [], error_info

    async def collect_all_urls(self, session: aiohttp.ClientSession, verify_ssl: bool = True) -> tuple[List[str], Dict[str, str], Dict[str, str], List[Dict[str, Any]]]:
        """Collect all URLs from sites configuration. Returns (urls, url_sources, url_descriptions, collection_errors)"""
        all_urls = []
        url_sources = {}  # Maps URL to its source (collection URL or 'Single Sites')
        url_descriptions = {}  # Maps URL to its description
        collection_errors = []
        verify_ssl = self.config.get('verify_ssl', True)

        for site_entry in self.sites_config.get('sites', []):
            if isinstance(site_entry, str):
                # Direct URL
                all_urls.append(site_entry)
                url_sources[site_entry] = 'Single Sites'
            elif isinstance(site_entry, dict):
                # Skip if explicitly disabled
                if not site_entry.get('enabled', True):
                    desc = site_entry.get('description', '')
                    desc_text = f" ({desc})" if desc else ""
                    logger.info(f"Skipping disabled site: {site_entry.get('url', 'unknown')}{desc_text}")
                    continue

                if site_entry.get('type') == 'collection':
                    # URL collection - fetch the list
                    collection_url = site_entry.get('url')
                    if collection_url:
                        collection_desc = site_entry.get('description', collection_url)
                        logger.info(f"Fetching collection from: {collection_url}")
                        urls, error = await self.fetch_site_collection(session, collection_url, verify_ssl)
                        all_urls.extend(urls)
                        # Mark all URLs from this collection with their source
                        for url in urls:
                            url_sources[url] = collection_desc
                            url_descriptions[url] = url  # Use actual URL as description
                        logger.info(f"Collected {len(urls)} URLs from {collection_url}")
                        if error:
                            collection_errors.append(error)
                elif site_entry.get('type') == 'single' or 'url' in site_entry:
                    # Single URL in dict format
                    url = site_entry.get('url')
                    if url:
                        all_urls.append(url)
                        description = site_entry.get('description', url)
                        url_sources[url] = description
                        url_descriptions[url] = description

        # Remove duplicates while preserving order
        seen = set()
        unique_urls = []
        for url in all_urls:
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)

        logger.info(f"Total unique URLs to check: {len(unique_urls)}")
        return unique_urls, url_sources, url_descriptions, collection_errors

    async def check_all_sites(self) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Check all configured sites asynchronously. Returns (site_results, collection_errors)"""
        verify_ssl = self.config.get('verify_ssl', True)
        # Force new connections and disable DNS caching to avoid stale DNS issues
        connector = aiohttp.TCPConnector(
            limit=self.config.get('concurrent_requests', 50),
            force_close=self.config.get('force_close', False),
            ttl_dns_cache=self.config.get('ttl_dns_cache', 10)  # DNS cache TTL in seconds
        )
        async with aiohttp.ClientSession(connector=connector) as session:
            # Collect all URLs
            urls, url_sources, url_descriptions, collection_errors = await self.collect_all_urls(session, verify_ssl)

            # Check all URLs concurrently
            logger.info(f"Starting health checks for {len(urls)} sites...")
            tasks = [self.fetch_url(session, url, verify_ssl) for url in urls]
            results = await asyncio.gather(*tasks)

            # Add source and description information to each result
            for result in results:
                result['source'] = url_sources.get(result['url'], 'Unknown')
                result['description'] = url_descriptions.get(result['url'], result['url'])

            return results, collection_errors

    def send_failure_email(self, failed_sites: List[Dict[str, Any]]):
        """Send email notification for failed sites"""
        if not failed_sites:
            return

        email_config = self.config.get('email', {})
        hostname = socket.gethostname()

        # Build email content
        base_subject = email_config.get('subject', 'VNS.SiteMonitor Alert: Site Failures Detected')
        subject = f"[{hostname}] {base_subject}"
        from_email = email_config.get('from')
        to_email = email_config.get('to')

        if not from_email or not to_email:
            logger.error("Email configuration missing 'from' or 'to' address")
            return

        # Create email body
        body_lines = [
            f"VNS.SiteMonitor Monitoring Alert - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Server: {hostname}",
            "",
            f"Detected {len(failed_sites)} failed site(s):",
            "",
            "=" * 80,
            ""
        ]

        for site in failed_sites:
            desc = site.get('description', '')
            if desc and desc != site['url']:
                body_lines.append(f"Site: {desc}")
                body_lines.append(f"URL: {site['url']}")
            else:
                body_lines.append(f"URL: {site['url']}")
            if site['status']:
                body_lines.append(f"Status Code: {site['status']}")
            if site['error']:
                body_lines.append(f"Error: {site['error']}")
            body_lines.append("-" * 80)
            body_lines.append("")

        body = "\n".join(body_lines)

        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email if isinstance(to_email, str) else ', '.join(to_email)
        msg['Subject'] = subject

        # Add priority if specified
        priority = email_config.get('priority', 'normal')
        if priority == 'high':
            msg['X-Priority'] = '1'
            msg['Importance'] = 'high'

        msg.attach(MIMEText(body, 'plain'))

        # Send email
        try:
            smtp_config = email_config.get('smtp', {})
            server = smtp_config.get('server', 'localhost')
            port = smtp_config.get('port', 587)
            use_tls = smtp_config.get('use_tls', True)
            username = smtp_config.get('username')
            password = smtp_config.get('password')

            with smtplib.SMTP(server, port) as smtp:
                if use_tls:
                    smtp.starttls()
                if username and password:
                    smtp.login(username, password)

                to_addresses = to_email if isinstance(to_email, list) else [to_email]
                smtp.sendmail(from_email, to_addresses, msg.as_string())

            logger.info(f"Alert email sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")

    def send_summary_email(self, successful_sites: List[Dict[str, Any]], failed_sites: List[Dict[str, Any]], collection_errors: List[Dict[str, Any]] | None = None):
        """Send email summary of all site checks (success and failures)"""
        email_config = self.config.get('email', {})
        hostname = socket.gethostname()
        if collection_errors is None:
            collection_errors = []

        # Build email content
        total = len(successful_sites) + len(failed_sites)
        total_failures = len(failed_sites) + len(collection_errors)
        if total_failures > 0:
            subject = f"[{hostname}] VNS.SiteMonitor Report: {total_failures} Failures, {len(successful_sites)} OK (Total: {total})"
        else:
            subject = f"[{hostname}] VNS.SiteMonitor Report: All {total} Sites OK ✓"

        from_email = email_config.get('from')
        to_email = email_config.get('to')

        if not from_email or not to_email:
            logger.error("Email configuration missing 'from' or 'to' address")
            return

        # Create email body
        body_lines = [
            f"VNS.SiteMonitor Monitoring Summary - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Server: {hostname}",
            "",
            "=" * 80,
            f"Total sites checked: {total}",
            f"Successful: {len(successful_sites)}",
            f"Failed: {len(failed_sites)}",
            f"Collection errors: {len(collection_errors)}",
            "=" * 80,
            ""
        ]

        # Add collection errors first if any
        if collection_errors:
            body_lines.append("COLLECTION FETCH ERRORS:")
            body_lines.append("")
            for error in collection_errors:
                body_lines.append(f"❌ {error['url']} (Collection)")
                if error['status']:
                    body_lines.append(f"   Status Code: {error['status']}")
                if error['error']:
                    body_lines.append(f"   Error: {error['error']}")
                body_lines.append("")
            body_lines.append("-" * 80)
            body_lines.append("")

        # Add failed sites if any - grouped by source
        if failed_sites:
            body_lines.append("FAILED SITES:")
            body_lines.append("")

            # Group by source
            failed_by_source = {}
            for site in failed_sites:
                source = site.get('source', 'Unknown')
                if source not in failed_by_source:
                    failed_by_source[source] = []
                failed_by_source[source].append(site)

            for source, sites in failed_by_source.items():
                body_lines.append("")
                body_lines.append(f"▼ {source.upper()} ▼")
                body_lines.append("-" * 60)
                for site in sites:
                    desc = site.get('description', '')
                    if desc and desc != site['url']:
                        body_lines.append(f"  ❌ {desc}")
                        body_lines.append(f"     {site['url']}")
                    else:
                        body_lines.append(f"  ❌ {site['url']}")
                    if site['status']:
                        body_lines.append(f"     Status Code: {site['status']}")
                    if site['error']:
                        body_lines.append(f"     Error: {site['error']}")
                body_lines.append("")
            body_lines.append("-" * 80)
            body_lines.append("")

        # Add successful sites - grouped by source
        if successful_sites:
            body_lines.append("SUCCESSFUL SITES:")
            body_lines.append("")

            # Group by source
            success_by_source = {}
            for site in successful_sites:
                source = site.get('source', 'Unknown')
                if source not in success_by_source:
                    success_by_source[source] = []
                success_by_source[source].append(site)

            for source, sites in success_by_source.items():
                body_lines.append("")
                body_lines.append(f"▼ {source.upper()} ({len(sites)} sites) ▼")
                body_lines.append("-" * 60)
                for site in sites:
                    desc = site.get('description', '')
                    if desc and desc != site['url']:
                        body_lines.append(f"  ✓ {desc} (Status: {site['status']})")
                    else:
                        body_lines.append(f"  ✓ {site['url']} (Status: {site['status']})")
                body_lines.append("")

        body = "\n".join(body_lines)

        # Create message
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email if isinstance(to_email, str) else ', '.join(to_email)
        msg['Subject'] = subject

        # Add priority only if there are failures
        if failed_sites or collection_errors:
            priority = email_config.get('priority', 'normal')
            if priority == 'high':
                msg['X-Priority'] = '1'
                msg['Importance'] = 'high'

        msg.attach(MIMEText(body, 'plain'))

        # Send email
        try:
            smtp_config = email_config.get('smtp', {})
            server = smtp_config.get('server', 'localhost')
            port = smtp_config.get('port', 587)
            use_tls = smtp_config.get('use_tls', True)
            username = smtp_config.get('username')
            password = smtp_config.get('password')

            with smtplib.SMTP(server, port) as smtp:
                if use_tls:
                    smtp.starttls()
                if username and password:
                    smtp.login(username, password)

                to_addresses = to_email if isinstance(to_email, list) else [to_email]
                smtp.sendmail(from_email, to_addresses, msg.as_string())

            logger.info(f"Summary email sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send summary email: {str(e)}")

    async def run_check(self):
        """Run a single monitoring check cycle"""
        logger.info("=" * 80)
        logger.info("Starting monitoring cycle")

        results, collection_errors = await self.check_all_sites()

        # Separate successful and failed sites
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        total_failures = len(failed) + len(collection_errors)

        logger.info(f"Check complete: {len(successful)} OK, {len(failed)} site failures, {len(collection_errors)} collection errors")

        # Handle email notifications based on configuration
        notification_level = self.config.get('email_notification_level', 'only_failures')

        if notification_level == 'disabled':
            logger.info("Email notifications are disabled")
        elif notification_level == 'always':
            logger.info("Sending summary email (notification level: always)")
            self.send_summary_email(successful, failed, collection_errors)
        elif notification_level == 'only_failures':
            if total_failures > 0:
                logger.warning(f"Failed sites: {[f['url'] for f in failed]}")
                if collection_errors:
                    logger.warning(f"Collection errors: {[e['url'] for e in collection_errors]}")
                # For only_failures mode, combine all errors into failed list
                all_failures = failed + collection_errors
                self.send_failure_email(all_failures)
            else:
                logger.info("No failures detected, skipping email (notification level: only_failures)")
        else:
            logger.warning(f"Unknown email_notification_level: {notification_level}, defaulting to only_failures")
            if total_failures > 0:
                logger.warning(f"Failed sites: {[f['url'] for f in failed]}")
                all_failures = failed + collection_errors
                self.send_failure_email(all_failures)

        return {
            'total': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'collection_errors': len(collection_errors),
            'failed_sites': failed
        }

    async def run_continuous(self):
        """Run monitoring continuously with configured interval"""
        interval = self.config.get('check_interval', 300)  # Default 5 minutes
        logger.info(f"Starting continuous monitoring (interval: {interval}s)")

        while True:
            try:
                await self.run_check()
            except Exception as e:
                logger.error(f"Error during monitoring cycle: {str(e)}", exc_info=True)

            logger.info(f"Waiting {interval} seconds until next check...")
            await asyncio.sleep(interval)


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='VNS.SiteMonitor Website Monitoring Service')
    parser.add_argument('--config', default='config.json', help='Path to config.json')
    parser.add_argument('--sites', default='sites.json', help='Path to sites.json')
    parser.add_argument('--once', action='store_true', help='Run once and exit (for testing)')

    args = parser.parse_args()

    monitor = SiteMonitorMonitor(args.config, args.sites)

    if args.once:
        logger.info("Running single check (--once mode)")
        await monitor.run_check()
    else:
        await monitor.run_continuous()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)
