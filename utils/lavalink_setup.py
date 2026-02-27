import os
import subprocess
import shutil
import sys
import tarfile
import urllib.request

# Configuration
LAVALINK_URL = "https://github.com/lavalink-devs/Lavalink/releases/download/4.0.8/Lavalink.jar"
# URL for OpenJDK 17 JRE (LTS) - Linux x64
JRE_URL = "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jre/hotspot/normal/eclipse?project=jdk"

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAVALINK_DIR = os.path.join(BASE_DIR, "lavalink")
JAR_PATH = os.path.join(LAVALINK_DIR, "Lavalink.jar")
CONFIG_PATH = os.path.join(LAVALINK_DIR, "application.yml")
JRE_DIR = os.path.join(LAVALINK_DIR, "jre")
JRE_BIN = os.path.join(JRE_DIR, "bin", "java")

def get_java_path():
    """Find a valid Java executable."""
    # 1. Check local JRE
    if os.path.exists(JRE_BIN) and os.access(JRE_BIN, os.X_OK):
        return JRE_BIN
    
    # 2. Check system PATH
    system_java = shutil.which("java")
    if system_java:
        return system_java

    # 3. Check common locations
    common_paths = [
        "/usr/bin/java",
        "/usr/local/bin/java",
        "/bin/java"
    ]
    for p in common_paths:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
            
    return None

def download_file(url, path):
    """Download a file using curl or urllib."""
    try:
        subprocess.check_call(["curl", "-L", url, "-o", path])
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            print(f"curl failed, trying urllib for {url}...")
            urllib.request.urlretrieve(url, path)
            return True
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return False

def download_jre():
    """Download and extract OpenJDK 17 JRE."""
    print("Java not found. Downloading OpenJDK 17 JRE...")
    if not os.path.exists(LAVALINK_DIR):
        os.makedirs(LAVALINK_DIR)
        
    tar_path = os.path.join(LAVALINK_DIR, "jre.tar.gz")
    
    if not download_file(JRE_URL, tar_path):
        return None
        
    print("Extracting JRE...")
    try:
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=LAVALINK_DIR)
            
        os.remove(tar_path)
        
        # Rename the extracted folder to 'jre'
        extracted_dirs = [d for d in os.listdir(LAVALINK_DIR) if os.path.isdir(os.path.join(LAVALINK_DIR, d)) and "jdk" in d]
        if extracted_dirs:
            # Sort by name length to find the most specific one if multiple? Usually just one.
            extracted_dir = os.path.join(LAVALINK_DIR, extracted_dirs[0])
            if os.path.exists(JRE_DIR):
                shutil.rmtree(JRE_DIR)
            os.rename(extracted_dir, JRE_DIR)
            
        if os.path.exists(JRE_BIN):
            os.chmod(JRE_BIN, 0o755)
            print(f"JRE installed to {JRE_DIR}")
            return JRE_BIN
            
    except Exception as e:
        print(f"Failed to extract/install JRE: {e}")
        return None
        
    return None

def setup_lavalink():
    """Ensure Lavalink is installed and configured. Returns the java executable path."""
    if not os.path.exists(LAVALINK_DIR):
        os.makedirs(LAVALINK_DIR)

    java_path = get_java_path()
    if not java_path:
        java_path = download_jre()
        if not java_path:
            print("Error: Could not find or install a valid Java runtime.")
            return None

    if not os.path.exists(JAR_PATH):
        print(f"Lavalink.jar not found. Downloading from {LAVALINK_URL}...")
        if not download_file(LAVALINK_URL, JAR_PATH):
            return None

    # Always rewrite configuration to ensure plugins are present
    print(f"Updating application.yml configuration...")
    with open(CONFIG_PATH, "w") as f:
        f.write("""server: # REST and WS server
  port: 2333
  address: 0.0.0.0
lavalink:
  plugins:
    - dependency: "dev.lavalink.youtube:youtube-plugin:1.11.1"
      repository: "https://maven.lavalink.dev/releases"
      snapshot: false
  server:
    password: "youshallnotpass"
    sources:
      youtube: false # Use plugin instead
      bandcamp: true
      soundcloud: true
      twitch: true
      vimeo: true
      http: true
      local: false
    bufferDurationMs: 400
    frameBufferDurationMs: 5000
    opusEncodingQuality: 10
    resamplingQuality: LOW
    trackStuckThresholdMs: 10000
    useSeekGhosting: true
    youtubePlaylistLoadLimit: 6
    playerUpdateInterval: 5
    youtubeSearchEnabled: true
    soundcloudSearchEnabled: true
    gc-warnings: true
    
    youtube:
      enabled: true
      allowSearch: true
      clients:
        - MUSIC
        - ANDROID_TESTSUITE
        - WEB
        - TVHTML5EMBEDDED
      # pot: "..." # Enable this if using PoToken
      # visitorData: "..." # Enable this if using Visitor Data

metrics:
  prometheus:
    enabled: false
    endpoint: /metrics

logging:
  file:
    path: ./logs/
  level:
    root: INFO
    lavalink: INFO
""")
    
    return java_path

if __name__ == "__main__":
    path = setup_lavalink()
    if path:
        print(f"Lavalink setup complete. Java path: {path}")
    else:
        sys.exit(1)
