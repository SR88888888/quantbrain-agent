FROM python:3.10-slim

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl build-essential && rm -rf /var/lib/apt/lists/*

WORKDIR /app
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p logs data/reports && chmod -R 777 logs data

ENV PYTHONPATH=/app
ENV PYTHONWARNINGS="ignore:Unverified HTTPS request"

CMD ["python", "main.py"]
