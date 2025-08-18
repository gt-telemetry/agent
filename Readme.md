#Process for WIndows build:
C:\Users\esoares\AppData\Local\Programs\Python\Python312\python.exe -m nuitka --standalone --windows-company-name="GT Telemetry" --windows-product-name="GT7TelemetryAgent" --windows-product-version="1.0.0" --assume-yes-for-downloads --remove-output .\gt7_telemetry_agent.py

#Process for linux build:
python -m nuitka --onefile gt7_telemetry_agent.py