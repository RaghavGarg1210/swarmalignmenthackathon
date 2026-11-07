# Agent sandbox for the swarm CTF runs.
# Debian + common CTF command-line tools. Python crypto/reversing libraries are
# NOT preinstalled: agents get them with pip from the internal index.
FROM python:3.12-slim-bookworm

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      binutils file xxd bsdextrautils gdb strace ltrace upx-ucl \
      unzip p7zip-full zstd xz-utils tshark binwalk \
      gcc g++ make curl wget netcat-openbsd git jq less vim-tiny \
      procps iproute2 iputils-ping dnsutils sudo ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pip.conf /etc/pip.conf
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /root
CMD ["tail", "-f", "/dev/null"]
