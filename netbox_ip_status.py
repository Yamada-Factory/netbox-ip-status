import config
import pynetbox
import requests
from icmplib import ping
import datetime
import socket
from IPy import IP

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
    for address in addresses:
        update_address(address, prefix_mask)

# IP アドレスのステータスを更新
# TODO: 状態チェックとNetboxへの登録は別々に行う
def update_address(ipy_address, prefix_mask = "24"):
    print(ipy_address.strNormal() + '/' + str(prefix_mask))

    ip = ipy_address.strNormal()
    updated = False
    try:
        ping_result = ping(address=ip, timeout=0.5, interval=1, count=3)
        rev = reverse_lookup(ip)
        address = nb.ipam.ip_addresses.get(address=ipy_address.strNormal(1))

        if address is not None:
            if ping_result.is_alive:
                print(ip + " -> " + str(ping_result.is_alive))
                # MEMO: deprecated / reserved の時に ping が通るようになった場合、status を active に戻す
                if address.status in {'deprecated', 'reserved'}:
                    address.status = 'active'
                    address.description = 'Updated at ' + today + '. ' + address.description

                    updated = True
            else:
                # address が登録されてて、かつ ping が通らないときかつ status が deprecated or reserved 以外のとき
                if address.status not in {'deprecated', 'reserved'}:
                    address.status = 'deprecated'
                    address.description = 'Updated at ' + today + '. ' + address.description

                    updated = True

            if updated:
                address.save()

        elif ping_result.is_alive:
            print(ip + " -> " + str(ping_result.is_alive))
            # The address does not currently exist in Netbox, so lets add a reservation so somebody does not re-use it.
            new_address = {
                "address": ipy_address.strNormal(1) + "/" + str(prefix_mask),
                "tags": [
                ],
                "status": "active",
            }
            if rev is not None:
                new_address["dns_name"] = rev
            nb.ipam.ip_addresses.create(new_address)
    except ValueError as e:
        # Lets just go to the next one
        print(e)

for prefix in prefixes:
    prefix_ip_object = IP(prefix.prefix)
    prefix_mask = prefix.prefix.split("/")[1]
    update_addresses(prefix_ip_object, prefix_mask)
