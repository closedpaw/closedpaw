"""
SecureSphere AI - File System Skill Executor
Operates in sandboxed environment with minimal privileges
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class FileOperation(str, Enum):
    """Allowed file operations"""
    READ = "read"
    LIST = "list"
    WRITE = "write"
    DELETE = "delete"
    CREATE_DIR = "create_dir"


@dataclass
class OperationResult:
    """Result of a file operation"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    path: Optional[str] = None


class FileSystemSkill:
    """
    File System Skill Executor
    
    Security features:
    - Sandbox directory restriction
    - Path traversal prevention
    - Operation whitelist
    - Size limits
    - Audit logging
    """
    
    def __init__(self, sandbox_dir: Optional[str] = None):
        """
        Initialize File System Skill
        
        Args:
            sandbox_dir: Directory to restrict operations to.
                        If None, uses a default secure directory.
        """
        if sandbox_dir:
            self.sandbox_dir = Path(sandbox_dir).resolve()
        else:
            # Default sandbox in user's home
            self.sandbox_dir = Path.home() / ".securesphere-ai" / "sandbox" / "filesystem"
        
        # Create sandbox directory if it doesn't exist
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        
        # Security limits
        self.max_file_size = 10 * 1024 * 1024  # 10 MB
        self.max_read_size = 1024 * 1024  # 1 MB
        self.allowed_extensions = [
            ".txt", ".md", ".json", ".yaml", ".yml", ".csv",
            ".py", ".js", ".html", ".css", ".xml"
        ]
        
        # Audit log
        self.audit_log: List[Dict] = []
        
        logger.info(f"FileSystemSkill initialized with sandbox: {self.sandbox_dir}")
    
    def _validate_path(self, path: str) -> Optional[Path]:
        """
        Validate and resolve path within sandbox
        
        Args:
            path: Relative or absolute path
            
        Returns:
            Resolved Path object or None if invalid
        """
        try:
            # Resolve the path
            if os.path.isabs(path):
                # If absolute, check if it's within sandbox
                resolved = Path(path).resolve()
            else:
                # If relative, resolve against sandbox
                resolved = (self.sandbox_dir / path).resolve()
            
            # Security check: ensure path is within sandbox
            try:
                resolved.relative_to(self.sandbox_dir)
            except ValueError:
                logger.warning(f"Path traversal attempt blocked: {path}")
                self._log_audit("validate_path", path, False, "Path traversal attempt")
                return None
            
            return resolved
            
        except Exception as e:
            logger.error(f"Path validation error: {e}")
            return None
    
    def _check_extension(self, path: Path) -> bool:
        """Check if file extension is allowed"""
        ext = path.suffix.lower()
        return ext in self.allowed_extensions or not ext
    
    def _log_audit(self, operation: str, path: str, success: bool, details: str = ""):
        """Log operation to audit trail"""
        from datetime import datetime
        
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "path": str(path),
            "success": success,
            "details": details
        }
        
        self.audit_log.append(entry)
        
        # Also log to system logger
        status = "SUCCESS" if success else "FAILED"
        logger.info(f"FILESYSTEM [{status}] {operation}: {path} - {details}")
    
    def read_file(self, file_path: str) -> OperationResult:
        """
        Read contents of a file
        
        Args:
            file_path: Path to file (relative to sandbox)
            
        Returns:
            OperationResult with file contents
        """
        # Validate path
        resolved_path = self._validate_path(file_path)
        if not resolved_path:
            return OperationResult(
                success=False,
                error="Invalid path or path traversal attempt detected",
                path=file_path
            )
        
        # Check if file exists
        if not resolved_path.exists():
            self._log_audit("read", file_path, False, "File not found")
            return OperationResult(
                success=False,
                error=f"File not found: {file_path}",
                path=file_path
            )
        
        # Check if it's a file
        if not resolved_path.is_file():
            self._log_audit("read", file_path, False, "Not a file")
            return OperationResult(
                success=False,
                error=f"Not a file: {file_path}",
                path=file_path
            )
        
        # Check extension
        if not self._check_extension(resolved_path):
            self._log_audit("read", file_path, False, "File type not allowed")
            return OperationResult(
                success=False,
                error=f"File type not allowed: {resolved_path.suffix}",
                path=file_path
            )
        
        # Check file size
        file_size = resolved_path.stat().st_size
        if file_size > self.max_read_size:
            self._log_audit("read", file_path, False, f"File too large: {file_size} bytes")
            return OperationResult(
                success=False,
                error=f"File too large: {file_size} bytes (max: {self.max_read_size})",
                path=file_path
            )
        
        try:
            # Read file
            with open(resolved_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self._log_audit("read", file_path, True, f"Read {len(content)} bytes")
            
            return OperationResult(
                success=True,
                data=content,
                path=str(resolved_path)
            )
            
        except Exception as e:
            self._log_audit("read", file_path, False, str(e))
            return OperationResult(
                success=False,
                error=f"Failed to read file: {str(e)}",
                path=file_path
            )
    
    def list_directory(self, dir_path: str = ".") -> OperationResult:
        """
        List contents of a directory
        
        Args:
            dir_path: Directory path (relative to sandbox)
            
        Returns:
            OperationResult with directory listing
        """
        # Validate path
        resolved_path = self._validate_path(dir_path)
        if not resolved_path:
            return OperationResult(
                success=False,
                error="Invalid path or path traversal attempt detected",
                path=dir_path
            )
        
        # Check if directory exists
        if not resolved_path.exists():
            self._log_audit("list", dir_path, False, "Directory not found")
            return OperationResult(
                success=False,
                error=f"Directory not found: {dir_path}",
                path=dir_path
            )
        
        # Check if it's a directory
        if not resolved_path.is_dir():
            self._log_audit("list", dir_path, False, "Not a directory")
            return OperationResult(
                success=False,
                error=f"Not a directory: {dir_path}",
                path=dir_path
            )
        
        try:
            # List directory contents
            entries = []
            for entry in resolved_path.iterdir():
                entry_info = {
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                    "size": entry.stat().st_size if entry.is_file() else None
                }
                entries.append(entry_info)
            
            self._log_audit("list", dir_path, True, f"Listed {len(entries)} entries")
            
            return OperationResult(
                success=True,
                data=entries,
                path=str(resolved_path)
            )
            
        except Exception as e:
            self._log_audit("list", dir_path, False, str(e))
            return OperationResult(
                success=False,
                error=f"Failed to list directory: {str(e)}",
                path=dir_path
            )
    
    def write_file(self, file_path: str, content: str) -> OperationResult:
        """
        Write content to a file
        
        Args:
            file_path: Path to file (relative to sandbox)
            content: Content to write
            
        Returns:
            OperationResult
        """
        # Validate path
        resolved_path = self._validate_path(file_path)
        if not resolved_path:
            return OperationResult(
                success=False,
                error="Invalid path or path traversal attempt detected",
                path=file_path
            )
        
        # Check extension
        if not self._check_extension(resolved_path):
            self._log_audit("write", file_path, False, "File type not allowed")
            return OperationResult(
                success=False,
                error=f"File type not allowed: {resolved_path.suffix}",
                path=file_path
            )
        
        # Check content size
        content_size = len(content.encode('utf-8'))
        if content_size > self.max_file_size:
            self._log_audit("write", file_path, False, f"Content too large: {content_size} bytes")
            return OperationResult(
                success=False,
                error=f"Content too large: {content_size} bytes (max: {self.max_file_size})",
                path=file_path
            )
        
        try:
            # Ensure parent directory exists
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(resolved_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self._log_audit("write", file_path, True, f"Wrote {content_size} bytes")
            
            return OperationResult(
                success=True,
                data=f"Wrote {content_size} bytes",
                path=str(resolved_path)
            )
            
        except Exception as e:
            self._log_audit("write", file_path, False, str(e))
            return OperationResult(
                success=False,
                error=f"Failed to write file: {str(e)}",
                path=file_path
            )
    
    def delete_file(self, file_path: str) -> OperationResult:
        """
        Delete a file
        
        Args:
            file_path: Path to file (relative to sandbox)
            
        Returns:
            OperationResult
        """
        # Validate path
        resolved_path = self._validate_path(file_path)
        if not resolved_path:
            return OperationResult(
                success=False,
                error="Invalid path or path traversal attempt detected",
                path=file_path
            )
        
        # Check if file exists
        if not resolved_path.exists():
            self._log_audit("delete", file_path, False, "File not found")
            return OperationResult(
                success=False,
                error=f"File not found: {file_path}",
                path=file_path
            )
        
        # Check if it's a file (not directory)
        if not resolved_path.is_file():
            self._log_audit("delete", file_path, False, "Not a file")
            return OperationResult(
                success=False,
                error=f"Not a file: {file_path}",
                path=file_path
            )
        
        try:
            # Delete file
            resolved_path.unlink()
            
            self._log_audit("delete", file_path, True, "File deleted")
            
            return OperationResult(
                success=True,
                data="File deleted successfully",
                path=str(resolved_path)
            )
            
        except Exception as e:
            self._log_audit("delete", file_path, False, str(e))
            return OperationResult(
                success=False,
                error=f"Failed to delete file: {str(e)}",
                path=file_path
            )
    
    def create_directory(self, dir_path: str) -> OperationResult:
        """
        Create a directory
        
        Args:
            dir_path: Directory path (relative to sandbox)
            
        Returns:
            OperationResult
        """
        # Validate path
        resolved_path = self._validate_path(dir_path)
        if not resolved_path:
            return OperationResult(
                success=False,
                error="Invalid path or path traversal attempt detected",
                path=dir_path
            )
        
        # Check if already exists
        if resolved_path.exists():
            self._log_audit("create_dir", dir_path, False, "Already exists")
            return OperationResult(
                success=False,
                error=f"Already exists: {dir_path}",
                path=dir_path
            )
        
        try:
            # Create directory
            resolved_path.mkdir(parents=True, exist_ok=True)
            
            self._log_audit("create_dir", dir_path, True, "Directory created")
            
            return OperationResult(
                success=True,
                data="Directory created successfully",
                path=str(resolved_path)
            )
            
        except Exception as e:
            self._log_audit("create_dir", dir_path, False, str(e))
            return OperationResult(
                success=False,
                error=f"Failed to create directory: {str(e)}",
                path=dir_path
            )
    
    def get_audit_log(self) -> List[Dict]:
        """Get audit log for this skill"""
        return self.audit_log
    
    def get_sandbox_info(self) -> Dict[str, Any]:
        """Get information about the sandbox"""
        try:
            total_size = sum(f.stat().st_size for f in self.sandbox_dir.rglob('*') if f.is_file())
            file_count = sum(1 for f in self.sandbox_dir.rglob('*') if f.is_file())
            dir_count = sum(1 for d in self.sandbox_dir.rglob('*') if d.is_dir())
            
            return {
                "sandbox_dir": str(self.sandbox_dir),
                "total_size_bytes": total_size,
                "file_count": file_count,
                "directory_count": dir_count,
                "max_file_size": self.max_file_size,
                "allowed_extensions": self.allowed_extensions
            }
        except Exception as e:
            return {
                "sandbox_dir": str(self.sandbox_dir),
                "error": str(e)
            }


# Skill metadata for registration
SKILL_METADATA = {
    "id": "filesystem",
    "name": "File System",
    "version": "1.0.0",
    "description": "Secure file system operations with sandbox isolation",
    "operations": ["read", "write", "delete", "list", "create_dir"],
    "security_level": "high",
    "requires_hitl": True,
    "sandboxed": True
}


def create_skill(sandbox_dir: Optional[str] = None) -> FileSystemSkill:
    """Factory function to create FileSystemSkill instance"""
    return FileSystemSkill(sandbox_dir)