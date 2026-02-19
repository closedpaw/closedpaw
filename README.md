# ClosedPaw

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![English](https://img.shields.io/badge/lang-English-blue.svg)](README.md)
[![Русский](https://img.shields.io/badge/lang-Русский-red.svg)](README.ru.md)
[![中文](https://img.shields.io/badge/lang-中文-yellow.svg)](README.zh.md)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-000000.svg?logo=next.js&logoColor=white)](https://nextjs.org/)

> **Zero-Trust AI Assistant** - Secure, local-first AI with hardened sandboxing

ClosedPaw is a privacy-focused AI assistant that runs entirely on your local machine. Unlike cloud-based solutions, your data never leaves your device. Built with security-first architecture using gVisor/Kata Containers for true isolation.

## 🚀 Quick Start

### Recommended Platform

**Linux or macOS is strongly recommended** for the best security experience:

- ✅ **Full gVisor/Kata sandboxing** - True kernel-level isolation
- ✅ **Native container security** - No virtualization overhead
- ✅ **Better AI model performance** - Direct GPU access
- ⚠️ **Windows limitations** - Limited to Docker Desktop or WSL2; full sandboxing unavailable on Windows Home

### npm Installation (Cross-platform)

```bash
npm install -g closedpaw
```

### One-Command Installation (Alternative)

**Linux / macOS (Recommended):**
```bash
curl -sSL https://raw.githubusercontent.com/logansin/closedpaw/main/installer/install.sh | bash
```

**Windows (PowerShell):**
```powershell
iwr -useb https://raw.githubusercontent.com/logansin/closedpaw/main/installer/install.ps1 | iex
```

### Manual Installation

```bash
# Clone repository
git clone https://github.com/logansin/closedpaw.git
cd closedpaw

# Install backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install frontend
cd ../frontend
npm install

# Start services
npm run dev  # Starts both backend and frontend
```

## 🔒 Security Features

- **Zero-Trust Architecture** - No implicit trust, all actions verified
- **Hardened Sandboxing** - gVisor/Kata Containers (not just Docker)
- **Prompt Injection Defense** - Protection against CVE-2026-25253 type attacks
- **Local-Only Operation** - Ollama on 127.0.0.1, Web UI on localhost
- **Human-in-the-Loop** - Critical actions require approval
- **Audit Logging** - All actions logged for forensic analysis
- **Encrypted Storage** - API keys encrypted at rest

## 🛡️ Security Reality Check

> **No system is 100% secure.** We don't claim perfection — we claim *maximum feasible protection*.

### What We Protect Against

| Threat | Protection Level | Notes |
|--------|-----------------|-------|
| Prompt Injection | ✅ High | Multiple defense layers, input sanitization |
| Code Execution | ✅ High | gVisor sandbox, seccomp filters |
| Data Exfiltration | ✅ High | Local-only, encrypted storage |
| Network Attacks | ✅ High | 127.0.0.1 binding, no external exposure |
| Supply Chain | ⚠️ Medium | Signed packages, dependency scanning |
| Physical Access | ❌ Low | OS-level encryption recommended |

### Defense in Depth

ClosedPaw implements **defense in depth** — multiple overlapping security layers:

```
┌─────────────────────────────────────────┐
│  Layer 1: Input Validation              │
│  Layer 2: Prompt Injection Filters      │
│  Layer 3: Sandboxed Execution (gVisor)  │
│  Layer 4: Human-in-the-Loop             │
│  Layer 5: Audit Logging                 │
│  Layer 6: Encrypted Storage             │
└─────────────────────────────────────────┘
```

**If one layer fails, others protect you.**

### Why Size Matters

> **112 MB** — this is the weight of protection.

```
Package Size Breakdown:
├── 🛡️ gVisor/Kata Runtime     ~15 MB
├── 🔐 Cryptography Stack      ~25 MB  (PyNaCl, Cryptography)
├── 🤖 AI Safety Layers        ~20 MB  (prompt filters, validators)
├── 📡 Communication Channels  ~15 MB  (Telegram, Discord, Slack)
├── 🎨 Next.js Web UI          ~37 MB
└── Total: Protection you can trust
```

**Smaller size = fewer defenses.** We don't apologize for protecting you properly.

### Comparison

| Product | Size | Sandboxing | HITL | Encryption |
|---------|------|------------|------|------------|
| "Lightweight" AI tools | 5-10 MB | ❌ None | ❌ No | ❌ No |
| OpenClaw | ~50 MB | ⚠️ Docker only | ❌ No | ⚠️ Partial |
| **ClosedPaw** | **112 MB** | **✅ gVisor/Kata** | **✅ Yes** | **✅ Full** |
- **Human-in-the-Loop** - Critical actions require approval
- **Audit Logging** - All actions logged for forensic analysis
- **Encrypted Storage** - API keys encrypted at rest

## 🏗️ Architecture

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

## 🛠️ Technology Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic AI
- **Frontend:** Next.js 15, React 19, Tailwind CSS
- **LLM:** Ollama (local), OpenAI/Anthropic (optional cloud)
- **Sandboxing:** gVisor, Kata Containers
- **Security:** Cryptography, PyNaCl, Seccomp

## 📋 Requirements

- Python 3.11+
- Node.js 20+
- Ollama
- gVisor or Kata Containers (for sandboxing)

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with lessons learned from OpenClaw security analysis
- Inspired by the need for truly secure AI assistants
- Community-driven open source project

## ⚠️ Security Notice

This project prioritizes security over convenience. Some features may require additional setup (like gVisor/Kata installation) to ensure proper isolation. Never disable security features for convenience.

---

**Made with 🔒 by the ClosedPaw Team**