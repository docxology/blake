# Troubleshooting Guide

## Common Issues and Solutions

### Installation Issues

#### Issue: Package Installation Fails
**Symptoms:**
- `pip install blake` fails with dependency errors
- `uv add blake` fails with resolution errors

**Solutions:**
```bash
# Update pip and setuptools
pip install --upgrade pip setuptools wheel

# Install with UV (recommended)
uv add blake

# Or install with pip and specific Python version
python3.11 -m pip install blake

# Install with all extras
uv add "blake[gui,api,dev]"
```

#### Issue: Missing Dependencies
**Symptoms:**
- `ModuleNotFoundError` for specific packages
- Import errors when running blake

**Solutions:**
```bash
# Install missing dependencies
uv add aiohttp aiofiles beautifulsoup4 lxml pandas numpy

# Install analysis dependencies
uv add nltk spacy scikit-learn transformers torch

# Install visualization dependencies
uv add matplotlib seaborn plotly streamlit

# Download spaCy model
python -m spacy download en_core_web_sm
```

### Download Issues

#### Issue: No Works Downloaded
**Symptoms:**
- `download_all()` returns empty list
- No files in data directory

**Solutions:**
```python
# Check internet connection
import aiohttp
async with aiohttp.ClientSession() as session:
    async with session.get('https://www.gutenberg.org') as response:
        print(f"Gutenberg accessible: {response.status}")

# Check source availability
from blake import BlakeCorpus
blake = BlakeCorpus("./blake_data", output_dir="./analysis_output")
works = await blake.download_all()
print(f"Downloaded {len(works)} works")

# Check specific source
from blake.models import SourceType
works = await blake.downloader.download_from_source(SourceType.PROJECT_GUTENBERG)
```

#### Issue: Download Failures
**Symptoms:**
- `DownloadError` exceptions
- Partial downloads
- Timeout errors

**Solutions:**
```python
# Increase timeout
import os
os.environ['BLAKE_DOWNLOAD_TIMEOUT'] = '60'

# Reduce concurrent downloads
os.environ['BLAKE_MAX_CONCURRENT_DOWNLOADS'] = '5'

# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check specific error
try:
    works = await blake.download_all()
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")
```

#### Issue: Slow Downloads
**Symptoms:**
- Downloads take very long time
- System becomes unresponsive

**Solutions:**
```python
# Reduce concurrent downloads
blake = BlakeCorpus("./blake_data", output_dir="./analysis_output")
blake.downloader.max_concurrent = 3

# Increase timeout
blake.downloader.timeout = 60

# Check network speed
import time
start = time.time()
# Run download
end = time.time()
print(f"Download time: {end - start} seconds")
```

### Analysis Issues

#### Issue: Analysis Fails
**Symptoms:**
- `AnalysisError` exceptions
- Works not marked as processed
- Empty analysis results

**Solutions:**
```python
# Check if work has content
work = await blake.get_work("21160")
print(f"Has text: {work.text_content is not None}")
print(f"Has images: {len(work.images) > 0}")

# Check analysis errors
print(f"Processing errors: {work.processing_errors}")

# Run analysis manually
try:
    results = await blake.analyze_work("21160")
    print(f"Analysis results: {results}")
except Exception as e:
    print(f"Analysis error: {e}")
```

#### Issue: spaCy Model Not Found
**Symptoms:**
- Warning: "spaCy English model not found"
- Text analysis fails

**Solutions:**
```bash
# Download spaCy model
python -m spacy download en_core_web_sm

# Or install with pip
pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.4.1/en_core_web_sm-3.4.1.tar.gz

# Verify installation
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('Model loaded successfully')"
```

#### Issue: Memory Issues During Analysis
**Symptoms:**
- `MemoryError` exceptions
- System becomes slow
- Analysis stops unexpectedly

**Solutions:**
```python
# Clear cache
blake.clear_cache()

# Process works in smaller batches
works = await blake.get_all_works()
batch_size = 3
for i in range(0, len(works), batch_size):
    batch = works[i:i + batch_size]
    for work in batch:
        await blake.analyze_work(work.id)
    blake.clear_cache()

# Check memory usage
import psutil
print(f"Memory usage: {psutil.virtual_memory().percent}%")
```

### GUI Issues

#### Issue: GUI Won't Start
**Symptoms:**
- `blake.explore()` fails
- Port already in use error
- Streamlit errors

**Solutions:**
```python
# Check if port is available
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('localhost', 8501))
if result == 0:
    print("Port 8501 is in use")
    sock.close()
else:
    print("Port 8501 is available")
    sock.close()

# Use different port
blake.explore(port=8502)

# Check Streamlit installation
import streamlit as st
print(f"Streamlit version: {st.__version__}")
```

#### Issue: GUI Loads But No Data
**Symptoms:**
- GUI opens but shows no works
- Empty interface
- Loading errors

**Solutions:**
```python
# Check if data exists
works = await blake.get_all_works()
print(f"Works in database: {len(works)}")

# Check data directory
import os
data_dir = Path("./blake_data")
print(f"Data directory exists: {data_dir.exists()}")
print(f"Contents: {list(data_dir.iterdir())}")

# Refresh GUI data
blake.clear_cache()
# Restart GUI
```

### Database Issues

#### Issue: Database Errors
**Symptoms:**
- `DatabaseError` exceptions
- Works not saved
- Search returns empty results

**Solutions:**
```python
# Check database file
import sqlite3
db_path = Path("./blake_data/metadata/blake.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM works")
    count = cursor.fetchone()[0]
    print(f"Works in database: {count}")
    conn.close()
else:
    print("Database file not found")

# Recreate database
blake.metadata_manager.recreate_database()
```

#### Issue: Search Not Working
**Symptoms:**
- Search returns no results
- Search errors
- Slow search performance

**Solutions:**
```python
# Check search functionality
results = await blake.search_works("innocence")
print(f"Search results: {len(results)}")

# Check database indexes
import sqlite3
conn = sqlite3.connect("./blake_data/metadata/blake.db")
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
indexes = cursor.fetchall()
print(f"Database indexes: {indexes}")
conn.close()

# Rebuild search index
blake.metadata_manager.rebuild_search_index()
```

### Performance Issues

#### Issue: Slow Performance
**Symptoms:**
- Operations take very long
- System becomes unresponsive
- High memory usage

**Solutions:**
```python
# Check system resources
import psutil
print(f"CPU usage: {psutil.cpu_percent()}%")
print(f"Memory usage: {psutil.virtual_memory().percent}%")
print(f"Disk usage: {psutil.disk_usage('/').percent}%")

# Optimize configuration
import os
os.environ['BLAKE_MAX_CONCURRENT_DOWNLOADS'] = '3'
os.environ['BLAKE_BATCH_SIZE'] = '2'

# Clear caches
blake.clear_cache()
import gc
gc.collect()
```

#### Issue: High Memory Usage
**Symptoms:**
- Memory usage keeps growing
- System becomes slow
- Out of memory errors

**Solutions:**
```python
# Monitor memory usage
import psutil
import gc

def check_memory():
    return psutil.virtual_memory().percent

print(f"Memory before: {check_memory()}%")

# Process works in batches
works = await blake.get_all_works()
batch_size = 5
for i in range(0, len(works), batch_size):
    batch = works[i:i + batch_size]
    for work in batch:
        await blake.analyze_work(work.id)
    
    # Clear cache and garbage collect
    blake.clear_cache()
    gc.collect()
    print(f"Memory after batch {i//batch_size + 1}: {check_memory()}%")
```

### File System Issues

#### Issue: Permission Errors
**Symptoms:**
- `PermissionError` when creating files
- Cannot write to data directory
- Access denied errors

**Solutions:**
```python
# Check directory permissions
import os
data_dir = Path("./blake_data")
print(f"Directory exists: {data_dir.exists()}")
print(f"Directory writable: {os.access(data_dir, os.W_OK)}")

# Create directory with proper permissions
data_dir.mkdir(parents=True, exist_ok=True)
os.chmod(data_dir, 0o755)

# Use different directory
blake = BlakeCorpus(Path.home() / "blake_data", output_dir=Path.home() / "analysis_output")
```

#### Issue: Disk Space Issues
**Symptoms:**
- `No space left on device` errors
- Downloads fail
- Database errors

**Solutions:**
```python
# Check disk space
import shutil
total, used, free = shutil.disk_usage("./blake_data")
print(f"Total: {total // (1024**3)} GB")
print(f"Used: {used // (1024**3)} GB")
print(f"Free: {free // (1024**3)} GB")

# Clean up old files
import os
for root, dirs, files in os.walk("./blake_data"):
    for file in files:
        if file.endswith('.tmp'):
            os.remove(os.path.join(root, file))

# Use different location
blake = BlakeCorpus(Path("/path/to/larger/disk/blake_data"), output_dir=Path("/path/to/larger/disk/analysis_output"))
```

### Network Issues

#### Issue: Network Timeouts
**Symptoms:**
- `asyncio.TimeoutError` exceptions
- Downloads fail with timeout
- Slow network operations

**Solutions:**
```python
# Increase timeout
import os
os.environ['BLAKE_DOWNLOAD_TIMEOUT'] = '120'

# Check network connectivity
import aiohttp
async def test_connectivity():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get('https://www.gutenberg.org', timeout=30) as response:
                print(f"Gutenberg: {response.status}")
        except Exception as e:
            print(f"Gutenberg error: {e}")

# Run connectivity test
import asyncio
asyncio.run(test_connectivity())
```

#### Issue: Rate Limiting
**Symptoms:**
- HTTP 429 errors
- Downloads blocked
- IP banned

**Solutions:**
```python
# Reduce download rate
import os
os.environ['BLAKE_MAX_CONCURRENT_DOWNLOADS'] = '1'
os.environ['BLAKE_DELAY_BETWEEN_REQUESTS'] = '2.0'

# Use different user agent
os.environ['BLAKE_USER_AGENT'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Wait and retry
import time
time.sleep(60)  # Wait 1 minute
```

### Debugging Tools

#### Enable Debug Logging
```python
import logging

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('blake_debug.log'),
        logging.StreamHandler()
    ]
)

# Run with debug logging
works = await blake.download_all()
```

#### Check System Information
```python
import sys
import platform
import psutil

print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"CPU count: {psutil.cpu_count()}")
print(f"Memory: {psutil.virtual_memory().total // (1024**3)} GB")
print(f"Disk space: {psutil.disk_usage('/').free // (1024**3)} GB")
```

#### Verify Installation
```python
# Check package installation
try:
    import blake
    print(f"Blake package version: {blake.__version__}")
except ImportError as e:
    print(f"Blake package not found: {e}")

# Check dependencies
dependencies = [
    'aiohttp', 'aiofiles', 'beautifulsoup4', 'lxml',
    'pandas', 'numpy', 'nltk', 'spacy', 'streamlit'
]

for dep in dependencies:
    try:
        __import__(dep)
        print(f"✓ {dep}")
    except ImportError:
        print(f"✗ {dep} - not installed")
```

### Getting Help

#### Check Logs
```python
# Check log files
import os
log_dir = Path("./blake_data/logs")
if log_dir.exists():
    for log_file in log_dir.glob("*.log"):
        print(f"Log file: {log_file}")
        with open(log_file, 'r') as f:
            lines = f.readlines()
            print(f"Last 10 lines:")
            for line in lines[-10:]:
                print(line.strip())
```

#### Create Bug Report
```python
# Generate system information for bug report
import sys
import platform
import blake

bug_report = {
    "python_version": sys.version,
    "platform": platform.platform(),
    "blake_version": blake.__version__,
    "data_directory": str(blake.data_dir),
    "works_count": len(await blake.get_all_works()),
    "error_log": "Check blake_data/logs/ for error logs"
}

print("Bug Report Information:")
for key, value in bug_report.items():
    print(f"{key}: {value}")
```

#### Community Support
- **GitHub Issues**: Report bugs and request features
- **GitHub Discussions**: Ask questions and share ideas
- **Documentation**: Check this guide and API reference
- **Examples**: Look at example scripts in `/examples` directory

### Prevention Tips

1. **Regular Updates**: Keep the package and dependencies updated
2. **Backup Data**: Regularly backup your data directory
3. **Monitor Resources**: Keep an eye on disk space and memory usage
4. **Test Changes**: Test configuration changes in a safe environment
5. **Read Logs**: Regularly check log files for warnings and errors
6. **Use Virtual Environments**: Isolate the package in a virtual environment
7. **Document Issues**: Keep track of issues and their solutions

This troubleshooting guide should help you resolve most common issues with the Blake package. If you encounter a problem not covered here, please create a GitHub issue with detailed information about your system and the error you're experiencing.
