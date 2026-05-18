# Learning Workbench

## Run locally in WSL

Install the frontend and backend dependencies once:

```bash
npm install
npm run setup:backend
```

The backend setup command creates a local `.venv` and installs Python packages there, which avoids Debian/Ubuntu's externally-managed Python restriction.

If WSL says `No module named venv`, install the Python venv package first:

```bash
sudo apt install python3-venv
```

If your distro creates a venv without `pip`, the setup script will try to repair it automatically. If that still fails, install full Python support:

```bash
sudo apt install python3-full
```

Then start the whole project with:

```bash
npm run start
```

This launches:

- Vite frontend dev server
- FastAPI backend at `http://127.0.0.1:8483`

If your preferred base Python executable is not `python3`, override it during setup:

```bash
BASE_PYTHON=python3.12 npm run setup:backend
```

If your preferred runtime Python executable is not `.venv/bin/python`, override it when starting:

```bash
PYTHON_BIN=python npm run start
```
