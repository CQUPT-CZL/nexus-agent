# 使用官方轻量级 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖 (如果 pynvml 需要 gcc 编译可以加上，通常不需要)
# RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
# 这里我们直接用命令安装，为了减少文件数量方便你复制
RUN pip install --no-cache-dir fastapi uvicorn pynvml psutil

# 复制当前目录下的代码到容器中
COPY main.py .

# 暴露端口
EXPOSE 8005

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]