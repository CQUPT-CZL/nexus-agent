# Nexus Agent

Nexus Agent is a web-based dashboard that provides real-time monitoring and management of agents. It consists of a Python-based server and a web-based dashboard.

## Project Structure

The project is organized into two main directories:

-   `agent/`: Contains the agent-side code.
-   `dashboard/`: Contains the web-based dashboard code.

The `dashboard/` directory includes the following files:

-   `config.json`: Configuration file for the dashboard.
-   `index.html`: The main HTML file for the dashboard.
-   `server.py`: The Python-based server for the dashboard.

## Getting Started

To get started with the Nexus Agent, you will need to have Python installed on your system. You can then run the following command to start the server:

```bash
python dashboard/server.py
```

This will start the server on port 3000. You can then access the dashboard by navigating to `http://localhost:3000` in your web browser.

## Configuration

The `dashboard/config.json` file is used to configure the list of agents that the dashboard will connect to. It is a JSON array of objects, where each object represents an agent and has the following properties:

-   `id`: A unique identifier for the agent.
-   `name`: The name of the agent.
-   `url`: The URL of the agent's endpoint.

## Agent

The `agent/` directory contains a FastAPI-based monitoring agent that collects and exposes system and GPU metrics.

### Running the Agent

You can run the agent either directly with Python or using Docker.

#### With Python

1.  Install the required dependencies:
    ```bash
    sudo python3 -m venv venv

    sudo ./venv/bin/pip install fastapi uvicorn pynvml psutil
    ```
2.  Run the agent:
    ```bash
    sudo PORT=8005 ./venv/bin/python main.py
    ```
    The agent will be available at `http://localhost:8005`.

#### With Docker

1.  Build the Docker image:
    ```bash
    docker build -t nexus-agent agent/
    ```
2.  Run the Docker container:
    ```bash
    docker run -d \
    --name nexus-agent \
    --gpus all \
    --network host \
    --restart always \
    nexus-agent
    ```
    The agent will be available at `http://localhost:8005`.

### Agent API

The agent provides the following endpoints:

#### GET /

Returns the status of the agent.

-   **Response:**
    ```json
    {
      "status": "Nexus Agent is running",
      "version": "0.1.0"
    }
    ```

#### GET /metrics

Returns detailed system and GPU metrics.

-   **Response Model:** `SystemMetrics`
    ```json
    {
      "hostname": "string",
      "os": "string",
      "uptime_seconds": "float",
      "cpu_model": "string",
      "cpu_usage": "float",
      "ram_total": "float",
      "ram_used": "float",
      "ram_percent": "float",
      "net_sent_mb": "float",
      "net_recv_mb": "float",
      "gpus": [
        {
          "id": "int",
          "name": "string",
          "temperature": "int",
          "utilization": "int",
          "memory_total": "float",
          "memory_used": "float",
          "memory_utilization": "float"
        }
      ]
    }
    ```

## API

The dashboard provides a simple API for managing the agent configuration.

### GET /api/config

Returns the current agent configuration as a JSON array.

### POST /api/config

Updates the agent configuration. The request body should be a JSON array of agent objects.

## Contributing

Contributions are welcome! Please feel free to submit a pull request with any changes.

## License

This project is licensed under the MIT License.