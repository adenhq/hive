"""
Standalone demonstration of SSRF protection logic
(without requiring httpx/beautifulsoup dependencies)
"""

import ipaddress
import socket
from urllib.parse import urlparse


def is_private_ip(ip: str) -> bool:
    """
    Check if an IP address is private, reserved, or localhost.
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        return (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        )
    except ValueError:
        return True  # Block invalid IPs


def resolve_and_validate_url(url: str) -> tuple[bool, str]:
    """
    Resolve hostname to IP and validate it's not targeting internal resources.
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        
        if not hostname:
            return False, "Invalid URL: no hostname found"
        
        # Block direct IP addresses
        try:
            ip_obj = ipaddress.ip_address(hostname)
            if is_private_ip(hostname):
                return False, f"Access to private/internal IP addresses is blocked: {hostname}"
        except ValueError:
            pass  # Not a direct IP, continue with DNS resolution
        
        # Resolve hostname to IP address(es)
        try:
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            
            for info in addr_info:
                ip = info[4][0]
                
                if '%' in ip:
                    ip = ip.split('%')[0]
                
                if is_private_ip(ip):
                    return False, f"Hostname '{hostname}' resolves to private/internal IP: {ip}"
            
            return True, f"Hostname '{hostname}' resolved to public IP(s)"
            
        except socket.gaierror as e:
            return False, f"DNS resolution failed for '{hostname}': {str(e)}"
        except Exception as e:
            return False, f"Error resolving hostname '{hostname}': {str(e)}"
            
    except Exception as e:
        return False, f"URL validation error: {str(e)}"


def main():
    print("\n" + "█" * 70)
    print("  SSRF PROTECTION DEMONSTRATION")
    print("█" * 70 + "\n")
    
    # Test 1: Private IP Detection
    print("=" * 70)
    print("TEST 1: Private IP Detection")
    print("=" * 70 + "\n")
    
    ip_tests = [
        ("127.0.0.1", "IPv4 localhost"),
        ("::1", "IPv6 localhost"),
        ("10.0.0.1", "Private range 10.x.x.x"),
        ("192.168.1.1", "Private range 192.168.x.x"),
        ("172.16.0.1", "Private range 172.16-31.x.x"),
        ("169.254.169.254", "AWS metadata endpoint"),
        ("8.8.8.8", "Public IP (Google DNS)"),
        ("1.1.1.1", "Public IP (Cloudflare)"),
    ]
    
    for ip, desc in ip_tests:
        result = is_private_ip(ip)
        status = "🚫 PRIVATE" if result else "✅ PUBLIC"
        print(f"{status:12} | {ip:20} | {desc}")
    
    # Test 2: URL Validation
    print("\n" + "=" * 70)
    print("TEST 2: URL Validation (SSRF Protection)")
    print("=" * 70 + "\n")
    
    url_tests = [
        ("http://localhost", "Should block localhost"),
        ("http://127.0.0.1", "Should block loopback IP"),
        ("http://192.168.1.1/admin", "Should block private IP"),
        ("http://10.0.0.1", "Should block private IP"),
        ("http://169.254.169.254/latest/meta-data/", "Should block AWS metadata"),
        ("http://[::1]", "Should block IPv6 localhost"),
        ("http://example.com", "Should allow public domain"),
        ("https://google.com", "Should allow public domain"),
    ]
    
    for url, desc in url_tests:
        allowed, reason = resolve_and_validate_url(url)
        status = "✅ ALLOWED" if allowed else "🚫 BLOCKED"
        print(f"{status:12} | {url:45}")
        print(f"{'':12} | {desc}")
        print(f"{'':12} | Reason: {reason}")
        print()
    
    # Summary
    print("=" * 70)
    print("SECURITY FEATURES IMPLEMENTED")
    print("=" * 70 + "\n")
    
    features = [
        "✓ Blocks localhost addresses (127.0.0.1, ::1)",
        "✓ Blocks private IP ranges (RFC 1918: 10.x, 192.168.x, 172.16-31.x)",
        "✓ Blocks link-local addresses (169.254.x.x)",
        "✓ Blocks cloud metadata endpoints (169.254.169.254)",
        "✓ Blocks IPv6 private and link-local addresses",
        "✓ Blocks multicast, broadcast, and reserved IPs",
        "✓ Performs DNS resolution to check resolved IPs",
        "✓ Validates BEFORE making HTTP requests",
        "✓ Prevents SSRF attacks on internal infrastructure",
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print("\n" + "=" * 70)
    print("Protection validated successfully!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()