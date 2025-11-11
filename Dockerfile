# ===== 基础镜像 =====
FROM runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404

# ===== 升级 pip、setuptools、wheel =====
RUN pip3 install --upgrade pip setuptools wheel

# ===== 安装 uv（更快的 pip）=====
RUN pip3 install --no-cache-dir uv

# ===== 安装 comfy-cli =====
RUN uv pip install --upgrade comfy-cli --system

# ===== 安装运行时依赖 =====
RUN uv pip install runpod requests --system

# ===== 拷贝代码 =====
COPY rp_handler.py /rp_handler.py
COPY start.sh /start.sh

# ===== 处理脚本换行符并授权执行 =====
RUN apt-get update && apt-get install -y dos2unix && rm -rf /var/lib/apt/lists/*
RUN dos2unix /start.sh && chmod +x /start.sh

# ===== 启动入口 =====
ENTRYPOINT ["/start.sh"]
