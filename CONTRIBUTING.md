# Contributing to Drone Ground Station

Thank you for your interest in contributing to the Andhra University CSSE Drone Ground Station project! This guide will help you get started.

---

## Code of Conduct

- Be respectful and constructive in all interactions
- Focus on technical merit in code reviews
- Help newcomers learn and grow
- Credit others' contributions

---

## Getting Started

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.8+ | Primary language |
| ROS2 | Humble | Middleware |
| GStreamer | 1.0+ | Video pipeline |
| Git | 2.25+ | Version control |
| pymavlink | 2.4+ | MAVLink protocol |
| OpenCV | 4.5+ | Image processing |

### Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/Andhra-University-CSSE-Drone-Ground-Station.git
cd Andhra-University-CSSE-Drone-Ground-Station

# 2. Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov

# 3. Build ROS2 package
cd src && colcon build && source install/setup.bash

# 4. Run tests
pytest tests/ -v
```

---

## How to Contribute

### Reporting Bugs

Open an issue with:
- **Title**: Short, descriptive summary
- **Environment**: OS, Python version, ROS2 version
- **Steps to reproduce**: Minimal steps to trigger the bug
- **Expected vs actual behavior**
- **Logs**: Relevant error output

### Suggesting Features

Open an issue with:
- **Use case**: What problem does this solve?
- **Proposed solution**: How should it work?
- **Alternatives considered**: What else did you think about?

### Submitting Code

1. Create a branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the code style guide below

3. Write tests for new functionality

4. Commit with a descriptive message:
   ```
   Add MAVLink GLOBAL_POSITION_INT message handling

   Parse lat/lon/relative_alt/hdg fields from message ID 33.
   Update telemetry_data under lock for thread safety.
   ```

5. Push and open a Pull Request

---

## Code Style Guide

### Python

- **PEP 8** compliance
- **Type hints** required on all function signatures
- **Docstrings** on all public methods
- **Line length**: 88 characters max (Black formatter)

```python
# Good
def parse_telemetry_data(self, data: bytes) -> None:
    """Parse received telemetry data (JSON or MAVLink)."""
    ...

# Bad
def parse_telemetry_data(self, data):
    ...
```

### Thread Safety

- All shared state **must** be protected by a `threading.Lock`
- Use helper methods: `_update_fields()`, `_get_telemetry_snapshot()`
- Never hold a lock while doing I/O

### Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Classes | PascalCase | `TelemetryReceiver` |
| Functions | snake_case | `parse_mavlink_data` |
| Private methods | _prefix | `_handle_mavlink_message` |
| Constants | UPPER_SNAKE | `MAVLINK_MODE_MAP` |
| ROS2 topics | slash/separated | `drone/battery` |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_telemetry_receiver.py -v
```

### Test Requirements

- New features need unit tests
- Bug fixes need regression tests
- Tests must pass without ROS2/hardware (use mocks)
- Aim for >80% coverage on new code

---

## Pull Request Checklist

- [ ] Code follows the style guide
- [ ] Type hints added to all new functions
- [ ] Thread safety considered for shared state
- [ ] Tests written and passing
- [ ] No secrets or credentials in code
- [ ] Commit messages are descriptive
- [ ] Documentation updated if needed

---

## Branch Naming

| Prefix | Use |
|--------|-----|
| `feature/` | New functionality |
| `fix/` | Bug fixes |
| `docs/` | Documentation only |
| `refactor/` | Code restructuring |
| `test/` | Test additions |

---

## Contact

**Andhra University**
Department of Computer Science & Systems Engineering

For academic inquiries or collaboration opportunities, please contact the department or open a GitHub issue.

---

*Thank you for helping improve the Drone Ground Station project!*
