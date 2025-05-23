import config
import pynetbox
import requests
import datetime
import socket
from IPy import IP
from logger import logger
from enum import Enum
import subprocess
import xml2dict
import xml.etree.ElementTree as ET

def scan_network(ip_range):
    try:
        logger.info(f"Scanning network: {ip_range}")
        # nmapコマンドを実行
        nmap_cmd = ['nmap', '-v', '-sn', '-n', '-oX', '-', ip_range]
        logger.debug("Nmap command: " + ' '.join(nmap_cmd))
        result = subprocess.run(nmap_cmd, stdout=subprocess.PIPE, text=True)
        logger.debug("Nmap command output: " + result.stdout)


        element = ET.fromstring(result.stdout)
        nmap_result = xml2dict.xml_to_dict(element)
        hosts = nmap_result['host']

        devices = []
        for host in hosts:
            host_address = host.get('address')
            host_status = host.get('status')

            if host_address is None or host_status is None:
                logger.warning("No address or status found for host.")
                continue

            # host_address がリストかどうか確認
            if isinstance(host_address, list):
                ipv4_address = None
                for addr in host_address:
                    if addr['addrtype'] == 'ipv4':
                        ipv4_address = addr
                        break
                host_address = ipv4_address if ipv4_address else None

            if not isinstance(host_address, dict):
                logger.warning("No valid IPv4 address found for host.")
                continue

            host_address_addr = host_address.get('addr')
            if host_address_addr is None:
                logger.warning("No address found for host.")
                continue

            # 数字と. 以外の文字を削除
            host_address_addr = ''.join(filter(lambda x: x.isdigit() or x in '.:abcdefABCDEF', host_address_addr))
            # IPアドレスの形式を確認
            if IP(host_address_addr).iptype() != 'PUBLIC' and IP(host_address_addr).iptype() != 'PRIVATE':
                logger.warning(f"Invalid IP address format: {host_address_addr}")
                continue

            host_address_addrtype = host_address.get('addrtype')
            if host_address_addrtype != 'ipv4' and host_address_addrtype != 'ipv6':
                logger.warning("Address type is not IPv4 or IPv6.")
                continue

            host_status_state = host_status.get('state')
            if host_status_state == 'up':
                logger.debug(f"Host is up: {host_address_addr}")
            else:
                logger.debug(f"Host is down: {host_address_addr}")
                continue

            # IPアドレスをリストに追加
            devices.append(host_address_addr)
            logger.debug(f"Host address: {host_address_addr}")

        # IPアドレス一覧を表示
        logger.info(f"{len(devices)} devices found:")
        for ip in devices:
            logger.info(ip)

        return devices
    except Exception as e:
        logger.error(f"IP Scan Error: {e}")
        raise e

class NetboxStatus(Enum):
    ACTIVE = 'active'
    DEPRECATED = 'deprecated'
    RESERVED = 'reserved'

# create netbox session
netbox_session = requests.Session()
nb = pynetbox.api(
    config.NETBOX_URL,
    token=config.API_KEY,
    threading=True
)
nb.http_session = netbox_session

# 更新対象の prefix を取得
prefixes = nb.ipam.prefixes.filter(tag=[config.PREFIX_TAG])

today_datetime = datetime.datetime.now()
today = today_datetime.strftime('%Y-%m-%d')

# IP アドレスからホスト名を逆引き
def reverse_lookup(ip):
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except socket.herror:
        return None

# IP アドレスのステータスを更新
def update_addresses(addresses, prefix_mask):
    devices = scan_network(addresses.strNormal())
    if len(devices) == 0:
        logger.info("No devices found in the network.")

    for address in addresses:
        update_address(address, prefix_mask, devices)

# IP アドレスのステータスを更新
def update_address(ipy_address, prefix_mask = "24", devices = list()):
    logger.info(ipy_address.strNormal() + '/' + str(prefix_mask))

    ip = ipy_address.strNormal()
    updated = False
    try:
        rev = reverse_lookup(ip)
        address = nb.ipam.ip_addresses.get(address=ipy_address.strNormal(1))

        is_alive_ip = ipy_address.strNormal() in devices
        logger.debug('Device result: ' + str(is_alive_ip))

        if address is not None:
            logger.debug('Found: ' + ip + ' -> ' + address.status.value)

            if is_alive_ip:
                logger.info(ip + " -> " + str(is_alive_ip))
                # MEMO: deprecated / reserved の時に ping が通るようになった場合、status を active に戻す
                if address.status.value in {NetboxStatus.DEPRECATED.value, NetboxStatus.RESERVED.value}:
                    address.status = NetboxStatus.ACTIVE.value
                    address.comments = 'Updated at ' + today + '.\n' + address.comments

                    updated = True
            else:
                # address が登録されてて、かつ ping が通らないときかつ status が deprecated or reserved 以外のとき
                if address.status.value not in {NetboxStatus.DEPRECATED.value, NetboxStatus.RESERVED.value}:
                    address.status = NetboxStatus.DEPRECATED.value
                    address.comments = 'Updated at ' + today + '.\n' + address.comments

                    updated = True

            if updated:
                address.save()
                logger.info('Updated: ' + ip + ' -> ' + address.status)

        elif is_alive_ip:
            logger.info(ip + " -> " + str(is_alive_ip))
            # The address does not currently exist in Netbox, so lets add a reservation so somebody does not re-use it.
            new_address = {
                "address": ipy_address.strNormal(1) + "/" + str(prefix_mask),
                "tags": [
                ],
                "status": NetboxStatus.ACTIVE.value,
            }
            if rev is not None:
                new_address["dns_name"] = rev
            nb.ipam.ip_addresses.create(new_address)
            logger.info('Created: ' + ip + ' -> ' + 'active')
    except Exception as e:
        logger.error(f"Error updating address {ipy_address}: {e}")
        raise e

for prefix in prefixes:
    prefix_ip_object = IP(prefix.prefix)
    prefix_mask = prefix.prefix.split("/")[1]
    update_addresses(prefix_ip_object, prefix_mask)
