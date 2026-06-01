# Contributing to OneAPI

Thank you for your interest in contributing! 🎉

## How to Contribute

### 1. Fork & Clone

```bash
git clone https://github.com/YOUR_USERNAME/OneAPI.git
cd OneAPI
```

### 2. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

### 3. Make Changes

- Follow the existing code style
- Add tests for new features
- Update documentation if needed

### 4. Test

```bash
pip install -e ".[dev]"
pytest tests/
```

### 5. Submit PR

- Write a clear description of your changes
- Link any related issues
- Make sure all tests pass

## Adding a New Provider

1. Create a new file in `oneapi/providers/`
2. Extend `BaseProvider` and implement `chat()` and `models()`
3. Use the `@register_provider("name")` decorator
4. Add the provider config to `oneapi/config.py`
5. Add routing rules in `DEFAULT_ROUTES`
6. Update README with the new provider info

## Code Style

- Python 3.10+
- Use type hints
- Line length: 100 chars
- Run `ruff check .` before committing

## Reporting Issues

- Use GitHub Issues
- Include: OS, Python version, error message, steps to reproduce

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
