FROM python:3.11-slim
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
WORKDIR /workspace
# Operator-only secrets and benchmark target labels are never copied into this image.
CMD ["bash"]
