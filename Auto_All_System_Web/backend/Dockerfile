FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_ENVIRONMENT=production

# Allow using faster pip mirror during docker build
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST

# Optional: pip proxy (ONLY for pip, not for apt)
ARG PIP_PROXY

# Allow using HTTP proxy during docker build (for slow networks)
ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG http_proxy
ARG https_proxy
ARG no_proxy

# 安装系统依赖
RUN HTTP_PROXY= HTTPS_PROXY= NO_PROXY= http_proxy= https_proxy= no_proxy= \
    apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements/ requirements/

# 安装 Python 依赖
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
      ${PIP_PROXY:+--proxy "$PIP_PROXY"} \
      ${PIP_INDEX_URL:+-i "$PIP_INDEX_URL"} \
      ${PIP_TRUSTED_HOST:+--trusted-host "$PIP_TRUSTED_HOST"} && \
    pip install -r requirements/base.txt \
      ${PIP_PROXY:+--proxy "$PIP_PROXY"} \
      ${PIP_INDEX_URL:+-i "$PIP_INDEX_URL"} \
      ${PIP_TRUSTED_HOST:+--trusted-host "$PIP_TRUSTED_HOST"}

# 复制项目文件
COPY . .

# 复制并设置启动脚本权限
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# 创建静态文件和日志目录
RUN mkdir -p staticfiles media /var/log/auto_all_system logs && touch logs/django.log

# 暴露端口
EXPOSE 8000

# 设置入口点
ENTRYPOINT ["docker-entrypoint.sh"]

# 启动命令（默认，可被 docker-compose 覆盖）
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
