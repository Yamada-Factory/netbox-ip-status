import config
import pynetbox
import requests
import datetime
import socket
from IPy import IP
from logger import logger
from enum import Enum
import subprocess

def scan_network(ip_range):
    try:
        logger.info(f"Scanning network: {ip_range}")
        # nmapコマンドを実行
        result = subprocess.run(['nmap', '-sn', ip_range], stdout=subprocess.PIPE, text=True)
        logger.debug("Nmap command: " + ' '.join(['nmap', '-sn', ip_range]))
        logger.debug("Nmap command output: " + result.stdout)

        # IPアドレスを抽出
        devices = []
        for line in result.stdout.split('\n'):
            if "Nmap scan report for" in line:
                ip = line.split(' ')[-1] # IPは行末にある

                # 数字と. 以外の文字を削除
                ip = ''.join(filter(lambda x: x.isdigit() or x == '.', ip))

                # IPアドレスの形式を確認
                if IP(ip).iptype() == 'PUBLIC' or IP(ip).iptype() == 'PRIVATE':
                    devices.append(ip)
                else:
                    logger.warning(f"Invalid IP address format: {ip}")

        # IPアドレス一覧を表示
        logger.info(f"{len(devices)} devices found:")
        for ip in devices:
            logger.info(ip)

    except Exception as e:
        logger.error(f"IP Scan Error: {e}")

    return devices

# ネットワークをスキャン
ip_range = '172.26.26.0/24'  # 自分のネットワークに合わせてください
scan_network(ip_range)

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
    devices = scan_network(addresses.strNormal() + '/' + str(prefix_mask))
    if len(devices) == 0:
        logger.info("No devices found in the network.")

    for address in addresses:
        update_address(address, prefix_mask, devices)

# IP アドレスのステータスを更新
# TODO: 状態チェックとNetboxへの登録は別々に行う
def update_address(ipy_address, prefix_mask = "24", devices = list()):
    logger.info(ipy_address.strNormal() + '/' + str(prefix_mask))

    ip = ipy_address.strNormal()
    updated = False
    try:
        logger.debug('Checking: ' + ip)
        rev = reverse_lookup(ip)
        address = nb.ipam.ip_addresses.get(address=ipy_address.strNormal(1))

        is_alive_ip = ipy_address.strNormal() in devices
        logger.debug('Device result: ' + str(is_alive_ip))

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
