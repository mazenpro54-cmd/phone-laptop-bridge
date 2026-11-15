import sys
import socket
import qrcode
import uvicorn
from zeroconf import Zeroconf, ServiceInfo
from system_control import get_system_network_info


def start_mdns_broadcast(ip: str, port: int, hostname: str):
    """
    Registers mDNS / Bonjour service so iPhones and Apple devices
    can access http://mazen-laptop.local:8000 without needing to know the IP address.
    """
    try:
        zc = Zeroconf()
        ip_bytes = socket.inet_aton(ip)
        clean_hostname = hostname.lower().replace(" ", "-")
        server_name = f"{clean_hostname}-laptop.local."

        info = ServiceInfo(
            "_http._tcp.local.",
            f"Laptop Remote ({clean_hostname})._http._tcp.local.",
            addresses=[ip_bytes],
            port=port,
            server=server_name,
            properties={"path": "/"}
        )
        zc.register_service(info)
        return zc, info, server_name.rstrip(".")
    except Exception as e:
        print(f"[!] Warning: Could not register mDNS service: {e}")
        return None, None, f"{hostname.lower()}.local"


def print_banner(ip: str, port: int, mac: str, mdns_domain: str):
    mdns_url = f"http://{mdns_domain}:{port}"
    ip_url = f"http://{ip}:{port}"

    print("=" * 64)
    print("   📱 PHONE-TO-LAPTOP BRIDGE SERVER IS RUNNING!   ")
    print("=" * 64)
    print(f"\n[★] FIXED HOSTNAME URL : {mdns_url}")
    print("    (Bookmark this on your iPhone — it never changes even if IP changes!)")
    print(f"[+] Direct IP URL      : {ip_url}")
    print(f"[+] Laptop MAC Address : {mac}")
    print(f"[+] WoL Broadcast IP   : 255.255.255.255")
    print(f"[+] WoL Port           : 9 (UDP)\n")
    print("Scan this QR code with your iPhone camera to connect:")
    print("-" * 64)

    try:
        qr = qrcode.QRCode(border=1)
        # Point QR code to mDNS url so it remains valid across IP changes
        qr.add_data(mdns_url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except Exception as e:
        print(f"(Could not render ASCII QR code: {e})")

    print("-" * 64)
    print(f"iPhone Safari URL: {mdns_url}  or  {ip_url}\n")


def main():
    port = 8000
    net_info = get_system_network_info()
    ip = net_info.get("primary_ip", "127.0.0.1")
    mac = net_info.get("mac_address", "Unknown")
    hostname = net_info.get("hostname", "laptop")

    zc, info, mdns_domain = start_mdns_broadcast(ip, port, hostname)
    print_banner(ip, port, mac, mdns_domain)

    try:
        uvicorn.run("server:app", host="0.0.0.0", port=port, log_level="info")
    finally:
        if zc and info:
            try:
                zc.unregister_service(info)
                zc.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()
