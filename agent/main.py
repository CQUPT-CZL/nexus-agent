import os
import time
import psutil
import platform
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import List, Optional

# 尝试导入 NVIDIA 管理库，如果是在非 GPU 机器开发，处理一下兼容性
try:
    import pynvml
    HAS_GPU = True
except ImportError:
    HAS_GPU = False
except Exception:
    HAS_GPU = False

app = FastAPI(title="Nexus Monitor Agent")

# 允许跨域，因为前端 Dashboard 可能跑在不同的 IP 上
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---

class GpuInfo(BaseModel):
    id: int
    name: str
    temperature: int
    utilization: int  # Core usage %
    memory_total: float # GB
    memory_used: float # GB
    memory_utilization: float # %

class SystemMetrics(BaseModel):
    hostname: str
    os: str
    uptime_seconds: float
    cpu_model: str
    cpu_usage: float
    ram_total: float # GB
    ram_used: float # GB
    ram_percent: float
    net_sent_mb: float
    net_recv_mb: float
    gpus: List[GpuInfo]

# --- Helper Functions ---

def get_cpu_model():
    try:
        if platform.system() == "Linux":
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        return platform.processor()
    except:
        return "Unknown CPU"

def init_nvml():
    if HAS_GPU:
        try:
            pynvml.nvmlInit()
            return True
        except:
            return False
    return False

# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    if HAS_GPU:
        try:
            pynvml.nvmlInit()
            print("✅ NVIDIA Driver detected and NVML initialized.")
        except Exception as e:
            print(f"⚠️ Failed to initialize NVML: {e}")

@app.get("/")
def read_root():
    return {"status": "Nexus Agent is running", "version": "0.1.0"}

@app.get("/metrics", response_model=SystemMetrics)
def get_metrics():
    # 1. System Basic Info
    uptime = time.time() - psutil.boot_time()
    
    # 2. CPU & RAM
    cpu_percent = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    
    # 3. Network (Total since boot, delta calculation usually handled by frontend or stateful backend, 
    #    but here we send totals and let frontend calc speed or we calc speed if we keep state)
    #    For simplicity v1: sending total bytes, let's do a simple rate calc later or just send raw.
    #    Let's send raw bytes converted to MB for now.
    net = psutil.net_io_counters()
    
    # 4. GPU Info
    gpu_list = []
    if HAS_GPU:
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                # Decoding bytes to string if necessary (older pynvml versions)
                if isinstance(name, bytes):
                    name = name.decode("utf-8")
                
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                except:
                    util = 0
                    
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except:
                    temp = 0

                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                gpu_list.append(GpuInfo(
                    id=i,
                    name=name,
                    temperature=temp,
                    utilization=util,
                    memory_total=round(mem_info.total / 1024**3, 1),
                    memory_used=round(mem_info.used / 1024**3, 1),
                    memory_utilization=round((mem_info.used / mem_info.total) * 100, 1)
                ))
        except Exception as e:
            print(f"Error reading GPU stats: {e}")
            # Fallback or empty list

    return SystemMetrics(
        hostname=platform.node(),
        os=f"{platform.system()} {platform.release()}",
        uptime_seconds=uptime,
        cpu_model=get_cpu_model(),
        cpu_usage=cpu_percent,
        ram_total=round(mem.total / 1024**3, 1),
        ram_used=round(mem.used / 1024**3, 1),
        ram_percent=mem.percent,
        net_sent_mb=round(net.bytes_sent / 1024**2, 2),
        net_recv_mb=round(net.bytes_recv / 1024**2, 2),
        gpus=gpu_list
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)