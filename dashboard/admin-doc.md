# Nexus Agent 管理员技术文档

## 1. 项目结构

- `agent/`：部署在服务器上的监控 Agent，负责暴露 `/metrics`
- `dashboard/`：看板前端和网关服务
- `dashboard/server.py`：看板静态资源服务、配置读写接口、代理接口
- `dashboard/config.json`：服务器配置文件
- `dashboard/index.html`：看板主页面

## 2. 启动方式

### 启动看板

```bash
python dashboard/server.py
```

默认端口：

```text
http://0.0.0.0:3000
```

### 启动 Agent
在每个服务器的czl账号后，家目录中的project中一般有一个nexus-agent项目，进入项目目录后，启动Agent（注意启动环境）：
```bash
cd agent
sudo PORT=8005 ./venv/bin/python main.py
```

Agent 指标接口：

```text
http://<server-ip>:8005/metrics
```

