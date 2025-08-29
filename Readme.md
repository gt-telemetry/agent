
# GT7 Telemetry Agent

A cross-platform telemetry agent for Gran Turismo 7, designed to collect, save, and upload lap data for analysis and sharing. Supports local and remote storage, robust error handling, and easy integration with the GT Telemetry backend.

---

## Setup

### Requirements
- Python 3.8+
- pip (Python package manager)
- (Optional) Nuitka for building standalone executables

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/frogwog/SimRacingTelemetryApp-agent.git
   cd SimRacingTelemetryApp-agent
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Optional) Build with Nuitka:
   - **Windows:**
     ```bash
     python -m nuitka --standalone --windows-company-name="<Your Company Name>" --windows-product-name="<Agent name>" --windows-product-version="1.0.0" --assume-yes-for-downloads --remove-output <path to main>
     ```
   - **Linux:**
     ```bash
     python -m nuitka --onefile <path to main>
     ```

---

## Usage

Run the agent from the command line:
```bash
python gt7_telemetry_agent.py [--ps_ip <PlayStation_IP>] [--local] [--track] [--verbose]
```

- `--ps_ip` : PlayStation IPv4 address (prompted if not provided)
- `--local` : Save laps locally instead of uploading to GT Telemetry backend
- `--track` : Record only positional data to save track layout
- `--verbose` or `-v` : Enable debug logging

You will be prompted to choose local or remote lap saving. For remote, you must provide a valid JWT token for authentication.

---

## Contribution Guidelines

We welcome contributions! To contribute:
1. Fork the repository and create your feature branch (`git checkout -b feature/AmazingFeature`)
2. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
3. Push to the branch (`git push origin feature/AmazingFeature`)
4. Open a pull request

### Code Style
- Use type hints and docstrings for all functions/classes
- Follow PEP8 for Python code
- Add tests for new features or bug fixes
- Ensure all dependencies are listed in `requirements.txt` and `pyproject.toml`

---

## License
MIT

---

## Support
For questions or help, open an issue or contact the maintainers via GitHub.