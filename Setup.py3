import os
import sys
import subprocess

# List of dependencies
dependencies = [
    "flask",
    "pyjwt",
    "werkzeug",
    "flask-session",
    "flask-socketio",
    "flask-cors"
]

def install_dependencies():
    """
    Install the required Python packages based on the operating system.
    """
    try:
        # Ensure pip is up-to-date
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)

        # Install dependencies
        for package in dependencies:
            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)

        print("\n✅ Dependencies installed successfully!")
    
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error installing dependencies: {e}")
        sys.exit(1)

def install_system_dependencies():
    """
    Installs system dependencies like SQLite (if needed) on Linux/macOS.
    """
    try:
        if sys.platform.startswith("linux"):
            print("\n🔹 Detected Linux OS...")
            subprocess.run(["sudo", "apt", "update"], check=True)
            subprocess.run(["sudo", "apt", "install", "-y", "sqlite3", "libsqlite3-dev"], check=True)

        elif sys.platform == "darwin":
            print("\n🔹 Detected macOS...")
            subprocess.run(["brew", "install", "sqlite"], check=True)

        print("\n✅ System dependencies installed successfully!")
    
    except Exception as e:
        print(f"\n⚠️ System dependency installation skipped or failed: {e}")

def main():
    print("\n🚀 Starting dependency installation...\n")

    # Install Python dependencies
    install_dependencies()

    # Install system dependencies if needed
    if sys.platform in ["linux", "darwin"]:  # Skip for Windows
        install_system_dependencies()

    print("\n🎉 Setup complete! You can now run your Flask app.")

if __name__ == "__main__":
    main()
