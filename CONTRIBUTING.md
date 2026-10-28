# Contributing to mvsep-cli

Thank you for your interest in contributing to `mvsep-cli`!

## Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/mvsep-cli.git
   cd mvsep-cli
   ```

2. **Set up a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies in editable mode:**
   ```bash
   pip install -e .
   ```

## Running Tests

Run the test suite using Python's built-in `unittest`:
```bash
python3 -m unittest discover tests
```

Make sure all tests pass before opening a Pull Request. If you introduce new features, please add corresponding test cases under `tests/`.

## Code Style

- Keep dependencies minimal (`requests`, `rich`).
- Write clean, readable Python with type annotations where appropriate.
- Follow PEP 8 guidelines.

## Submitting Pull Requests

1. Create a descriptive feature branch: `git checkout -b feature/my-new-feature`.
2. Commit your changes with clear commit messages.
3. Push to your branch: `git push origin feature/my-new-feature`.
4. Open a Pull Request on GitHub describing the motivation and changes made.
