"""
装机助手 - PC Setup Assistant
一键检测硬件信息、软件激活状态、批量安装必备软件
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as tkfont
import psutil
import platform
import subprocess
import threading
import wmi
import os
from concurrent.futures import ThreadPoolExecutor
import ctypes
from datetime import datetime

# ─── 主题配置 ─────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg":         "#0f0f14",
    "sidebar":    "#16161e",
    "card":       "#1e1e2a",
    "card_hover": "#262636",
    "accent":     "#6c5ce7",
    "accent2":    "#00cec9",
    "text":       "#e8e8ef",
    "text_dim":   "#6b6b80",
    "success":    "#00b894",
    "warning":    "#fdcb6e",
    "error":      "#d63031",
    "border":     "#2d2d40",
}

SOFTWARE_LIST = [
    ("Google Chrome",        "Google.Chrome",               "浏览器",   "最流行的网页浏览器"),
    ("Firefox",              "Mozilla.Firefox",             "浏览器",   "开源隐私浏览器"),
    ("Edge",                 "Microsoft.Edge",              "浏览器",   "微软 Chromium 浏览器"),
    ("Visual Studio Code",   "Microsoft.VisualStudioCode",  "开发工具", "轻量级代码编辑器"),
    ("Git",                  "Git.Git",                     "开发工具", "分布式版本控制系统"),
    ("Python 3",             "Python.Python.3.12",          "开发工具", "Python 编程语言"),
    ("Node.js",              "OpenJS.NodeJS.LTS",           "开发工具", "JavaScript 运行时"),
    ("7-Zip",                "7zip.7zip",                   "工具软件", "开源压缩解压工具"),
    ("Bandizip",             "Bandisoft.Bandizip",          "工具软件", "免费好用的压缩工具"),
    ("Notepad++",            "Notepad++.Notepad++",         "工具软件", "增强型文本编辑器"),
    ("Everything",           "voidtools.Everything",        "工具软件", "极速文件搜索工具"),
    ("PotPlayer",            "Kakao.PotPlayer",             "影音媒体", "功能强大的媒体播放器"),
    ("QQ音乐",               "Tencent.QQMusic",             "影音媒体", "腾讯音乐客户端"),
    ("网易云音乐",            "NetEase.CloudMusic",          "影音媒体", "网易云音乐客户端"),
    ("微信",                 "Tencent.WeChat",              "社交通讯", "国民级即时通讯"),
    ("QQ",                   "Tencent.QQ",                  "社交通讯", "腾讯即时通讯"),
    ("钉钉",                 "Alibaba.DingTalk",            "办公协作", "企业办公协作平台"),
    ("飞书",                 "ByteDance.Feishu",            "办公协作", "字节跳动协作平台"),
    ("WPS Office",           "Kingsoft.WPSOffice",          "办公协作", "国产办公套件"),
    ("Adobe Acrobat Reader", "Adobe.Acrobat.Reader.64-bit", "办公协作", "PDF 阅读器"),
    ("Steam",                "Valve.Steam",                 "游戏平台", "全球最大游戏平台"),
    ("腾讯会议",              "Tencent.TencentMeeting",      "办公协作", "在线视频会议"),
    ("向日葵远程",            "Oray.Sunlogin",               "工具软件", "远程控制工具"),
    ("OBS Studio",           "OBSProject.OBSStudio",        "影音媒体", "开源直播录屏软件"),
    ("Docker Desktop",       "Docker.DockerDesktop",        "开发工具", "容器化开发平台"),
    ("Postman",              "Postman.Postman",             "开发工具", "API 开发测试工具"),
    ("Fiddler Classic",      "Telerik.FiddlerClassic",      "开发工具", "HTTP 调试代理"),
    ("Typora",               "appmakes.Typora",             "工具软件", "极简 Markdown 编辑器"),
    ("IDM",                  "Tonec.InternetDownloadManager","工具软件", "高速下载管理器"),
    ("Clash Verge",          "ClashVergeRev.ClashVergeRev", "工具软件", "网络代理工具"),
]


# ─── 工具函数 ────────────────────────────────────────────

def run_cmd(cmd, timeout=15):
    try:
        r = subprocess.run(
            cmd, capture_output=True,
            timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW, shell=True,
        )
        for enc in ("utf-8", "gbk", "cp936", "latin-1"):
            try:
                return r.stdout.decode(enc).strip()
            except (UnicodeDecodeError, LookupError):
                continue
        return r.stdout.decode("latin-1", errors="replace").strip()
    except Exception:
        return ""


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════
#  硬件信息采集
# ═══════════════════════════════════════════════════════════

class HardwareCollector:
    def __init__(self):
        self._local = threading.local()

    def _get_conn(self):
        """每个线程独立的 WMI 连接（COM 对象不可跨线程）"""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            try:
                import pythoncom
                pythoncom.CoInitialize()
                conn = wmi.WMI()
            except Exception:
                conn = None
            self._local.conn = conn
        return conn

    def _wmi_query(self, cls_name, fallback=None):
        """安全 WMI 查询，失败返回 fallback 而非抛异常"""
        conn = self._get_conn()
        if not conn:
            return fallback or []
        try:
            return getattr(conn, cls_name)()
        except Exception:
            return fallback or []

    def get_cpu_info(self):
        info = {}
        try:
            # 用 WMI 取 CPU 信息（比 cpuinfo 快 10 倍以上）
            procs = self._wmi_query("Win32_Processor")
            if procs:
                p = procs[0]
                info["名称"] = (p.Name or "未知").strip()
                info["核心数"] = f"{p.NumberOfCores or '?'} 物理 / {p.NumberOfLogicalProcessors or '?'} 逻辑"
                if p.MaxClockSpeed:
                    info["最高频率"] = f"{p.MaxClockSpeed} MHz"
                if p.L2CacheSize:
                    info["L2 缓存"] = f"{p.L2CacheSize} KB"
                if p.L3CacheSize:
                    info["L3 缓存"] = f"{p.L3CacheSize} KB"
            else:
                info["名称"] = platform.processor() or "未知"
            info["架构"] = platform.machine()
            freq = psutil.cpu_freq()
            if freq:
                info["当前频率"] = f"{freq.current:.0f} MHz"
            info["当前占用"] = f"{psutil.cpu_percent(interval=0)}%"
        except Exception:
            pass
        return info

    def get_memory_info(self):
        info = {}
        try:
            mem = psutil.virtual_memory()
            info["总容量"] = f"{mem.total / (1024**3):.1f} GB"
            info["已使用"] = f"{mem.used / (1024**3):.1f} GB"
            info["可用"] = f"{mem.available / (1024**3):.1f} GB"
            info["使用率"] = f"{mem.percent}%"
            swap = psutil.swap_memory()
            if swap.total > 0:
                info["虚拟内存"] = f"{swap.total / (1024**3):.1f} GB"
            for i, chip in enumerate(self._wmi_query("Win32_PhysicalMemory")):
                try:
                    cap = int(chip.Capacity) / (1024**3) if chip.Capacity else 0
                    speed = chip.Speed or "?"
                    mfr = (chip.Manufacturer or "未知").strip()
                    part = (chip.PartNumber or "").strip()
                    desc = f"{cap:.0f} GB  {speed} MHz  {mfr}"
                    if part:
                        desc += f"  {part}"
                    info[f"内存条{i+1}"] = desc
                except (ValueError, TypeError):
                    info[f"内存条{i+1}"] = chip.Caption or "检测异常"
        except Exception:
            pass
        return info

    def get_disk_info(self):
        info = {}
        try:
            for part in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    info[f"分区 {part.mountpoint}"] = (
                        f"{usage.total / (1024**3):.0f} GB 总量 | "
                        f"{usage.used / (1024**3):.0f} GB 已用 | "
                        f"{usage.free / (1024**3):.0f} GB 可用 | {part.fstype}"
                    )
                except OSError:
                    pass
            for disk in self._wmi_query("Win32_DiskDrive"):
                try:
                    size = int(disk.Size) / (1024**3) if disk.Size else 0
                    model = disk.Model or "未知型号"
                    interface = disk.InterfaceType or ""
                    info[f"磁盘{disk.Index} ({model})"] = f"{size:.0f} GB  {interface}"
                except (ValueError, TypeError):
                    pass
        except Exception:
            pass
        return info

    def get_gpu_info(self):
        info = {}
        try:
            idx = 0
            for gpu in self._wmi_query("Win32_VideoController"):
                name = gpu.Name or "未知显卡"
                skip = ("idd", "virtual", "oray", "gameviewer")
                if any(kw in name.lower() for kw in skip):
                    continue
                info[f"GPU{idx} 名称"] = name
                try:
                    vram = int(gpu.AdapterRAM) / (1024**2) if gpu.AdapterRAM else 0
                    if vram > 0:
                        info[f"GPU{idx} 显存"] = f"{vram:.0f} MB"
                except (ValueError, TypeError):
                    pass
                info[f"GPU{idx} 驱动"] = gpu.DriverVersion or "未知"
                vmd = gpu.VideoModeDescription or ""
                if "x" in vmd:
                    parts = vmd.split("x")
                    try:
                        w, h = int(parts[0].strip()), int(parts[1].strip().split()[0])
                        if 0 < w < 99999 and 0 < h < 99999:
                            info[f"GPU{idx} 分辨率"] = f"{w} x {h}"
                    except (ValueError, IndexError):
                        pass
                idx += 1
            if not info:
                smi = run_cmd("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits")
                if smi:
                    for i, line in enumerate(smi.strip().split("\n")):
                        p = [x.strip() for x in line.split(",")]
                        info[f"GPU{i} 名称"] = p[0]
                        if len(p) > 1 and p[1]:
                            info[f"GPU{i} 显存"] = f"{p[1]} MB"
        except Exception:
            pass
        return info

    def get_motherboard_info(self):
        info = {}
        try:
            # 主板信息
            boards = self._wmi_query("Win32_BaseBoard")
            if boards:
                b = boards[0]
                mfr = (b.Manufacturer or "").strip()
                prod = (b.Product or "").strip()
                if mfr:
                    info["制造商"] = mfr
                if prod:
                    info["型号"] = prod
                if b.SerialNumber:
                    info["序列号"] = b.SerialNumber
            # 兜底：从 ComputerSystem 取制造商
            if "制造商" not in info:
                for cs in self._wmi_query("Win32_ComputerSystem"):
                    mfr = (cs.Manufacturer or "").strip()
                    if mfr:
                        info["制造商"] = mfr
                        break
            if "型号" not in info:
                for cs in self._wmi_query("Win32_ComputerSystem"):
                    model = (cs.Model or "").strip()
                    if model:
                        info["型号"] = model
                        break
            # BIOS
            bios_list = self._wmi_query("Win32_BIOS")
            if bios_list:
                bios = bios_list[0]
                bios_mfr = (bios.Manufacturer or "").strip()
                bios_ver = (bios.SMBIOSBIOSVersion or "").strip()
                if bios_mfr or bios_ver:
                    info["BIOS"] = f"{bios_mfr} {bios_ver}".strip()
                rd = bios.ReleaseDate
                if rd and len(rd) >= 8:
                    info["BIOS日期"] = f"{rd[:4]}-{rd[4:6]}-{rd[6:8]}"
        except Exception:
            pass
        return info

    def get_network_info(self):
        info = {}
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            for name, addr_list in addrs.items():
                if name == "lo" or name.startswith("Loopback"):
                    continue
                for addr in addr_list:
                    if addr.family.name == "AF_INET" and not addr.address.startswith("169.254"):
                        speed = ""
                        if name in stats and stats[name].speed > 0:
                            speed = f" | {stats[name].speed} Mbps"
                        info[name] = f"IP: {addr.address}{speed}"
        except Exception:
            pass
        return info

    def get_os_info(self):
        info = {}
        try:
            info["系统"] = f"{platform.system()} {platform.release()}"
            info["版本号"] = platform.version()
            info["计算机名"] = platform.node()
            info["用户名"] = os.getlogin()
            info["系统位数"] = platform.architecture()[0]
            boot = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot
            d, rem = uptime.days, uptime.seconds
            h, m = divmod(rem, 60)
            parts = []
            if d:
                parts.append(f"{d}天")
            if h:
                parts.append(f"{h}小时")
            parts.append(f"{m}分钟")
            info["开机时间"] = boot.strftime("%Y-%m-%d %H:%M")
            info["运行时长"] = " ".join(parts)
            # 从注册表读取（比 slmgr.vbs / PowerShell 快 100 倍）
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
                )
                build_num = 0
                try:
                    info["版本名称"] = winreg.QueryValueEx(key, "ProductName")[0]
                except Exception:
                    pass
                try:
                    info["版本号"] = winreg.QueryValueEx(key, "DisplayVersion")[0]
                except Exception:
                    pass
                try:
                    build_num = int(winreg.QueryValueEx(key, "CurrentBuild")[0])
                    info["构建号"] = str(build_num)
                except Exception:
                    pass
                winreg.CloseKey(key)
                # Windows 11 注册表 ProductName 仍写 "Windows 10"，需根据构建号修正
                if build_num >= 22000 and "版本名称" in info:
                    info["版本名称"] = info["版本名称"].replace("Windows 10", "Windows 11")
            except Exception:
                pass
        except Exception:
            pass
        return info

    def get_activation_status(self):
        """单独查询激活状态"""
        try:
            for prod in self._wmi_query("SoftwareLicensingProduct"):
                if prod.PartialProductKey and prod.LicenseStatus == 1:
                    return "已激活"
            return "未检测到"
        except Exception:
            return "检测失败"

    def get_monitor_info(self):
        info = {}
        try:
            monitor_names = []
            for mon in self._wmi_query("Win32_DesktopMonitor"):
                name = (mon.Name or "").strip()
                if name and name != "默认监视器":
                    monitor_names.append(name)
            try:
                user32 = ctypes.windll.user32
                w = user32.GetSystemMetrics(0)
                h = user32.GetSystemMetrics(1)
                if monitor_names:
                    info[monitor_names[0]] = f"{w} x {h}"
                else:
                    info["主显示器"] = f"{w} x {h}"
            except Exception:
                pass
            # 刷新率
            try:
                class DEVMODE(ctypes.Structure):
                    _fields_ = [
                        ("dmDeviceName", ctypes.c_wchar * 32),
                        ("dmSpecVersion", ctypes.c_uint16),
                        ("dmDriverVersion", ctypes.c_uint16),
                        ("dmSize", ctypes.c_uint16),
                        ("dmDriverExtra", ctypes.c_uint16),
                        ("dmFields", ctypes.c_uint32),
                        ("dmPositionX", ctypes.c_int32),
                        ("dmPositionY", ctypes.c_int32),
                        ("dmDisplayOrientation", ctypes.c_uint32),
                        ("dmDisplayFixedOutput", ctypes.c_uint32),
                        ("dmColor", ctypes.c_int16),
                        ("dmDuplex", ctypes.c_int16),
                        ("dmYResolution", ctypes.c_int16),
                        ("dmTTOption", ctypes.c_int16),
                        ("dmCollate", ctypes.c_int16),
                        ("dmFormName", ctypes.c_wchar * 32),
                        ("dmLogPixels", ctypes.c_uint16),
                        ("dmBitsPerPel", ctypes.c_uint32),
                        ("dmPelsWidth", ctypes.c_uint32),
                        ("dmPelsHeight", ctypes.c_uint32),
                        ("dmDisplayFlags", ctypes.c_uint32),
                        ("dmDisplayFrequency", ctypes.c_uint32),
                    ]
                dm = DEVMODE()
                dm.dmSize = ctypes.sizeof(DEVMODE)
                if ctypes.windll.user32.EnumDisplaySettingsW(None, 0xFFFFFFFF, ctypes.byref(dm)):
                    freq = dm.dmDisplayFrequency
                    if freq and freq > 0:
                        info["刷新率"] = f"{freq} Hz"
            except Exception:
                pass
            for i, name in enumerate(monitor_names[1:], 2):
                info[f"显示器{i}"] = name
        except Exception:
            pass
        return info

    def get_all(self):
        # 并行执行所有检测，总耗时 = 最慢单项耗时（而非总和）
        tasks = {
            "操作系统": self.get_os_info,
            "处理器 (CPU)": self.get_cpu_info,
            "内存 (RAM)": self.get_memory_info,
            "显卡 (GPU)": self.get_gpu_info,
            "存储设备": self.get_disk_info,
            "主板": self.get_motherboard_info,
            "显示器": self.get_monitor_info,
            "网络": self.get_network_info,
        }
        results = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(fn): key for key, fn in tasks.items()}
            for future in futures:
                key = futures[future]
                try:
                    results[key] = future.result(timeout=10)
                except Exception:
                    results[key] = {}
        # 保持原始顺序
        return {k: results.get(k, {}) for k in tasks}


# ═══════════════════════════════════════════════════════════
#  软件检测（带缓存）
# ═══════════════════════════════════════════════════════════

class SoftwareDetector:
    _cache = None

    @classmethod
    def check_installed(cls, force=False):
        if cls._cache is not None and not force:
            return cls._cache
        result = {}
        try:
            output = run_cmd("winget list --accept-source-agreements", timeout=30)
            low = output.lower()
            for name, wid, cat, desc in SOFTWARE_LIST:
                result[wid] = wid.lower() in low or name.lower() in low
        except Exception:
            for _, wid, _, _ in SOFTWARE_LIST:
                result[wid] = False
        cls._cache = result
        return result

    @classmethod
    def invalidate(cls):
        cls._cache = None


# ═══════════════════════════════════════════════════════════
#  UI 组件
# ═══════════════════════════════════════════════════════════

class CardScrollView(ctk.CTkFrame):
    """
    基于 Canvas 的卡片式滚动视图。
    用 create_rectangle + create_text 渲染卡片，无嵌入 widget，滚动流畅。
    """
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)

        self.canvas = tk.Canvas(
            self, bg=COLORS["bg"], highlightthickness=0, bd=0,
        )
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self._cards = []          # [(title, data_dict), ...]
        self._card_positions = []  # [(y, height), ...]
        self._total_h = 0
        self._key_font = tkfont.Font(family="Microsoft YaHei UI", size=12)

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<MouseWheel>", self._on_wheel)

    def clear(self):
        self.canvas.delete("all")
        self._cards.clear()
        self._card_positions.clear()
        self._total_h = 0

    def add_card(self, title, data: dict):
        """添加一个卡片区块"""
        self._cards.append((title, data))

    def render_all(self):
        """渲染所有卡片"""
        self._calc_positions()
        self._paint()

    def _calc_positions(self):
        """计算每张卡片的 y 坐标和高度"""
        self._card_positions.clear()
        y = 12
        for title, data in self._cards:
            rows = len(data)
            h = 44 + rows * 26 + 14  # title bar + rows + padding
            self._card_positions.append((y, h))
            y += h + 14  # card gap
        self._total_h = y

    def _paint(self):
        """绘制所有卡片到 Canvas"""
        self.canvas.delete("all")
        w = self.canvas.winfo_width() - 4
        if w < 100:
            return
        self._rendered_w = w

        card_x = 12
        card_w = w - 24

        for i, (title, data) in enumerate(self._cards):
            cy, ch = self._card_positions[i]

            # 卡片背景矩形
            self.canvas.create_rectangle(
                card_x, cy, card_x + card_w, cy + ch,
                fill=COLORS["card"], outline=COLORS["border"], width=1,
            )
            # 标题
            self.canvas.create_text(
                card_x + 16, cy + 14, text=title,
                font=("Microsoft YaHei UI", 14, "bold"),
                fill=COLORS["accent2"], anchor="nw",
            )
            # 分隔线
            sep_y = cy + 40
            self.canvas.create_line(
                card_x + 12, sep_y, card_x + card_w - 12, sep_y,
                fill=COLORS["border"],
            )
            # 数据行 — 先测量最长键名，动态定位值
            max_kw = 0
            for k in data:
                kw = self._key_font.measure(k)
                if kw > max_kw:
                    max_kw = kw
            val_x = card_x + 24 + max_kw + 12  # 键名右侧留 12px 间距
            val_x = min(val_x, card_x + card_w - 60)  # 不超出卡片

            ry = sep_y + 10
            for k, v in data.items():
                self.canvas.create_text(
                    card_x + 24, ry, text=k,
                    font=("Microsoft YaHei UI", 12),
                    fill=COLORS["text_dim"], anchor="nw",
                )
                # 长值自动截断
                max_val_w = card_x + card_w - val_x - 16
                display_v = v
                while self._key_font.measure(display_v) > max_val_w and len(display_v) > 4:
                    display_v = display_v[:-4] + "..."
                self.canvas.create_text(
                    val_x, ry, text=display_v,
                    font=("Microsoft YaHei UI", 12),
                    fill=COLORS["text"], anchor="nw",
                )
                ry += 26

        self.canvas.configure(scrollregion=(0, 0, w, self._total_h))

    def _on_resize(self, event):
        """窗口大小变化时重绘"""
        self._paint()

    def _on_wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class TextScrollView(ctk.CTkFrame):
    """
    基于 tk.Text 的高性能滚动视图。
    tk.Text 原生处理滚动，快速拖拽滚动条时文字不会粘滞。
    """
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)

        self.text = tk.Text(
            self, bg=COLORS["bg"], fg=COLORS["text"],
            font=("Microsoft YaHei UI", 13),
            relief="flat", bd=0, highlightthickness=0,
            wrap="word", cursor="arrow",
            state="disabled",
            spacing1=2, spacing3=2,
            padx=8, pady=4,
        )
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        # 样式标签
        self.text.tag_configure("header",   font=("Microsoft YaHei UI", 15, "bold"), foreground=COLORS["accent2"], spacing3=6)
        self.text.tag_configure("name",     font=("Microsoft YaHei UI", 14, "bold"), foreground=COLORS["text"])
        self.text.tag_configure("name_dim", font=("Microsoft YaHei UI", 14, "bold"), foreground=COLORS["text_dim"])
        self.text.tag_configure("desc",     font=("Microsoft YaHei UI", 11),         foreground=COLORS["text_dim"])
        self.text.tag_configure("ok",       font=("Microsoft YaHei UI", 13, "bold"), foreground=COLORS["success"])
        self.text.tag_configure("no",       font=("Microsoft YaHei UI", 13, "bold"), foreground=COLORS["text_dim"])
        self.text.tag_configure("dot_ok",   font=("Microsoft YaHei UI", 15),         foreground=COLORS["success"])
        self.text.tag_configure("dot_no",   font=("Microsoft YaHei UI", 15),         foreground=COLORS["text_dim"])
        self.text.tag_configure("cat",      font=("Microsoft YaHei UI", 11),         foreground=COLORS["accent2"])
        self.text.tag_configure("sep",      font=("Microsoft YaHei UI", 2),          foreground=COLORS["border"])
        self.text.tag_configure("sec_title",font=("Microsoft YaHei UI", 15, "bold"), foreground=COLORS["accent"], spacing1=10, spacing3=4)
        self.text.tag_configure("sec_key",  font=("Microsoft YaHei UI", 12),         foreground=COLORS["text_dim"])
        self.text.tag_configure("sec_val",  font=("Microsoft YaHei UI", 12),         foreground=COLORS["text"])
        self.text.tag_configure("chk_on",   font=("Microsoft YaHei UI", 15, "bold"), foreground=COLORS["accent2"])
        self.text.tag_configure("chk_off",  font=("Microsoft YaHei UI", 15, "bold"), foreground=COLORS["accent"])
        self.text.tag_configure("chk_dis",  font=("Microsoft YaHei UI", 15, "bold"), foreground=COLORS["text_dim"])
        self.text.tag_configure("status_ok",font=("Microsoft YaHei UI", 12),         foreground=COLORS["success"])
        self.text.tag_configure("status_no",font=("Microsoft YaHei UI", 12),         foreground=COLORS["text_dim"])

        # 可点击行追踪
        self._click_items = {}   # tag -> {checked, name, wid, on_toggle}
        self._hover_row = None

        self.text.bind("<Button-1>", self._on_click)
        self.text.bind("<Motion>", self._on_motion)
        self.text.bind("<Leave>", lambda e: self._clear_hover())

    def clear(self):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")
        self._click_items.clear()

    def _append(self, text_str, tags=(), row_tag=None):
        if row_tag:
            tags = tuple(tags) + (row_tag,)
            if row_tag not in self.text.tag_names():
                self.text.tag_configure(row_tag)
        self.text.configure(state="normal")
        self.text.insert("end", text_str, tags)
        self.text.configure(state="disabled")

    def add_category(self, title):
        self._append(f"\n{title}\n", ("header",))
        self._append("─" * 60 + "\n", ("sep",))

    def add_info_row(self, name, desc, installed):
        dot_tag = "dot_ok" if installed else "dot_no"
        self._append(" ● ", (dot_tag,))
        icon = "✓" if installed else "✗"
        icon_tag = "ok" if installed else "no"
        self._append(f"{icon}  ", (icon_tag,))
        name_tag = "name" if installed else "name_dim"
        self._append(name, (name_tag,))
        self._append(f"   {desc}\n", ("desc",))

    def add_check_row(self, name, wid, desc, cat, installed):
        row_tag = f"row_{len(self._click_items)}"
        if installed:
            self._append(" ● ", ("dot_ok",), row_tag=row_tag)
            self._append("☑ ", ("chk_dis",), row_tag=row_tag)
            self._append(name, ("name_dim",), row_tag=row_tag)
            self._append(f"   {desc}", ("desc",), row_tag=row_tag)
            self._append(f"        {cat}", ("cat",), row_tag=row_tag)
            self._append("   已安装\n", ("status_ok",))
            self._click_items[row_tag] = {
                "checked": False, "name": name, "wid": wid, "installed": True,
            }
        else:
            self._append(" ● ", ("dot_no",), row_tag=row_tag)
            self._append("☐ ", ("chk_off",), row_tag=row_tag)
            self._append(name, ("name",), row_tag=row_tag)
            self._append(f"   {desc}", ("desc",), row_tag=row_tag)
            self._append(f"        {cat}", ("cat",), row_tag=row_tag)
            self._append("   待安装\n", ("status_no",))
            self._click_items[row_tag] = {
                "checked": False, "name": name, "wid": wid, "installed": False,
            }

    def add_section(self, title, data: dict):
        """渲染一个带标题的键值对区块"""
        self._append(f"\n{title}\n", ("sec_title",))
        self._append("─" * 60 + "\n", ("sep",))
        for k, v in data.items():
            self._append(f"  {k:<12}", ("sec_key",))
            self._append(f"  {v}\n", ("sec_val",))

    def _on_click(self, e):
        idx = self.text.index(f"@{e.x},{e.y}")
        for tag in self.text.tag_names(idx):
            if tag in self._click_items:
                item = self._click_items[tag]
                if not item["installed"]:
                    item["checked"] = not item["checked"]
                    self._refresh_check(tag, item)
                return

    def _refresh_check(self, tag, item):
        # 只替换勾选符号，不影响其他标签
        ranges = self.text.tag_ranges(tag)
        if not ranges:
            return
        start = str(ranges[0])
        # 找到该 tag 范围内的 "☐" 或 "☑"
        end = str(ranges[1])
        self.text.configure(state="normal")
        content = self.text.get(start, end)
        idx = content.find("☐")
        if idx < 0:
            idx = content.find("☑")
        if idx >= 0:
            char_pos = f"{start}+{idx}c"
            self.text.delete(char_pos)
            sym = "☑" if item["checked"] else "☐"
            sym_tag = "chk_on" if item["checked"] else "chk_off"
            self.text.insert(char_pos, sym, (tag, sym_tag))
        self.text.configure(state="disabled")

    def _on_motion(self, e):
        idx = self.text.index(f"@{e.x},{e.y}")
        found = None
        for tag in self.text.tag_names(idx):
            if tag in self._click_items:
                found = tag
                break
        if found != self._hover_row:
            self._clear_hover()
            if found:
                self._hover_row = found
                self.text.tag_configure(found, background=COLORS["card_hover"])

    def _clear_hover(self):
        if self._hover_row:
            self.text.tag_configure(self._hover_row, background="")
            self._hover_row = None

    def get_selected(self):
        return [(v["name"], v["wid"]) for v in self._click_items.values()
                if v["checked"] and not v["installed"]]

    def select_all(self, val=True):
        for tag, item in self._click_items.items():
            if not item["installed"]:
                item["checked"] = val
                self._refresh_check(tag, item)


# ═══════════════════════════════════════════════════════════
#  主应用
# ═══════════════════════════════════════════════════════════

class SetupAssistant(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("装机助手")
        self.geometry("1080x720")
        self.minsize(900, 600)
        self.configure(fg_color=COLORS["bg"])

        self.hw = HardwareCollector()
        self.pages = {}
        self.current_page = None
        self._hw_data = None
        self._sw_data = None
        self._fading = False
        self._sys_loaded = False
        self._sys_loading = False

        self._build_sidebar()
        self._build_pages()
        self._show_page("system")

        # 后台预加载其他页面数据
        self.after(500, self._background_preload)

    def _background_preload(self):
        """启动时后台预加载硬件和软件数据"""
        def load_hw():
            if self._hw_data is None:
                self._hw_data = self.hw.get_all()
                self.after(0, self._on_hw_preloaded)
        def load_sw():
            if self._sw_data is None:
                self._sw_data = SoftwareDetector.check_installed()
        threading.Thread(target=load_hw, daemon=True).start()
        threading.Thread(target=load_sw, daemon=True).start()

    def _on_hw_preloaded(self):
        """硬件数据预加载完成，如果当前在系统页且未加载过则渲染"""
        if self.current_page == "system" and not self._sys_loaded:
            self._load_system_info()

    # ─── 侧边栏 ──────────────────────────────────────────
    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, fg_color=COLORS["sidebar"], width=200, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo.pack(fill="x", padx=16, pady=(24, 8))
        ctk.CTkLabel(logo, text="⚡", font=ctk.CTkFont(size=32)).pack(side="left")
        ctk.CTkLabel(logo, text="装机助手", font=ctk.CTkFont(size=18, weight="bold"),
                      text_color=COLORS["text"]).pack(side="left", padx=8)
        ctk.CTkFrame(self.sidebar, fg_color=COLORS["border"], height=1).pack(fill="x", padx=16, pady=(8, 16))

        nav = [
            ("system",   "💻  系统信息", "查看硬件和系统详情"),
            ("software", "📦  软件状态", "检测已安装软件"),
            ("install",  "🚀  一键装机", "批量安装必备软件"),
        ]
        self.nav_btns = {}
        for pid, text, hint in nav:
            frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
            frame.pack(fill="x", padx=8, pady=2)
            btn = ctk.CTkButton(frame, text=text, font=ctk.CTkFont(size=14),
                                 fg_color="transparent", hover_color=COLORS["card"],
                                 text_color=COLORS["text"], anchor="w", height=40,
                                 corner_radius=8, command=lambda p=pid: self._show_page(p))
            btn.pack(fill="x")
            hl = ctk.CTkLabel(frame, text=hint, font=ctk.CTkFont(size=10),
                               text_color=COLORS["text_dim"], anchor="w")
            hl.pack(fill="x", padx=16)
            self.nav_btns[pid] = (btn, hl)

        spacer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)
        bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        bottom.pack(fill="x", padx=16, pady=16)
        ctk.CTkLabel(bottom, text=f"v1.0  |  {datetime.now().strftime('%Y.%m')}",
                      font=ctk.CTkFont(size=10), text_color=COLORS["text_dim"]).pack()

    # ─── 页面构建 ─────────────────────────────────────────
    def _build_pages(self):
        self.page_container = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.page_container.pack(side="left", fill="both", expand=True)

        self.pages["system"]   = self._build_system_page()
        self.pages["software"] = self._build_software_page()
        self.pages["install"]  = self._build_install_page()

    # ─── 页面切换 ─────────────────────────────────────────
    def _show_page(self, pid):
        if pid == self.current_page or self._fading:
            return
        self._fading = True

        old_widget = self.pages.get(self.current_page) if self.current_page else None
        new_widget = self.pages[pid]

        for k, (btn, hl) in self.nav_btns.items():
            if k == pid:
                btn.configure(fg_color=COLORS["card"])
                hl.configure(text_color=COLORS["accent"])
            else:
                btn.configure(fg_color="transparent")
                hl.configure(text_color=COLORS["text_dim"])

        overlay = tk.Canvas(self.page_container, bg=COLORS["bg"], highlightthickness=0, bd=0)
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._fade_overlay = overlay
        self._fade_alpha = 0.0
        self._fade_old_widget = old_widget
        self._fade_new_widget = new_widget
        self._fade_pid = pid
        self._fade_phase = "out"
        self._do_fade_step()

    def _do_fade_step(self):
        step = 0.12
        if self._fade_phase == "out":
            self._fade_alpha = min(self._fade_alpha + step, 1.0)
            g = int(15 * self._fade_alpha)
            self._fade_overlay.configure(bg=f"#{g:02x}{g:02x}{min(g+5,255):02x}")
            if self._fade_alpha >= 1.0:
                if self._fade_old_widget:
                    self._fade_old_widget.pack_forget()
                self._fade_new_widget.pack(fill="both", expand=True)
                self.current_page = self._fade_pid
                self._fade_phase = "in"
                self._trigger_load(self._fade_pid)
        else:
            self._fade_alpha = max(self._fade_alpha - step, 0.0)
            g = int(15 * self._fade_alpha)
            self._fade_overlay.configure(bg=f"#{g:02x}{g:02x}{min(g+5,255):02x}")
            if self._fade_alpha <= 0.0:
                self._fade_overlay.destroy()
                self._fading = False
                return
        self.after(16, self._do_fade_step)

    def _trigger_load(self, pid):
        if pid == "system":
            if not self._sys_loaded:
                self.after(50, self._load_system_info)
        elif pid == "software":
            if self._sw_data:
                self._render_software_status(self._sw_data)
            else:
                self.after(50, self._load_software_status)
        elif pid == "install":
            if self._sw_data:
                self._render_install_list(self._sw_data)
            else:
                self.after(50, self._load_install_page)

    # ─── 系统信息页面 ──────────────────────────────────────
    def _build_system_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(top, text="系统信息", font=ctk.CTkFont(size=24, weight="bold"),
                      text_color=COLORS["text"]).pack(side="left")
        ctk.CTkButton(top, text="🔄 刷新", width=80, fg_color=COLORS["accent"],
                       hover_color="#5b4bd5",
                       command=lambda: self._load_system_info(force=True)).pack(side="right")

        self.sys_cards = CardScrollView(page)
        self.sys_cards.pack(fill="both", expand=True, padx=24, pady=(8, 24))
        return page

    def _load_system_info(self, force=False):
        if force:
            self._sys_loaded = False
        if self._sys_loaded or self._sys_loading:
            return  # 已加载过或正在加载中

        self._sys_loaded = True
        self._sys_loading = True

        def worker():
            try:
                if self._hw_data is None or force:
                    self._hw_data = self.hw.get_all()
                activation = self.hw.get_activation_status()
                self.after(0, lambda: self._render_system_info(self._hw_data, activation))
            finally:
                self._sys_loading = False
        threading.Thread(target=worker, daemon=True).start()

    def _render_system_info(self, data, activation=None):
        self.sys_cards.clear()
        self._sys_render_gen = getattr(self, "_sys_render_gen", 0) + 1
        icons = {
            "操作系统": "🖥️", "处理器 (CPU)": "🧠", "内存 (RAM)": "📊",
            "显卡 (GPU)": "🎮", "存储设备": "💾", "主板": "🔧",
            "显示器": "🖥️", "网络": "🌐",
        }
        for section, info in data.items():
            if not info:
                continue
            icon = icons.get(section, "📋")
            self.sys_cards.add_card(f"{icon}  {section}", info)

        if activation:
            self.sys_cards.add_card("📋  激活状态", {"状态": activation})
        self.sys_cards.render_all()

    # ─── 软件状态页面 ──────────────────────────────────────
    def _build_software_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(top, text="软件状态", font=ctk.CTkFont(size=24, weight="bold"),
                      text_color=COLORS["text"]).pack(side="left")
        self.sw_count = ctk.CTkLabel(top, text="", font=ctk.CTkFont(size=13),
                                      text_color=COLORS["text_dim"])
        self.sw_count.pack(side="left", padx=16)
        ctk.CTkButton(top, text="🔄 重新检测", width=100, fg_color=COLORS["accent"],
                       hover_color="#5b4bd5",
                       command=lambda: self._load_software_status(force=True)).pack(side="right")

        self.sw_text = TextScrollView(page)
        self.sw_text.pack(fill="both", expand=True, padx=24, pady=(8, 24))
        return page

    def _load_software_status(self, force=False):
        if not force and self._sw_data:
            self._render_software_status(self._sw_data)
            return
        self.sw_text.clear()
        self.sw_text._append("  正在检测已安装软件...\n", ("desc",))

        def worker():
            data = SoftwareDetector.check_installed(force=force)
            self._sw_data = data
            self.after(0, lambda: self._render_software_status(data))
        threading.Thread(target=worker, daemon=True).start()

    def _render_software_status(self, installed):
        self.sw_text.clear()
        total = len(SOFTWARE_LIST)
        cnt = sum(1 for v in installed.values() if v)
        self.sw_count.configure(text=f"已安装 {cnt} / {total}")

        categories = {}
        for name, wid, cat, desc in SOFTWARE_LIST:
            categories.setdefault(cat, []).append((name, wid, desc, installed.get(wid, False)))

        for cat, items in categories.items():
            self.sw_text.add_category(cat)
            for name, wid, desc, ok in items:
                self.sw_text.add_info_row(name, desc, ok)

    # ─── 一键装机页面 ──────────────────────────────────────
    def _build_install_page(self):
        page = ctk.CTkFrame(self.page_container, fg_color="transparent")
        top = ctk.CTkFrame(page, fg_color="transparent")
        top.pack(fill="x", padx=24, pady=(20, 8))
        ctk.CTkLabel(top, text="一键装机", font=ctk.CTkFont(size=24, weight="bold"),
                      text_color=COLORS["text"]).pack(side="left")
        ctk.CTkLabel(top, text="勾选需要安装的软件，点击开始安装",
                      font=ctk.CTkFont(size=13), text_color=COLORS["text_dim"]).pack(side="left", padx=16)

        btn_box = ctk.CTkFrame(top, fg_color="transparent")
        btn_box.pack(side="right")
        self.sel_all_var = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(btn_box, text="全选未安装", variable=self.sel_all_var,
                         font=ctk.CTkFont(size=13), fg_color=COLORS["accent"],
                         hover_color=COLORS["accent2"], border_color=COLORS["border"],
                         command=self._toggle_select_all).pack(side="left", padx=8)
        self.install_btn = ctk.CTkButton(btn_box, text="🚀 开始安装", width=130, height=36,
                                          font=ctk.CTkFont(size=14),
                                          fg_color=COLORS["success"], hover_color="#00a884",
                                          command=self._start_install)
        self.install_btn.pack(side="left")

        self.install_text = TextScrollView(page)
        self.install_text.pack(fill="both", expand=True, padx=24, pady=(8, 12))

        self.progress_frame = ctk.CTkFrame(page, fg_color=COLORS["card"],
                                            corner_radius=12, border_width=1,
                                            border_color=COLORS["border"])
        self._prog_visible = False
        self.prog_bar = ctk.CTkProgressBar(self.progress_frame, fg_color=COLORS["bg"],
                                            progress_color=COLORS["accent"], height=6)
        self.prog_bar.pack(fill="x", padx=16, pady=(12, 4))
        self.prog_bar.set(0)
        self.prog_label = ctk.CTkLabel(self.progress_frame, text="就绪",
                                        font=ctk.CTkFont(size=13), text_color=COLORS["text_dim"])
        self.prog_label.pack(padx=16, pady=(0, 12))
        return page

    def _load_install_page(self, force=False):
        if not force and self._sw_data:
            self._render_install_list(self._sw_data)
            return
        self.install_text.clear()
        self.install_text._append("  正在检测软件状态...\n", ("desc",))

        def worker():
            data = SoftwareDetector.check_installed(force=force)
            self._sw_data = data
            self.after(0, lambda: self._render_install_list(data))
        threading.Thread(target=worker, daemon=True).start()

    def _render_install_list(self, installed):
        self.install_text.clear()
        categories = {}
        for name, wid, cat, desc in SOFTWARE_LIST:
            categories.setdefault(cat, []).append((name, wid, desc, installed.get(wid, False)))

        for cat, items in categories.items():
            self.install_text.add_category(cat)
            for name, wid, desc, ok in items:
                self.install_text.add_check_row(name, wid, desc, cat, ok)

    def _toggle_select_all(self):
        self.install_text.select_all(self.sel_all_var.get())

    def _start_install(self):
        selected = self.install_text.get_selected()
        if not selected:
            messagebox.showinfo("提示", "请先勾选要安装的软件")
            return
        if not is_admin():
            messagebox.showwarning("权限不足",
                                   "安装软件需要管理员权限，请以管理员身份运行本程序。\n\n"
                                   "右键点击程序 → 以管理员身份运行")
            return

        if not self._prog_visible:
            self.progress_frame.pack(fill="x", padx=24, pady=(0, 16), before=self.install_text)
            self._prog_visible = True
        self.prog_bar.set(0)
        self.install_btn.configure(state="disabled", text="安装中...")

        def worker():
            total = len(selected)
            for i, (name, wid) in enumerate(selected):
                self.after(0, lambda n=name, idx=i: self._update_prog(idx, total, f"正在安装 {n}..."))
                try:
                    r = run_cmd(
                        f"winget install --id {wid} --accept-package-agreements "
                        f"--accept-source-agreements --silent", timeout=300,
                    )
                    ok = any(w in r for w in ("成功", "Successfully", "已安装"))
                    self.after(0, lambda n=name, s=ok: self._update_prog_done(n, s))
                except Exception:
                    self.after(0, lambda n=name: self._update_prog_done(n, False))
            self.after(0, lambda: self._install_complete(total))
        threading.Thread(target=worker, daemon=True).start()

    def _update_prog(self, cur, total, text):
        self.prog_bar.set(cur / total)
        self.prog_label.configure(text=text, text_color=COLORS["text"])

    def _update_prog_done(self, name, ok):
        self.prog_label.configure(
            text=f"✓ {name} 安装成功" if ok else f"✗ {name} 安装失败",
            text_color=COLORS["success"] if ok else COLORS["error"],
        )

    def _install_complete(self, total):
        self.prog_bar.set(1.0)
        self.prog_label.configure(text=f"安装完成！共处理 {total} 个软件", text_color=COLORS["success"])
        self.install_btn.configure(state="normal", text="🚀 开始安装")
        messagebox.showinfo("完成", f"已处理 {total} 个软件的安装。\n部分软件可能需要重启才能使用。")
        SoftwareDetector.invalidate()
        self._load_install_page(force=True)


if __name__ == "__main__":
    app = SetupAssistant()
    app.mainloop()
