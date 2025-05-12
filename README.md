# netbox-ip-status
arpテーブルを見て存在してるIPをNetboxへ記録するツール  
※ PINGを利用した方式は存在しないIPなどを検知したりしたのでARPに移行しました


## How to use
### Dockerコンテナを使う方法

```bash
$ docker pull ghcr.io/yamada-factory/netbox-ip-status:latest
$ docker run -e NETBOX_API_KEY="mofumofu" -e NETBOX_URL="http://netbox.example.com" -e NETBOX_PREFIX_TAG="homelab-1" ghcr.io/yamada-factory/netbox-ip-status:latest
```

#### compose.yml
.env.sample を .env にコピーして編集

```yml
services:
  netbox-ip-status:
    image: ghcr.io/yamada-factory/netbox-ip-status:latest
    env_file:
      - .env

```

### プログラムをそのまま実行する方法

#### arp install
ggrks

#### Run

```bash
$ git clone git@github.com/Yamada-Factory/netbox-ip-status.git && cd netbox-ip-status
$ cp .env.sample .env # edit .env
$ python netbox-ip-status.py
```
