"""
SecureSphere AI - Agent Manager
Manages AI agents in hardened sandboxed environments
Uses gVisor or Kata Containers for kernel-level isolation
"""

import asyncio
import json
import logging
import subprocess
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import os

logger = logging.getLogger(__name__)


class SandboxType(str, Enum):
    """Type of sandbox to use for isolation"""
    GVISOR = "gvisor"
    KATA = "kata"
    # Docker is intentionally NOT included - insufficient isolation


class AgentStatus(str, Enum):
    """Status of an agent"""
    PENDING = "pending"
    CREATING = "creating"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class ResourceLimits:
    """Resource limits for sandboxed agent"""
    cpu_cores: float = 1.0
    memory_mb: int = 512
    disk_mb: int = 1024
    network_enabled: bool = False
    max_processes: int = 50


@dataclass
class AgentInstance:
    """Represents a sandboxed agent instance"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    skill_id: str = ""
    sandbox_type: SandboxType = SandboxType.GVISOR
    status: AgentStatus = AgentStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    container_id: Optional[str] = None
    resource_limits: ResourceLimits = field(default_factory=ResourceLimits)
    exit_code: Optional[int] = None
    error_message: Optional[str] = None


class AgentManager:
    """
    Agent Manager for SecureSphere AI
    
    Manages Skill Executors in hardened sandboxed environments.
    Uses gVisor or Kata Containers for true kernel-level isolation.
    Docker alone is NOT used due to escape risks.
    
    Security features:
    - gVisor/Kata Containers sandboxing
    - Resource limits (CPU, memory, disk)
    - Network isolation
    - Process isolation
    - Audit logging
    """
    
    def __init__(self):
        self.agents: Dict[str, AgentInstance] = {}
        self.sandbox_type: SandboxType = self._detect_sandbox_runtime()
        self.available = self._check_sandbox_availability()
        
        # Security configuration
        self.security_config = {
            "default_cpu_limit": 1.0,
            "default_memory_limit_mb": 512,
            "default_disk_limit_mb": 1024,
            "max_agents": 10,
            "agent_timeout_seconds": 300,
            "kill_on_escape_attempt": True
        }
        
        logger.info(f"AgentManager initialized with sandbox: {self.sandbox_type.value}")
        logger.info(f"Sandbox availability: {self.available}")
    
    def _detect_sandbox_runtime(self) -> SandboxType:
        """Detect which sandbox runtime is available"""
        # Check for gVisor first (preferred)
        if self._check_gvisor():
            logger.info("gVisor runtime detected")
            return SandboxType.GVISOR
        
        # Check for Kata Containers
        if self._check_kata():
            logger.info("Kata Containers runtime detected")
            return SandboxType.KATA
        
        # Default to gVisor even if not available (will fail gracefully)
        logger.warning("No sandbox runtime detected. gVisor will be required.")
        return SandboxType.GVISOR
    
    def _check_gvisor(self) -> bool:
        """Check if gVisor (runsc) is installed"""
        try:
            result = subprocess.run(
                ["runsc", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_kata(self) -> bool:
        """Check if Kata Containers is installed"""
        try:
            result = subprocess.run(
                ["kata-runtime", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def _check_sandbox_availability(self) -> bool:
        """Check if sandbox can be used"""
        if self.sandbox_type == SandboxType.GVISOR:
            return self._check_gvisor()
        elif self.sandbox_type == SandboxType.KATA:
            return self._check_kata()
        return False
    
    async def create_agent(self, skill_id: str, 
                          resource_limits: Optional[ResourceLimits] = None) -> AgentInstance:
        """
        Create a new sandboxed agent
        
        Args:
            skill_id: ID of the skill to run
            resource_limits: Resource limits for the agent
            
        Returns:
            AgentInstance
        """
        if not self.available:
            raise RuntimeError("Sandbox runtime not available. Please install gVisor or Kata Containers.")
        
        # Check agent limit
        if len(self.agents) >= self.security_config["max_agents"]:
            raise RuntimeError(f"Maximum number of agents ({self.security_config['max_agents']}) reached")
        
        # Create agent instance
        agent = AgentInstance(
            skill_id=skill_id,
            sandbox_type=self.sandbox_type,
            resource_limits=resource_limits or ResourceLimits()
        )
        
        self.agents[agent.id] = agent
        
        logger.info(f"Creating agent {agent.id} for skill {skill_id}")
        
        # Create sandbox container
        try:
            agent.status = AgentStatus.CREATING
            await self._create_sandbox(agent)
            agent.status = AgentStatus.RUNNING
            agent.started_at = datetime.utcnow()
            logger.info(f"Agent {agent.id} created and running")
        except Exception as e:
            agent.status = AgentStatus.ERROR
            agent.error_message = str(e)
            logger.error(f"Failed to create agent {agent.id}: {e}")
            raise
        
        return agent
    
    async def _create_sandbox(self, agent: AgentInstance):
        """Create sandboxed container for agent"""
        if agent.sandbox_type == SandboxType.GVISOR:
            await self._create_gvisor_sandbox(agent)
        elif agent.sandbox_type == SandboxType.KATA:
            await self._create_kata_sandbox(agent)
        else:
            raise RuntimeError(f"Unsupported sandbox type: {agent.sandbox_type}")
    
    async def _create_gvisor_sandbox(self, agent: AgentInstance):
        """Create gVisor sandbox container"""
        container_name = f"securesphere-agent-{agent.id}"
        
        # Prepare sandbox directory
        sandbox_dir = f"/tmp/securesphere-sandboxes/{agent.id}"
        os.makedirs(sandbox_dir, exist_ok=True)
        
        # Create OCI bundle for gVisor
        bundle_dir = f"{sandbox_dir}/bundle"
        rootfs_dir = f"{bundle_dir}/rootfs"
        os.makedirs(rootfs_dir, exist_ok=True)
        
        # Create minimal rootfs (would use container image in production)
        await self._prepare_rootfs(rootfs_dir, agent.skill_id)
        
        # Create config.json for OCI runtime
        config = self._create_oci_config(agent)
        with open(f"{bundle_dir}/config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        # Create container with gVisor
        cmd = [
            "runsc",
            "--root=/var/run/runsc",
            "--debug-log=/tmp/runsc.log",
            "--debug",
            "--strace",
            "--log-packets",
            "create",
            "--bundle", bundle_dir,
            container_name
        ]
        
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await result.communicate()
        
        if result.returncode != 0:
            raise RuntimeError(f"gVisor container creation failed: {stderr.decode()}")
        
        agent.container_id = container_name
        
        # Start the container
        start_result = await asyncio.create_subprocess_exec(
            "runsc", "--root=/var/run/runsc", "start", container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await start_result.communicate()
        
        if start_result.returncode != 0:
            raise RuntimeError("gVisor container start failed")
    
    async def _create_kata_sandbox(self, agent: AgentInstance):
        """Create Kata Containers sandbox"""
        container_name = f"securesphere-agent-{agent.id}"
        
        # Create container with Kata runtime
        cmd = [
            "docker",  # Kata uses Docker/Podman as frontend
            "run",
            "-d",  # Detached
            "--runtime", "kata-runtime",
            "--name", container_name,
            "--cpus", str(agent.resource_limits.cpu_cores),
            "--memory", f"{agent.resource_limits.memory_mb}m",
            "--network", "none",  # No network access
            "--read-only",  # Read-only rootfs
            "--tmpfs", "/tmp:noexec,nosuid,size=100m",
            "securesphere-skill:latest",  # Skill container image
            "python", "-m", f"skills.{agent.skill_id}"
        ]
        
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await result.communicate()
        
        if result.returncode != 0:
            raise RuntimeError(f"Kata container creation failed: {stderr.decode()}")
        
        agent.container_id = container_name
    
    async def _prepare_rootfs(self, rootfs_dir: str, skill_id: str):
        """Prepare minimal rootfs for sandbox"""
        # In production, this would extract from a container image
        # For now, create minimal structure
        dirs = ["bin", "lib", "lib64", "usr", "tmp", "home", "etc"]
        for d in dirs:
            os.makedirs(f"{rootfs_dir}/{d}", exist_ok=True)
        
        # Copy skill code
        skill_src = f"/app/skills/{skill_id}"
        if os.path.exists(skill_src):
            import shutil
            shutil.copytree(skill_src, f"{rootfs_dir}/app/skill", dirs_exist_ok=True)
    
    def _create_oci_config(self, agent: AgentInstance) -> dict:
        """Create OCI runtime configuration"""
        return {
            "ociVersion": "1.0.0",
            "process": {
                "terminal": False,
                "user": {"uid": 65534, "gid": 65534},  # nobody user
                "args": ["python", "-m", f"skills.{agent.skill_id}"],
                "env": [
                    "PATH=/usr/local/bin:/usr/bin:/bin",
                    "HOME=/home",
                    "PYTHONUNBUFFERED=1"
                ],
                "cwd": "/app",
                "capabilities": {
                    "bounding": [],
                    "effective": [],
                    "inheritable": [],
                    "permitted": []
                },
                "rlimits": [
                    {"type": "RLIMIT_NOFILE", "hard": 64, "soft": 64},
                    {"type": "RLIMIT_NPROC", "hard": agent.resource_limits.max_processes, "soft": agent.resource_limits.max_processes}
                ],
                "noNewPrivileges": True
            },
            "root": {
                "path": "rootfs",
                "readonly": True
            },
            "hostname": f"agent-{agent.id[:8]}",
            "mounts": [
                {
                    "destination": "/proc",
                    "type": "proc",
                    "source": "proc"
                },
                {
                    "destination": "/tmp",
                    "type": "tmpfs",
                    "source": "tmpfs",
                    "options": ["nosuid", "strictatime", "mode=755", "size=100m"]
                }
            ],
            "linux": {
                "resources": {
                    "cpu": {
                        "shares": int(agent.resource_limits.cpu_cores * 1024),
                        "quota": int(agent.resource_limits.cpu_cores * 100000),
                        "period": 100000
                    },
                    "memory": {
                        "limit": agent.resource_limits.memory_mb * 1024 * 1024,
                        "swap": agent.resource_limits.memory_mb * 1024 * 1024
                    },
                    "blockIO": {
                        "weight": 100
                    }
                },
                "namespaces": [
                    {"type": "pid"},
                    {"type": "network"},
                    {"type": "ipc"},
                    {"type": "uts"},
                    {"type": "mount"},
                    {"type": "user"}
                ],
                "maskedPaths": [
                    "/proc/kcore",
                    "/proc/latency_stats",
                    "/proc/timer_list",
                    "/proc/timer_stats",
                    "/proc/sched_debug",
                    "/sys/firmware"
                ],
                "readonlyPaths": [
                    "/proc/asound",
                    "/proc/bus",
                    "/proc/fs",
                    "/proc/irq",
                    "/proc/sys",
                    "/proc/sysrq-trigger"
                ],
                "seccomp": {
                    "defaultAction": "SCMP_ACT_ERRNO",
                    "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_X86", "SCMP_ARCH_AARCH64"],
                    "syscalls": [
                        {
                            "names": [
                                "accept", "accept4", "access", "adjtimex", "alarm", "bind",
                                "brk", "capget", "capset", "chdir", "chmod", "chown", "chown32",
                                "clock_adjtime", "clock_getres", "clock_gettime", "clock_nanosleep",
                                "close", "connect", "copy_file_range", "creat", "dup", "dup2",
                                "dup3", "epoll_create", "epoll_create1", "epoll_ctl", "epoll_ctl_old",
                                "epoll_pwait", "epoll_wait", "epoll_wait_old", "eventfd", "eventfd2",
                                "execve", "execveat", "exit", "exit_group", "faccessat",
                                "fadvise64", "fadvise64_64", "fallocate", "fanotify_mark",
                                "fchdir", "fchmod", "fchmodat", "fchown", "fchown32", "fchownat",
                                "fcntl", "fcntl64", "fdatasync", "fgetxattr", "flistxattr",
                                "flock", "fork", "fremovexattr", "fsetxattr", "fstat", "fstat64",
                                "fstatat64", "fstatfs", "fstatfs64", "fsync", "ftruncate",
                                "ftruncate64", "futex", "getcpu", "getcwd", "getdents",
                                "getdents64", "getegid", "getegid32", "geteuid", "geteuid32",
                                "getgid", "getgid32", "getgroups", "getgroups32", "getitimer",
                                "getpeername", "getpgid", "getpgrp", "getpid", "getppid",
                                "getpriority", "getrandom", "getresgid", "getresgid32",
                                "getresuid", "getresuid32", "getrlimit", "get_robust_list",
                                "getrusage", "getsid", "getsockname", "getsockopt", "get_thread_area",
                                "gettid", "gettimeofday", "getuid", "getuid32", "getxattr",
                                "inotify_add_watch", "inotify_init", "inotify_init1",
                                "inotify_rm_watch", "io_cancel", "ioctl", "io_destroy",
                                "io_getevents", "io_pgetevents", "ioprio_get", "ioprio_set",
                                "io_setup", "io_submit", "io_uring_enter", "io_uring_register",
                                "io_uring_setup", "kill", "lchown", "lchown32", "lgetxattr",
                                "link", "linkat", "listen", "listxattr", "llistxattr",
                                "lremovexattr", "lseek", "lsetxattr", "lstat", "lstat64",
                                "madvise", "memfd_create", "mincore", "mkdir", "mkdirat",
                                "mknod", "mknodat", "mlock", "mlock2", "mlockall", "mmap",
                                "mmap2", "mprotect", "mq_getsetattr", "mq_notify", "mq_open",
                                "mq_timedreceive", "mq_timedsend", "mq_unlink", "mremap",
                                "msgctl", "msgget", "msgrcv", "msgsnd", "msync", "munlock",
                                "munlockall", "munmap", "nanosleep", "newfstatat", "open",
                                "openat", "pause", "pipe", "pipe2", "poll", "ppoll",
                                "ppoll_time64", "prctl", "pread64", "preadv", "preadv2",
                                "prlimit64", "pselect6", "pselect6_time64", "pwrite64",
                                "pwritev", "pwritev2", "read", "readahead", "readdir",
                                "readlink", "readlinkat", "readv", "recv", "recvfrom",
                                "recvmmsg", "recvmsg", "remap_file_pages", "removexattr",
                                "rename", "renameat", "renameat2", "restart_syscall",
                                "rmdir", "rseq", "rt_sigaction", "rt_sigpending",
                                "rt_sigprocmask", "rt_sigqueueinfo", "rt_sigreturn",
                                "rt_sigsuspend", "rt_sigtimedwait", "rt_tgsigqueueinfo",
                                "sched_getaffinity", "sched_getattr", "sched_getparam",
                                "sched_get_priority_max", "sched_get_priority_min",
                                "sched_getscheduler", "sched_rr_get_interval", "sched_setaffinity",
                                "sched_setattr", "sched_setparam", "sched_setscheduler",
                                "sched_yield", "seccomp", "select", "semctl", "semget",
                                "semop", "semtimedop", "send", "sendfile", "sendfile64",
                                "sendmmsg", "sendmsg", "sendto", "setfsgid", "setfsgid32",
                                "setfsuid", "setfsuid32", "setgid", "setgid32", "setgroups",
                                "setgroups32", "setitimer", "setpgid", "setpriority",
                                "setregid", "setregid32", "setresgid", "setresgid32",
                                "setresuid", "setresuid32", "setreuid", "setreuid32",
                                "setrlimit", "set_robust_list", "setsid", "setsockopt",
                                "set_thread_area", "set_tid_address", "setuid", "setuid32",
                                "setxattr", "shmat", "shmctl", "shmdt", "shmget", "shutdown",
                                "sigaltstack", "signalfd", "signalfd4", "sigpending",
                                "sigprocmask", "sigreturn", "socket", "socketcall",
                                "socketpair", "splice", "stat", "stat64", "statfs",
                                "statfs64", "statx", "symlink", "symlinkat", "sync",
                                "sync_file_range", "syncfs", "sysinfo", "tee", "tgkill",
                                "time", "timer_create", "timer_delete", "timer_getoverrun",
                                "timer_gettime", "timer_settime", "timerfd_create",
                                "timerfd_gettime", "timerfd_settime", "times", "tkill",
                                "truncate", "truncate64", "ugetrlimit", "umask", "uname",
                                "unlink", "unlinkat", "utime", "utimensat", "utimensat_time64",
                                "utimes", "vfork", "wait4", "waitid", "waitpid", "write",
                                "writev"
                            ],
                            "action": "SCMP_ACT_ALLOW"
                        }
                    ]
                }
            }
        }
    
    async def execute_in_agent(self, agent_id: str, command: str, 
                              timeout: int = 30) -> Dict[str, Any]:
        """
        Execute a command in a running agent
        
        Args:
            agent_id: ID of the agent
            command: Command to execute
            timeout: Timeout in seconds
            
        Returns:
            Execution result
        """
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        if agent.status != AgentStatus.RUNNING:
            raise RuntimeError(f"Agent {agent_id} is not running (status: {agent.status.value})")
        
        logger.info(f"Executing command in agent {agent_id}: {command}")
        
        try:
            if agent.sandbox_type == SandboxType.GVISOR:
                # Execute via gVisor
                exec_result = await asyncio.wait_for(
                    self._exec_gvisor(agent, command),
                    timeout=timeout
                )
            elif agent.sandbox_type == SandboxType.KATA:
                # Execute via Kata
                exec_result = await asyncio.wait_for(
                    self._exec_kata(agent, command),
                    timeout=timeout
                )
            else:
                raise RuntimeError(f"Unsupported sandbox type: {agent.sandbox_type}")
            
            return {
                "success": True,
                "stdout": exec_result.get("stdout", ""),
                "stderr": exec_result.get("stderr", ""),
                "exit_code": exec_result.get("exit_code", 0)
            }
            
        except asyncio.TimeoutError:
            logger.warning(f"Command timeout in agent {agent_id}")
            return {
                "success": False,
                "error": "Execution timeout",
                "stdout": "",
                "stderr": "",
                "exit_code": -1
            }
        except Exception as e:
            logger.error(f"Command execution failed in agent {agent_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "exit_code": -1
            }
    
    async def _exec_gvisor(self, agent: AgentInstance, command: str) -> Dict:
        """Execute command in gVisor container"""
        cmd = [
            "runsc",
            "--root=/var/run/runsc",
            "exec",
            agent.container_id,
            "sh", "-c", command
        ]
        
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await result.communicate()
        
        return {
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "exit_code": result.returncode
        }
    
    async def _exec_kata(self, agent: AgentInstance, command: str) -> Dict:
        """Execute command in Kata container"""
        cmd = [
            "docker",
            "exec",
            agent.container_id,
            "sh", "-c", command
        ]
        
        result = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await result.communicate()
        
        return {
            "stdout": stdout.decode(),
            "stderr": stderr.decode(),
            "exit_code": result.returncode
        }
    
    async def stop_agent(self, agent_id: str, force: bool = False) -> bool:
        """
        Stop a running agent
        
        Args:
            agent_id: ID of the agent
            force: Force kill if True
            
        Returns:
            True if stopped successfully
        """
        agent = self.agents.get(agent_id)
        if not agent:
            logger.warning(f"Agent {agent_id} not found for stopping")
            return False
        
        if agent.status not in [AgentStatus.RUNNING, AgentStatus.ERROR]:
            logger.info(f"Agent {agent_id} is not running (status: {agent.status.value})")
            return True
        
        logger.info(f"Stopping agent {agent_id} (force={force})")
        
        agent.status = AgentStatus.STOPPING
        
        try:
            if agent.sandbox_type == SandboxType.GVISOR:
                await self._stop_gvisor(agent, force)
            elif agent.sandbox_type == SandboxType.KATA:
                await self._stop_kata(agent, force)
            
            agent.status = AgentStatus.STOPPED
            agent.stopped_at = datetime.utcnow()
            
            logger.info(f"Agent {agent_id} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop agent {agent_id}: {e}")
            agent.status = AgentStatus.ERROR
            agent.error_message = str(e)
            return False
    
    async def _stop_gvisor(self, agent: AgentInstance, force: bool):
        """Stop gVisor container"""
        signal = "KILL" if force else "TERM"
        
        # Send signal
        cmd = ["runsc", "--root=/var/run/runsc", "kill", signal, agent.container_id]
        result = await asyncio.create_subprocess_exec(*cmd)
        await result.communicate()
        
        # Wait a bit for graceful shutdown
        if not force:
            await asyncio.sleep(2)
        
        # Delete container
        cmd = ["runsc", "--root=/var/run/runsc", "delete", agent.container_id]
        result = await asyncio.create_subprocess_exec(*cmd)
        await result.communicate()
    
    async def _stop_kata(self, agent: AgentInstance, force: bool):
        """Stop Kata container"""
        signal = "SIGKILL" if force else "SIGTERM"
        
        # Stop container
        cmd = ["docker", "stop", f"--signal={signal}", "-t", "5", agent.container_id]
        result = await asyncio.create_subprocess_exec(*cmd)
        await result.communicate()
        
        # Remove container
        cmd = ["docker", "rm", agent.container_id]
        result = await asyncio.create_subprocess_exec(*cmd)
        await result.communicate()
    
    async def cleanup(self):
        """Stop all agents and cleanup resources"""
        logger.info("Cleaning up all agents...")
        
        for agent_id in list(self.agents.keys()):
            await self.stop_agent(agent_id, force=True)
        
        self.agents.clear()
        logger.info("Agent cleanup complete")
    
    def get_agent_status(self, agent_id: str) -> Optional[AgentInstance]:
        """Get status of an agent"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[AgentInstance]:
        """List all agents"""
        return list(self.agents.values())
    
    def get_sandbox_info(self) -> Dict[str, Any]:
        """Get information about sandbox capabilities"""
        return {
            "sandbox_type": self.sandbox_type.value,
            "available": self.available,
            "gvisor_installed": self._check_gvisor(),
            "kata_installed": self._check_kata(),
            "max_agents": self.security_config["max_agents"],
            "current_agents": len(self.agents),
            "agents": [
                {
                    "id": a.id,
                    "skill_id": a.skill_id,
                    "status": a.status.value,
                    "sandbox_type": a.sandbox_type.value
                }
                for a in self.agents.values()
            ]
        }


# Singleton instance
_agent_manager: Optional[AgentManager] = None


def get_agent_manager() -> AgentManager:
    """Get or create the singleton AgentManager instance"""
    global _agent_manager
    if _agent_manager is None:
        _agent_manager = AgentManager()
    return _agent_manager