import dns.resolver 
import request
from bs4 import BeautifulSoup

DOMAIN = "google.com"

def resolve_domain(domain):
    record_types =[ 'A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT']

    for record_type in record_types: 
        try:
            answers = dns.resolver.resolve(domain, record_type)
            print(f"{record_type} records for {domain}:")
            for rdata in answers:
                print(f" - {rdata.to_text()}")
        except dns.resolver.NoAnswer:
            print(f"No {record_type} record found for {domain}.")
        except dns.resolver.NXDOMAIN:
            print(f"Domain {domain} does not exist.")
        except Exception as e:
            print(f"Error resolving {record_type} record for {domain}: {e}")

def scrape_website(domain):
    url = f"https://www.whois.com/whois/{domain}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    whois_info = soup.find('pre', class_='whois-data')
    if whois_info:
        print(f"WHOIS information for {domain}:\n{whois_info.text}")
    else:
        print(f"Could not retrieve WHOIS information for {domain}.")


print("="*15 + " DNS Resolver " + "="*15)
resolve_domain(DOMAIN)
print("="*30)

