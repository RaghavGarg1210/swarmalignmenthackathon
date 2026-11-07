# One image, two roles: the pypiserver backend and the logging front proxy.
FROM python:3.12-slim-bookworm
RUN pip install --no-cache-dir "pypiserver==2.4.2" "passlib==1.7.4"
COPY logproxy.py /opt/logproxy.py
