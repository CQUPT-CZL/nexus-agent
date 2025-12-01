# How to Set Up Auto-Start for Nexus Agent (Without Docker)

This guide explains how to configure the Nexus Agent to automatically start on system boot using `systemd`.

## 1. Create the `systemd` Service File

First, you need to create a service file for the Nexus Agent. You can do this by running the following command:

```bash
sudo nano /etc/systemd/system/nexus-agent.service
```

## 2. Add the Service Configuration

Next, add the following content to the `nexus-agent.service` file. This configuration assumes that you have cloned the project to `/home/czl/project/nexus-agent` and that you have a Python virtual environment set up at `/home/czl/project/nexus-agent/agent/venv`.

**Note:** If your project path or Python virtual environment is different, be sure to update the `WorkingDirectory` and `ExecStart` paths accordingly.

```ini
[Unit]
Description=Nexus Agent
After=network.target

[Service]
User=root
# 注意：这里改成你的实际路径
WorkingDirectory=/home/czl/project/nexus
Environment="PORT=8005"

# 启动命令指向 venv 里的 python
ExecStart=/home/czl/project/nexus/venv/bin/python main.py

Restart=always

[Install]
WantedBy=multi-user.target
```

## 3. Enable and Start the Service

Finally, you need to reload the `systemd` daemon, enable the service to start on boot, and then start it immediately. You can do this by running the following commands:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nexus-agent
sudo systemctl start nexus-agent
```

Your Nexus Agent should now be running and will automatically start every time the system boots.

## 4. Restarting After Code Changes

If you modify the Nexus Agent code and need to restart the service, use the following command:

```bash
sudo systemctl restart nexus-agent
```

This will gracefully restart the agent with your latest code changes.

## 5. Checking Service Status

To check the current status of the Nexus Agent service, use the following command:

```bash
sudo systemctl status nexus-agent
```

This will show you whether the service is running, any recent log output, and other status information.