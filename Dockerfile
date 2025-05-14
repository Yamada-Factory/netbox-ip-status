FROM python:3.12-alpine

ENV NETBOX_API_KEY="mofumofu"
ENV NETBOX_URL="http://netbox:8000"
ENV NETBOX_PREFIX_TAG="mofumofu"

WORKDIR /app

# install nmap net-tools
RUN apk add --no-cache net-tools nmap

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY *.py ./

CMD ["python", "-u", "netbox_ip_status.py"]
