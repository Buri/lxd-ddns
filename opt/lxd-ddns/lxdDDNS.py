#!/usr/bin/env python3
__author__ = 'buri'
import argparse
import re
import logging
import sys
import time
from subprocess import Popen, PIPE
from dns.resolver import Resolver
from dns.exception import DNSException
from pylxd import Client, EventType

# Templates for nsupdate
zone_update_start_template = """server {0}
zone {1}.
"""

zone_update_template = """update delete {0}.{1}
update add {0}.{1} 60 A {2}
"""

zone_update_add_alias_template = """update delete {0}.{1}
update add {0}.{1} 600 CNAME {2}.{1}.
update add {2}.{1} 600 TXT lxdDDNS-alias:{0}:
"""

zone_update_delete_record_template = """update delete {0}.{1}
"""

def register_container(container, ifaces):
    container_name = container.name
    networks = container.state().network
    for iface in ifaces:
        if iface in networks:
            setting = networks[iface]
            addresses = setting['addresses']
            for addr in addresses:
                if addr['scope'] == "global" and addr['family'] == "inet":
                    container_ip = addr['address']
                    logging.info("Updating %s to ip -> %s", container_name, container_ip)
                    if not args.dry_run:
                        nsupdate = Popen(['nsupdate', '-k', args.key], stdin=PIPE)
                        nsupdate.stdin.write(bytes(zone_update_start_template.format(args.server, args.zone), "UTF-8"))
                        nsupdate.stdin.write(bytes(zone_update_template.format(container_name, args.domain, container_ip), "UTF-8"))
                        if re.search("_", container_name):
                            alternate_name = re.sub('_','-',container_name)
                            logging.info("Adding alternate name %s to  %s", alternate_name, container_name)
                            nsupdate.stdin.write(bytes(zone_update_add_alias_template.format(alternate_name, args.domain, container_name), "UTF-8"))
                        nsupdate.stdin.write(bytes("send\n", "UTF-8"))
                        nsupdate.stdin.close()

def remove_container(container):
    container_name = container.name
    logging.info("Destroying %s", container_name)
    logging.debug("Looking for alias to %s.%s", container_name, args.domain)
    record_to_delete = [container_name]

    try:
        answers = resolver.query("{0}.{1}.".format(container_name, args.domain), "TXT", raise_on_no_answer=False).rrset
        if answers:
            for answer in answers:
                logging.debug("Checking TXT record %s for alias", answer)
                match = re.search(r"lxdDDNS-alias:([^:]+):", answer.to_text())
                if match:
                    record_to_delete.append(match.group(1))
    except DNSException as e:
        logging.error("Cannot get TXT record for %s: %s", container_name, e)
    except:
        logging.error("Unexpected error: %s", sys.exc_info()[0])
        raise

    if not args.dry_run:
        nsupdate = Popen(['nsupdate', '-k', args.key], stdin=PIPE)
        nsupdate.stdin.write(bytes(zone_update_start_template.format(args.server, args.zone), "UTF-8"))

        for record in record_to_delete:
            logging.info("Removing record for %s", record)
            nsupdate.stdin.write(bytes(zone_update_delete_record_template.format(record, args.domain), "UTF-8"))

        nsupdate.stdin.write(bytes("send\n", "UTF-8"))
        nsupdate.stdin.close()

def list_containers(client, ifaces):
    containers = client.containers.all()
    for container in containers:
        if container.status == "Stopped":
            remove_container(container)
        if container.status == "Running":
            register_container(container, ifaces)

parser = argparse.ArgumentParser()

parser.add_argument("--key", required=True, help="Path to the dynamic dns key")
parser.add_argument("--server", help="IP/Hostname of the server to update", default="127.0.0.1")
parser.add_argument("--domain", help="The domain to be updated", required=True)
parser.add_argument("--zone", help="The zone to be updated (default to the domain)")
parser.add_argument("--query-timeout", help="Max wait time in delete queries (seconds)", default="1")

parser.add_argument("--dry-run", help="Run in dry run mode without doing any update", default=False, action="store_true")

parser.add_argument("--log-level", help="Log level to display", default="INFO")
parser.add_argument("--log-file", help="Where to put the logs", default="/var/log/lxd-ddns.log")

parser.add_argument("--interfaces", help="Coma separated ordered list of interfaces to check for adresses. This is to select correct IP to assign to dns record in case of multiple IPs", default="eth0")
parser.add_argument("--interval", help="Pause between update checks, in seconds", default="30")

args = parser.parse_args()

logging.basicConfig(level=getattr(logging,args.log_level.upper()),
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename=(args.log_file if args.log_file != '-' else None))

if args.zone is None:
   args.zone = args.domain

logging.info("Starting with arguments %s", args)

c = Client()

resolver = Resolver()
resolver.nameservers = [args.server]
resolver.lifetime = float(args.query_timeout)

ifaces = args.interfaces.split(",")

while True:
    list_containers(c, ifaces)
    time.sleep(float(args.interval))

