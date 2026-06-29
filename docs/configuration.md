# Configuration Guide

## Overview

The Blake package supports extensive configuration options to customize behavior for different use cases, environments, and requirements. This guide covers all configuration methods and options.

## Configuration Methods

### 1. Environment Variables

Set these environment variables for global configuration:

```bash
# Data directory
export BLAKE_DATA_DIR="/path/to/your/blake/data"

# Download settings
export BLAKE_MAX_CONCURRENT_DOWNLOADS=10
export BLAKE_DOWNLOAD_TIMEOUT=30
export BLAKE_RETRY_ATTEMPTS=3
export BLAKE_USER_AGENT="Blake Package/1.0"

# Analysis settings
export BLAKE_ENABLE_TEXT_ANALYSIS=true
export BLAKE_ENABLE_VISUAL_ANALYSIS=true
export BLAKE_ENABLE_CROSS_ANALYSIS=true
export BLAKE_BATCH_SIZE=5

# GUI settings
export BLAKE_GUI_HOST="localhost"
export BLAKE_GUI_PORT=8501
export BLAKE_GUI_THEME="light"

# API settings
export BLAKE_API_HOST="0.0.0.0"
export BLAKE_API_PORT=8000
export BLAKE_API_CORS_ORIGINS="*"

# Logging
export BLAKE_LOG_LEVEL="INFO"
export BLAKE_LOG_FILE="/path/to/blake.log"
```

### 2. Configuration File

Create `blake_config.yaml` in your data directory:

```yaml
# Blake Package Configuration
version: "1.0"

# Data management
data:
  directory: "./blake_data"
  backup_enabled: true
  backup_frequency: "daily"
  max_storage_gb: 100

# Download configuration
download:
  max_concurrent: 10
  timeout: 30
  retry_attempts: 3
  user_agent: "Blake Package/1.0"
  respect_robots_txt: true
  delay_between_requests: 1.0
  
  # Source-specific settings
  sources:
    blake_archive:
      enabled: true
      api_key: "your_api_key"
      rate_limit: 10
    project_gutenberg:
      enabled: true
      rate_limit: 5
    internet_archive:
      enabled: true
      api_key: "your_api_key"
      rate_limit: 15

# Analysis configuration
analysis:
  text_analysis:
    enabled: true
    models:
      - "en_core_web_sm"
      - "en_core_web_md"
    features:
      - "sentiment"
      - "entities"
      - "topics"
      - "stylistic"
  
  visual_analysis:
    enabled: true
    features:
      - "color_analysis"
      - "composition"
      - "object_detection"
      - "similarity"
    image_processing:
      max_size: [2048, 2048]
      thumbnail_size: [300, 300]
      formats: ["jpg", "png", "tiff"]
  
  cross_analysis:
    enabled: true
    features:
      - "text_image_correlation"
      - "thematic_consistency"
      - "temporal_analysis"
  
  batch_processing:
    enabled: true
    batch_size: 5
    max_workers: 3

# Database configuration
database:
  type: "sqlite"
  path: "./blake_data/metadata/blake.db"
  backup_enabled: true
  backup_frequency: "daily"
  
  # For PostgreSQL (if used)
  postgresql:
    host: "localhost"
    port: 5432
    database: "blake"
    username: "blake_user"
    password: "blake_password"

# GUI configuration
gui:
  enabled: true
  host: "localhost"
  port: 8501
  theme: "light"
  title: "Blake Works Explorer"
  
  # Customization
  custom_css: null
  custom_js: null
  
  # Features
  features:
    work_browser: true
    search_interface: true
    analysis_dashboard: true
    export_tools: true
    user_management: false

# API configuration
api:
  enabled: true
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["*"]
  rate_limiting:
    enabled: true
    requests_per_minute: 60
  
  # Authentication (optional)
  authentication:
    enabled: false
    jwt_secret: "your_jwt_secret"
    token_expiry: 3600

# Export configuration
export:
  default_format: "json"
  output_directory: "./blake_data/exports"
  
  formats:
    json:
      enabled: true
      pretty_print: true
      include_metadata: true
    csv:
      enabled: true
      delimiter: ","
      include_headers: true
    pdf:
      enabled: true
      template: "default"
      include_images: true
    parquet:
      enabled: true
      compression: "snappy"

# Logging configuration
logging:
  level: "INFO"
  file: "./blake_data/logs/blake.log"
  max_size_mb: 100
  backup_count: 5
  
  # Loggers
  loggers:
    blake: "INFO"
    blake.downloader: "DEBUG"
    blake.analysis: "INFO"
    blake.gui: "WARNING"

# Performance configuration
performance:
  cache_size: 1000
  memory_limit_mb: 2048
  cpu_limit: 4
  
  # Optimization
  optimization:
    enable_caching: true
    enable_compression: true
    enable_parallel_processing: true

# Security configuration
security:
  enable_https: false
  ssl_cert: null
  ssl_key: null
  
  # Data protection
  data_encryption: false
  encryption_key: null
  
  # Access control
  allowed_ips: []
  blocked_ips: []

# Monitoring configuration
monitoring:
  enabled: true
  metrics_port: 9090
  
  # Health checks
  health_checks:
    enabled: true
    interval: 60
    timeout: 30
  
  # Alerts
  alerts:
    email:
      enabled: false
      smtp_server: null
      smtp_port: 587
      username: null
      password: null
      recipients: []
```

### 3. Programmatic Configuration

Configure the package programmatically:

```python
from blake import BlakeCorpus, CorpusConfig
from pathlib import Path

# Create configuration
config = CorpusConfig(
    data_dir=Path("./my_blake_data"),
    output_dir=Path("./analysis_output"),
    quick=True,
    target_profile="canonical",
    fixture_mode="auto",
    viz_profile="core",
)

# Initialize with configuration
corpus = BlakeCorpus(config=config)
```

### 4. Command Line Configuration

Use command line arguments:

```bash
# Basic configuration
blake --data-dir /path/to/data --output-dir /path/to/output corpus run --quick

# Coverage and visualization profiles
blake corpus run --quick --fixture-mode auto --viz-profile core
blake corpus status --coverage
blake corpus visualize --profile core

# Advanced configuration
blake --config-file /path/to/config.yaml --verbose

# GUI with custom settings
blake gui --host 0.0.0.0 --port 8502 --theme dark

# API with custom settings
blake api --host 0.0.0.0 --port 8001 --cors-origins "*"
```

## Configuration Options

### Download Configuration

#### Basic Settings
- `max_concurrent_downloads`: Maximum simultaneous downloads (default: 10)
- `timeout`: Download timeout in seconds (default: 30)
- `retry_attempts`: Number of retry attempts (default: 3)
- `user_agent`: User agent string for requests
- `delay_between_requests`: Delay between requests in seconds (default: 1.0)

#### Source-Specific Settings
```yaml
download:
  sources:
    blake_archive:
      enabled: true
      api_key: "your_api_key"
      rate_limit: 10
      timeout: 60
    project_gutenberg:
      enabled: true
      rate_limit: 5
      timeout: 30
    internet_archive:
      enabled: true
      api_key: "your_api_key"
      rate_limit: 15
      timeout: 45
```

### Analysis Configuration

#### Text Analysis
```yaml
analysis:
  text_analysis:
    enabled: true
    models:
      - "en_core_web_sm"  # Small model
      - "en_core_web_md"  # Medium model
    features:
      - "sentiment"       # Sentiment analysis
      - "entities"        # Named entity recognition
      - "topics"          # Topic modeling
      - "stylistic"       # Stylistic analysis
    batch_size: 10
    max_text_length: 1000000
```

#### Visual Analysis
```yaml
analysis:
  visual_analysis:
    enabled: true
    features:
      - "color_analysis"    # Color palette analysis
      - "composition"       # Composition analysis
      - "object_detection"  # Object detection
      - "similarity"        # Image similarity
    image_processing:
      max_size: [2048, 2048]
      thumbnail_size: [300, 300]
      formats: ["jpg", "png", "tiff"]
      quality: 95
```

#### Cross Analysis
```yaml
analysis:
  cross_analysis:
    enabled: true
    features:
      - "text_image_correlation"  # Text-image relationships
      - "thematic_consistency"    # Thematic consistency
      - "temporal_analysis"       # Temporal patterns
    correlation_threshold: 0.7
    similarity_threshold: 0.8
```

### Database Configuration

#### SQLite (Default)
```yaml
database:
  type: "sqlite"
  path: "./blake_data/metadata/blake.db"
  backup_enabled: true
  backup_frequency: "daily"
  vacuum_frequency: "weekly"
```

#### PostgreSQL
```yaml
database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "blake"
  username: "blake_user"
  password: "blake_password"
  pool_size: 10
  max_overflow: 20
```

### GUI Configuration

#### Basic Settings
```yaml
gui:
  enabled: true
  host: "localhost"
  port: 8501
  theme: "light"  # "light" or "dark"
  title: "Blake Works Explorer"
```

#### Advanced Settings
```yaml
gui:
  features:
    work_browser: true
    search_interface: true
    analysis_dashboard: true
    export_tools: true
    user_management: false
    real_time_updates: true
  
  customization:
    custom_css: "/path/to/custom.css"
    custom_js: "/path/to/custom.js"
    logo: "/path/to/logo.png"
    favicon: "/path/to/favicon.ico"
```

### API Configuration

#### Basic Settings
```yaml
api:
  enabled: true
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["*"]
```

#### Advanced Settings
```yaml
api:
  rate_limiting:
    enabled: true
    requests_per_minute: 60
    burst_size: 10
  
  authentication:
    enabled: false
    jwt_secret: "your_jwt_secret"
    token_expiry: 3600
    refresh_token_expiry: 86400
  
  documentation:
    enabled: true
    title: "Blake API"
    description: "API for William Blake's works"
    version: "1.0.0"
```

### Export Configuration

#### Format Settings
```yaml
export:
  default_format: "json"
  output_directory: "./blake_data/exports"
  
  formats:
    json:
      enabled: true
      pretty_print: true
      include_metadata: true
      include_analysis: true
    
    csv:
      enabled: true
      delimiter: ","
      include_headers: true
      encoding: "utf-8"
    
    pdf:
      enabled: true
      template: "default"
      include_images: true
      page_size: "A4"
    
    parquet:
      enabled: true
      compression: "snappy"
      include_metadata: true
```

### Logging Configuration

#### Basic Logging
```yaml
logging:
  level: "INFO"
  file: "./blake_data/logs/blake.log"
  max_size_mb: 100
  backup_count: 5
```

#### Advanced Logging
```yaml
logging:
  level: "INFO"
  file: "./blake_data/logs/blake.log"
  max_size_mb: 100
  backup_count: 5
  
  # Console logging
  console:
    enabled: true
    level: "INFO"
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  # Loggers
  loggers:
    blake: "INFO"
    blake.downloader: "DEBUG"
    blake.analysis: "INFO"
    blake.gui: "WARNING"
    blake.api: "INFO"
  
  # Structured logging
  structured:
    enabled: true
    format: "json"
```

### Performance Configuration

#### Memory and CPU
```yaml
performance:
  cache_size: 1000
  memory_limit_mb: 2048
  cpu_limit: 4
  
  # Optimization
  optimization:
    enable_caching: true
    enable_compression: true
    enable_parallel_processing: true
    enable_gpu_acceleration: false
```

#### Database Performance
```yaml
performance:
  database:
    connection_pool_size: 10
    max_overflow: 20
    pool_timeout: 30
    pool_recycle: 3600
    echo: false
```

### Security Configuration

#### Basic Security
```yaml
security:
  enable_https: false
  ssl_cert: null
  ssl_key: null
  
  # Data protection
  data_encryption: false
  encryption_key: null
```

#### Advanced Security
```yaml
security:
  enable_https: true
  ssl_cert: "/path/to/cert.pem"
  ssl_key: "/path/to/key.pem"
  
  # Data protection
  data_encryption: true
  encryption_key: "your_encryption_key"
  
  # Access control
  allowed_ips: ["192.168.1.0/24", "10.0.0.0/8"]
  blocked_ips: ["192.168.1.100"]
  
  # Authentication
  authentication:
    enabled: true
    method: "jwt"
    secret_key: "your_secret_key"
    token_expiry: 3600
```

## Configuration Validation

### Validate Configuration
```python
from blake.config import validate_config

# Validate configuration file
config_path = Path("./blake_config.yaml")
is_valid, errors = validate_config(config_path)

if not is_valid:
    print("Configuration errors:")
    for error in errors:
        print(f"- {error}")
```

### Configuration Schema
```yaml
# Configuration schema for validation
schema:
  type: "object"
  properties:
    data:
      type: "object"
      properties:
        directory:
          type: "string"
        backup_enabled:
          type: "boolean"
    download:
      type: "object"
      properties:
        max_concurrent:
          type: "integer"
          minimum: 1
          maximum: 100
        timeout:
          type: "integer"
          minimum: 1
          maximum: 300
```

## Best Practices

### 1. Environment-Specific Configuration
- Use different configuration files for development, staging, and production
- Store sensitive information (API keys, passwords) in environment variables
- Use configuration templates for common setups

### 2. Performance Optimization
- Adjust `max_concurrent_downloads` based on your network and system resources
- Enable caching for frequently accessed data
- Use appropriate database settings for your data size

### 3. Security Considerations
- Enable HTTPS in production environments
- Use strong encryption keys for sensitive data
- Implement proper access controls
- Regularly update configuration files

### 4. Monitoring and Logging
- Enable appropriate logging levels for your use case
- Set up log rotation to prevent disk space issues
- Monitor performance metrics and adjust configuration accordingly

### 5. Backup and Recovery
- Enable database backups
- Store configuration files in version control
- Test configuration changes in non-production environments

This comprehensive configuration system allows you to customize the Blake package for any use case, from personal research to large-scale institutional deployments.
