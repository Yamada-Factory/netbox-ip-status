import config
import pynetbox
import requests
import datetime
import socket
from IPy import IP
from concurrent.futures import ThreadPoolExecutor
from logger import logger
from enum import Enum
from scapy.all import ARP, Ether, srp

def check_ip_use(ip):
    arp_request = ARP(pdst=ip)
    broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
    arp_request_broadcast = broadcast / arp_request
    answered_list = srp(arp_request_broadcast, timeout=2, verbose=False)[0]

    logger.debug("ARP request: " + str(arp_request_broadcast))
    logger.debug("ARP response: " + str(answered_list))

    return len(answered_list) > 0

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
    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS, thread_name_prefix="ping address") as executor:
        executor.map(lambda address: update_address(address, prefix_mask), addresses)
    # for address in addresses:
    #     update_address(address, prefix_mask)

# IP アドレスのステータスを更新
# TODO: 状態チェックとNetboxへの登録は別々に行う
def update_address(ipy_address, prefix_mask = "24"):
    logger.info(ipy_address.strNormal() + '/' + str(prefix_mask))

    ip = ipy_address.strNormal()
    updated = False
    try:
        logger.debug('Checking: ' + ip)
        # ping_result = ping(address=ip, timeout=0.5, interval=1, count=3)
        is_alive_ip = check_ip_use(ip)
        # ping_result = async_ping(address=ip, timeout=0.5, interval=1, count=3)
        rev = reverse_lookup(ip)
        address = nb.ipam.ip_addresses.get(address=ipy_address.strNormal(1))

        if address is not None:
            logger.debug('Found: ' + ip + ' -> ' + address.status)

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
    except ValueError as e:
        # Lets just go to the next one
        logger.error(e)

for prefix in prefixes:
    prefix_ip_object = IP(prefix.prefix)
    prefix_mask = prefix.prefix.split("/")[1]
    update_addresses(prefix_ip_object, prefix_mask)
