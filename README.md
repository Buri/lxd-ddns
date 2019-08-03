# lxd-ddns
Automatic DNS updater for lxc (using lxd api). Modified [original script](https://github.com/ggtools/docker-tools/blob/master/dockerDDNS.py) by [gg-tools](https://github.com/ggtools)

## lxdDDNS.py

A daemon to update a dynamic DNS when lxc starts containers. Designed to be used with bind9. Have a look at [this page](https://www.erianna.com/nsupdate-dynamic-dns-updates-with-bind9) to setup correctly your DNS before using it.

### Usage

    lxdDDNS.py [-h] --key KEY [--server SERVER] --domain DOMAIN
                         [--zone ZONE] [--log-level LOG_LEVEL]
                         [--log-file LOG_FILE] [--query-timeout N] [--interfaces IFACES] [--interval N]

    optional arguments:
      -h, --help            show this help message and exit
      --key KEY             Path to the dynamic dns key
      --server SERVER       IP/Hostname of the server to update
      --domain DOMAIN       The domain to be updated
      --zone ZONE           The zone to be updated (default to the domain)
      --log-level LOG_LEVEL
                            Log level to display
      --log-file LOG_FILE   Where to put the logs
      --query-timeout N     Number of seconds before queries to DNS resolver are skipped (default 1)
      --interfaces IFACES   Coma-separated list of network interfaces for which to look for ip. First found will be used (default eth0)
      --interval N          Number of seconds between updates (default 30)

### Installation

This script is designed to run as a daemon after lxc's startup. There is sample `systemd` configuration present. You NEED to replace `<keyfile>` and `<domain>` with real values. After that, reload `systemd`:
```
systemctl daemon-reload
systemctl enable lxd-ddns
systemctl start lxd-ddns
```

### Future improvements

* Script currently uses polling to check for running and stopped container. It would be nice to use events api
** The problem with this is that lxc does not emmit any event when container gains an IP address
** Could be used at least for destroying containers

