# Contributing to ClosedPaw

Thank you for your interest in contributing to ClosedPaw! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Security Considerations](#security-considerations)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)

## Code of Conduct

This project and everyone participating in it is governed by our commitment to security and privacy first. We expect all contributors to:

- Respect the Zero-Trust architecture principles
- Prioritize security over convenience
- Never disable or bypass security features
- Report security vulnerabilities responsibly

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a new branch for your contribution
4. Follow the development setup instructions below

## How to Contribute

### Reporting Bugs

Before creating a bug report, please:

1. Check if the issue already exists
2. Use the latest version to verify the bug
3. Collect relevant logs and system information

When reporting bugs, include:
- Operating system and version
- Python/Node.js versions
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs (sanitized of sensitive data)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please provide:
- Clear description of the enhancement
- Use case and motivation
- Potential security implications
- Proposed implementation approach

### Security Issues

**DO NOT** report security vulnerabilities through public GitHub issues.

Instead, please create a private security advisory on GitHub

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Git
- gVisor or Kata Containers (for sandboxing)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Security Considerations

When contributing, you **MUST** adhere to these security requirements:

### Mandatory Security Practices

1. **Never disable security features** - Security is not optional
2. **Validate all inputs** - Use strict input validation for all user data
3. **Separate system and user prompts** - Prevent prompt injection attacks
4. **Use hardened sandboxes** - gVisor or Kata Containers only (Docker alone is insufficient)
5. **Encrypt sensitive data** - API keys must be encrypted at rest
6. **Log security events** - All actions must be audited
7. **Local-only binding** - Services must bind to 127.0.0.1 only

### Code Review Checklist

Before submitting a PR, verify:
- [ ] No hardcoded secrets or credentials
- [ ] All user inputs are validated and sanitized
- [ ] Security headers are present (CSP, HSTS, etc.)
- [ ] Error messages don't leak sensitive information
- [ ] Rate limiting is implemented for critical actions
- [ ] Audit logging is added for security-relevant operations

## Pull Request Process

1. **Create a feature branch** from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Test your changes** thoroughly
   - Run the test suite
   - Test on clean installations
   - Verify security features still work

4. **Update documentation** if needed

5. **Commit your changes** with clear messages
   ```bash
   git commit -m "feat: add feature description"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request** on GitHub

### PR Requirements

- Clear description of changes
- Reference any related issues
- Security impact assessment
- Testing evidence
- Documentation updates

### Commit Message Format

We follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/tooling changes
- `security`: Security-related changes

Examples:
```
feat(sandbox): add Kata Containers support

fix(security): prevent path traversal in file skill

docs(readme): update installation instructions
```

## Coding Standards

### Python

- Follow PEP 8
- Use type hints
- Document functions with docstrings
- Maximum line length: 100 characters
- Use `black` for formatting
- Use `pylint` or `ruff` for linting

### TypeScript/JavaScript

- Use TypeScript for new code
- Follow ESLint configuration
- Use functional components with hooks
- Document complex logic

### Security-Specific Rules

1. **Input Validation**
   ```python
   # Good
   from pydantic import BaseModel, validator
   
   class UserInput(BaseModel):
       path: str
       
       @validator('path')
       def validate_path(cls, v):
           if '..' in v or v.startswith('/'):
               raise ValueError('Invalid path')
           return v
   ```

2. **Secure Defaults**
   ```python
   # Good - secure by default
   def connect_to_service(host: str = "127.0.0.1", port: int = 8000):
       # Always bind to localhost by default
       ...
   ```

3. **Audit Logging**
   ```python
   # Required for security-relevant operations
   audit_logger.info(f"Action: {action_type}, User: {user_id}, Result: {result}")
   ```

## Questions?

If you have questions about contributing:
- Open a GitHub Discussion
- Join our community chat (coming soon)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make ClosedPaw more secure! 🔒