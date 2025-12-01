import os
import time
import psutil
import platform
import socket
import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel
from typing import List, Optional

# --- 显卡库初始化 ---
try:
    import pynvml
    pynvml.nvmlInit()
    HAS_GPU = True
except ImportError:
    HAS_GPU = False
except Exception:
    HAS_GPU = False

app = FastAPI(title="Nexus Monitor Agent (Enhanced)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models (Pydantic) ---

class ProcessInfo(BaseModel):
    pid: int
    user: str
    command: str
    cpu_percent: float
    memory_percent: float
    gpu_index: Optional[int] = None
    vram_used_mb: Optional[int] = None

class GpuInfo(BaseModel):
    id: int
    name: str
    temperature: int
    fan_speed: int         # 新增: 风扇转速 %
    power_draw: int        # 新增: 功率 (W)
    utilization: int       # Core usage %
    memory_total: float    # GB
    memory_used: float     # GB
    memory_utilization: float # %

class SystemMetrics(BaseModel):
    hostname: str
    ip_address: str        # 新增: 本机 IP
    os: str
    uptime_seconds: float
    uptime_human: str      # 新增: 格式化时间 (例如 2d 5h)
    cpu_model: str
    cpu_usage: float
    cpu_cores: int         # 新增: 核心数
    ram_total: float       # GB
    ram_used: float        # GB
    ram_percent: float
    net_sent_mb: float
    net_recv_mb: float
    gpus: List[GpuInfo]
    processes: List[ProcessInfo] # 新增: 关键进程列表

# --- Helper Functions ---

def get_ip_address():
    """获取本机对外通信的IP地址"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def format_uptime(seconds: float) -> str:
    """将秒数转换为易读格式"""
    td = datetime.timedelta(seconds=seconds)
    days = td.days
    hours = td.seconds // 3600
    minutes = (td.seconds // 60) % 60
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"

def get_cpu_model():
    try:
        if platform.system() == "Linux":
            # 尝试从 /proc/cpuinfo 获取更准确的型号
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "model name" in line:
                        return line.split(":")[1].strip()
        return platform.processor()
    except:
        return "Unknown CPU"

# --- API Endpoints ---

@app.on_event("startup")
async def startup_event():
    if HAS_GPU:
        print("✅ NVIDIA Driver detected and NVML initialized.")
    else:
        print("⚠️ No NVIDIA GPU detected or NVML failed. Running in CPU-only mode.")

@app.get("/")
def read_root():
    return {"status": "Nexus Agent is running", "version": "0.2.0 (Enhanced)"}

@app.get("/metrics", response_model=SystemMetrics)
def get_metrics():
    # 1. System Basic Info
    boot_time = psutil.boot_time()
    uptime_sec = time.time() - boot_time
    
    # 2. CPU & RAM
    cpu_percent = psutil.cpu_percent(interval=None) # 非阻塞
    cpu_cores = psutil.cpu_count(logical=True)
    mem = psutil.virtual_memory()
    
    # 3. Network
    net = psutil.net_io_counters()
    
    # 4. GPU Info & Process Mapping
    gpu_list = []
    gpu_processes_map = {} # PID -> {gpuIdx, vram}
    
    if HAS_GPU:
        try:
            device_count = pynvml.nvmlDeviceGetCount()
            for i in range(device_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode("utf-8")
                
                # Utilization
                try:
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                except: util = 0
                
                # Temperature
                try:
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                except: temp = 0

                # Fan Speed
                try:
                    fan = pynvml.nvmlDeviceGetFanSpeed(handle)
                except: fan = 0

                # Power Usage (mW -> W)
                try:
                    power_mw = pynvml.nvmlDeviceGetPowerUsage(handle)
                    power_w = int(power_mw / 1000)
                except: power_w = 0

                # Memory
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                gpu_list.append(GpuInfo(
                    id=i,
                    name=name,
                    temperature=temp,
                    fan_speed=fan,
                    power_draw=power_w,
                    utilization=util,
                    memory_total=round(mem_info.total / 1024**3, 1),
                    memory_used=round(mem_info.used / 1024**3, 1),
                    memory_utilization=round((mem_info.used / mem_info.total) * 100, 1)
                ))

                # Mapping Processes on this GPU
                try:
                    # Combine Compute and Graphics processes
                    procs = pynvml.nvmlDeviceGetComputeRunningProcesses(handle) + \
                            pynvml.nvmlDeviceGetGraphicsRunningProcesses(handle)
                    
                    for p in procs:
                        gpu_processes_map[p.pid] = {
                            "gpu_idx": i,
                            "vram_mb": int(p.usedGpuMemory / 1024 / 1024) if p.usedGpuMemory else 0
                        }
                except Exception:
                    pass
                    
        except Exception as e:
            print(f"Error reading GPU stats: {e}")

    # 5. Process List (Top active)
    active_processes = []
    try:
        # 获取所有进程的迭代器
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cmdline', 'cpu_percent', 'memory_percent']):
            # print(proc.info)
            try:
                p_info = proc.info
                pid = p_info['pid']
                
                # 判断是否是 GPU 进程
                is_gpu_proc = pid in gpu_processes_map
                
                # 过滤策略: 显示所有 GPU 进程，或者 CPU > 2.0% 的进程
                if is_gpu_proc or (p_info['cpu_percent'] or 0) > 2.0:
                    # print(p_info)
                    
                    cmd_str = p_info['name']
                    if p_info['cmdline']:
                        cmd_str = " ".join(p_info['cmdline'][:3]) # 取命令行前3个部分
                        if len(cmd_str) > 60:
                            cmd_str = cmd_str[:57] + "..."
                    
                    gpu_idx = None
                    vram_mb = None
                    
                    if is_gpu_proc:
                        gpu_data = gpu_processes_map[pid]
                        gpu_idx = gpu_data['gpu_idx']
                        vram_mb = gpu_data['vram_mb']

                    active_processes.append(ProcessInfo(
                        pid=pid,
                        user=p_info['username'] or "system",
                        command=cmd_str,
                        cpu_percent=p_info['cpu_percent'] or 0.0,
                        memory_percent=round(p_info['memory_percent'] or 0.0, 1),
                        gpu_index=gpu_idx,
                        vram_used_mb=vram_mb
                    ))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception:
        pass

    # 排序：优先 GPU 进程，然后按 CPU 降序，限制返回数量防止 JSON 过大
    active_processes.sort(key=lambda x: (x.gpu_index is None, x.cpu_percent * -1))
    active_processes = active_processes[:10]

    return SystemMetrics(
        hostname=platform.node(),
        ip_address=get_ip_address(),
        os=f"{platform.system()} {platform.release()}",
        uptime_seconds=uptime_sec,
        uptime_human=format_uptime(uptime_sec),
        cpu_model=get_cpu_model(),
        cpu_usage=cpu_percent,
        cpu_cores=cpu_cores,
        ram_total=round(mem.total / 1024**3, 1),
        ram_used=round(mem.used / 1024**3, 1),
        ram_percent=mem.percent,
        net_sent_mb=round(net.bytes_sent / 1024**2, 2),
        net_recv_mb=round(net.bytes_recv / 1024**2, 2),
        gpus=gpu_list,
        processes=active_processes
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)