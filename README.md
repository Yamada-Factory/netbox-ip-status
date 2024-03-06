# netbox-ip-status
指定したネットワーク内のすべてのアドレスにPINGを送信し、応答があれば記録する ツール


## How to use
### Dockerコンテナを使う方法

```bash
$ docker pull ghcr.io/yamada-factory/netbox-ip-status:latest
$ docker run -e NETBOX_API_KEY="mofumofu" -e NETBOX_URL="http://netbox.example.com" -e NETBOX_PREFIX_TAG="homelab-1" ghcr.io/yamada-factory/netbox-ip-status:latest
```

#### compose.yml
.env.sample を .env にコピーして編集

```yml
versions: '3'

services:
  netbox-ip-status:
    image: ghcr.io/yamada-factory/netbox-ip-status:latest
    env_file:
      - .env

```

### プログラムをそのまま実行する方法

```bash
$ git clone git@github.com/Yamada-Factory/netbox-ip-status.git && cd netbox-ip-status
$ cp .env.sample .env # edit .env
$ python netbox-ip-status.py
```
