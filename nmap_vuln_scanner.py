import nmap
import requests
import os
import socket
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import subprocess   
import argparse
load_dotenv()

# Read TARGET from env or command line; env wins if CLI omitted
parser = argparse.ArgumentParser(description="Python Nmap Vulnerability Scanner")
# make positional argument optional
parser.add_argument("TARGET", nargs="?", help="Target IP address or domain")
args = parser.parse_args()

# priority: CLI value -> .env -> default
TARGET = args.TARGET or os.getenv('TARGET') or None


def nmap_scan(target):
    if not target:
        print("No TARGET specified. Set TARGET in your .env or pass one.")
        return

    nm = nmap.PortScanner()
    print(f"Scanning {target} for open tcp ports...")

    # First do a fast discovery of open TCP ports across the full range
    try:
        nm.scan(hosts=target, arguments='-p- --open')
    except Exception as e:
        print(f"Error running initial scan: {e}")
        return

    hosts = nm.all_hosts()
    if not hosts:
        print(f"No hosts found for target {target}")
        return

    with ThreadPoolExecutor(max_workers=10) as executor:
        for host in hosts:
            print(f"Host: {host}")
            print(f"State: {nm[host].state()}")

            if 'tcp' not in nm[host]:
                continue

            # Collect open ports for this host and run a version scan on them
            open_ports = sorted(nm[host]['tcp'].keys())
            if not open_ports:
                continue

            ports_str = ','.join(str(p) for p in open_ports)
            try:
                nm.scan(hosts=host, ports=ports_str, arguments='-sV -Pn -T4')
            except Exception as e:
                print(f"Error running version scan on {host}: {e}")
                continue

            for port in sorted(nm[host]['tcp'].keys()):
                state = nm[host]['tcp'][port]['state']
                service = nm[host]['tcp'][port].get('name', '')
                version = nm[host]['tcp'][port].get('version', '')
                product = nm[host]['tcp'][port].get('product', '')

                print(f"Port {port}: {state} - {service} {product} {version}")
                if state == 'open':
                    executor.submit(banner_grab, host, port)
                if product:  # Only check vulnerabilities if we have product info
                    executor.submit(check_vulnerabilities, product, version)
                    executor.submit(search_exploits, product, version)
                print("-" * 30)

def banner_grab(host, port):
    try:
        with socket.create_connection((host, port), timeout=3) as sock:
            sock.settimeout(3)
            # try to receive up to 1024 bytes as banner
            banner = sock.recv(1024)
            if banner:
                print(f"Banner ({host}:{port}): {banner.decode(errors='ignore').strip()}")
    except Exception as e:
        # most connections will be reset/refused; ignore
        pass


def check_vulnerabilities(service, version):
    if not service or service.strip() == '':
        return
    
    base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    params = {
        "keywordSearch": f"{service} {version}",
        "resultsPerPage": 5
    }
    headers = {
        "User-Agent": "Python-VulnScanner"
    }
    
    api_key = os.getenv('API_KEY')
    if api_key:
        headers["apiKey"] = api_key
    
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("totalResults", 0) > 0:
            print(f"Potential vulnerabilities for {service} {version}:")
            cve_list = data.get("vulnerabilities", [])
            for item in cve_list[:5]:  # Show max 5 results
                cve = item.get("cve", {})
                cve_id = cve.get("id", "N/A")
                descriptions = cve.get("descriptions", [])
                description = descriptions[0].get("value", "N/A") if descriptions else "N/A"
                print(f"  {cve_id}: {description[:100]}...")
                print("-" * 10)
        else:
            print(f"No known vulnerabilities found for {service} {version}")
    except requests.exceptions.RequestException as e:
            print(f"Error checking vulnerabilities: {e}")


def search_exploits(service, version):
    query = f"{service} {version}"
    try:
        result = subprocess.run(
            ["searchsploit", query],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            print(f"Exploits found for {service} {version}:")
            print(result.stdout)
        elif result.returncode != 0 and result.stderr:
            print(f"Searchsploit error: {result.stderr}")
    except FileNotFoundError:
        print("searchsploit not installed. Install it with: sudo apt install exploitdb")
    except subprocess.TimeoutExpired:
        print(f"Searchsploit timeout for {service}")
    except Exception as e:
        print(f"Error running searchsploit: {e}")
if not TARGET:
    print("No target specified.")
    exit(0)
else:
    nmap_scan(TARGET)