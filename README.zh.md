# ClosedPaw

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000.svg?logo=next.js&logoColor=white)](https://nextjs.org/)

> **零信任 AI 助手** — 具有强化隔离功能的安全本地 AI

ClosedPaw 是一款注重隐私的 AI 助手，完全在您的本地计算机上运行。与云解决方案不同，您的数据永远不会离开您的设备。采用安全优先架构构建，使用 gVisor/Kata Containers 实现真正的隔离。

## 🚀 快速开始

### 推荐平台

**强烈建议使用 Linux 或 macOS** 以获得最佳安全体验：

- ✅ **完整的 gVisor/Kata 沙箱** — 真正的内核级隔离
- ✅ **原生容器安全** — 无虚拟化开销
- ✅ **更好的 AI 模型性能** — 直接 GPU 访问
- ⚠️ **Windows 限制** — 仅限 Docker Desktop 或 WSL2；Windows Home 无法使用完整沙箱

### npm 安装（跨平台）

```bash
npm install -g closedpaw
```

### 一键安装（备选）

**Linux / macOS（推荐）：**
```bash
curl -sSL https://raw.githubusercontent.com/logansin/closedpaw/main/installer/install.sh | bash
```

**Windows (PowerShell)：**
```powershell
iwr -useb https://raw.githubusercontent.com/logansin/closedpaw/main/installer/install.ps1 | iex
```

### 手动安装

```bash
# 克隆仓库
git clone https://github.com/logansin/closedpaw.git
cd closedpaw

# 安装后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 安装前端
cd ../frontend
npm install

# 启动服务
npm run dev  # 同时启动后端和前端
```

## 🔒 安全功能

- **零信任架构** — 没有隐式信任，所有操作都经过验证
- **强化沙箱** — gVisor/Kata Containers（不仅仅是 Docker）
- **提示注入防护** — 防御 CVE-2026-25253 类型的攻击
- **纯本地运行** — Ollama 绑定到 127.0.0.1，Web UI 在 localhost
- **人工介入 (HITL)** — 关键操作需要用户确认
- **审计日志** — 所有操作都记录用于取证分析
- **加密存储** — API 密钥在静态时加密

## 🛡️ 安全现实检查

> **没有系统是 100% 安全的。** 我们不声称完美 — 我们声称*最大可行的保护*。

### 我们防护什么

| 威胁 | 防护级别 | 说明 |
|------|---------|------|
| 提示注入 | ✅ 高 | 多层防护，输入净化 |
| 代码执行 | ✅ 高 | gVisor 沙箱，seccomp 过滤器 |
| 数据泄露 | ✅ 高 | 纯本地，加密存储 |
| 网络攻击 | ✅ 高 | 绑定到 127.0.0.1，无外部暴露 |
| 供应链 | ⚠️ 中 | 签名包，依赖扫描 |
| 物理访问 | ❌ 低 | 建议使用操作系统级加密 |

### 纵深防御

ClosedPaw 实现**纵深防御** — 多个重叠的安全层：

```
┌─────────────────────────────────────────┐
│  第 1 层：输入验证                       │
│  第 2 层：提示注入过滤器                  │
│  第 3 层：沙箱执行 (gVisor)              │
│  第 4 层：人工介入 (HITL)                │
│  第 5 层：审计日志                       │
│  第 6 层：加密存储                       │
└─────────────────────────────────────────┘
```

**如果一层失败，其他层会保护您。**

### 为什么大小很重要

> **112 MB** — 这是保护的重量。

```
包大小分解：
├── 🛡️ gVisor/Kata 运行时    ~15 MB
├── 🔐 加密技术栈            ~25 MB  (PyNaCl, Cryptography)
├── 🤖 AI 安全层             ~20 MB  (过滤器，验证器)
├── 📡 通信通道              ~15 MB  (Telegram, Discord, Slack)
├── 🎨 Next.js Web UI        ~37 MB
└── 总计：您可以信赖的保护
```

**更小的大小 = 更少的保护。** 我们不会为正确保护您而道歉。

### 对比

| 产品 | 大小 | 沙箱 | HITL | 加密 |
|------|------|------|------|------|
| "轻量级" AI 工具 | 5-10 MB | ❌ 无 | ❌ 无 | ❌ 无 |
| OpenClaw | ~50 MB | ⚠️ 仅 Docker | ❌ 无 | ⚠️ 部分 |
| **ClosedPaw** | **112 MB** | **✅ gVisor/Kata** | **✅ 有** | **✅ 完整** |

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│              ClosedPaw - Zero Trust                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Core      │  │   Agent     │  │   Human-in-the  │ │
│  │ Orchestrator│  │   Manager   │  │   Loop (HITL)   │ │
│  │  (FastAPI)  │  │ (gVisor/    │  │   Interface     │ │
│  │             │  │   Kata)     │  │                 │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
│           │              │                    │         │
│           ▼              ▼                    ▼         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   Local     │  │   Cloud     │  │   Data Vault    │ │
│  │   LLM       │  │   LLM       │  │  (Encrypted)    │ │
│  │  Gateway    │  │   Proxy     │  │                 │ │
│  │  (Ollama)   │  │             │  │                 │ │
│  └─────────────┘  └─────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 🛠️ 技术栈

- **后端:** Python 3.11+, FastAPI, Pydantic AI
- **前端:** Next.js 15, React 19, Tailwind CSS
- **LLM:** Ollama (本地), OpenAI/Anthropic (可选云)
- **沙箱:** gVisor, Kata Containers
- **安全:** Cryptography, PyNaCl, Seccomp

## 📋 系统要求

- Python 3.11+
- Node.js 20+
- Ollama
- gVisor 或 Kata Containers (用于沙箱)

## 🤝 贡献

我们欢迎贡献！请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解指南。

## 📄 许可证

本项目采用 MIT 许可证 — 请参阅 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- 基于 OpenClaw 安全分析的教训构建
- 受到对真正安全的 AI 助手的需求启发
- 社区驱动的开源项目

## ⚠️ 安全声明

本项目将安全置于便利之上。某些功能可能需要额外配置（例如安装 gVisor/Kata）以确保适当的隔离。切勿为了便利而禁用安全功能。

---

**用 🔒 由 ClosedPaw 团队制作**