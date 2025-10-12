# 🌸 BloomNet - Fractal Data Architecture

BloomNet is a distributed storage system inspired by fractal geometry, implementing a 3-way tree architecture for scalable, fault-tolerant data management.

> **New in v1.1.0**: Enhanced error handling, improved data consistency, and new health monitoring tools.

## ✨ Features

- **Fractal Architecture**: 3 kernel nodes + 9 datanodes across 3 data marts
- **Replication Factor 2**: Each data mart maintains 2 copies of data
- **Secure Networking**: JWT authentication + optional Tailscale overlay
- **Modern Web Portal**: Beautiful React-based interface for data management
- **S3-Compatible Storage**: MinIO object storage backend
- **Real-time Monitoring**: System health and upload progress tracking
- **Enhanced Error Handling**: Comprehensive error handling and retry mechanisms
- **Data Validation**: File validation including size and type checking
- **Health Monitoring**: New `check_health.py` script for system diagnostics
- **Automated Setup**: Improved initialization scripts for easier deployment

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 8GB+ RAM recommended
- Linux/macOS/Windows with Docker support
- Python 3.x (for initialization scripts)
- PyJWT library: `pip install PyJWT` (required for `init_marts.py`)

### 1. Clone and Setup
```bash
git clone <repository>
cd bloom-testbed
```

### 2. Configure Environment
```bash
# Edit .env file with your settings
nano .env
```

Required environment variables:
```env
KERNEL_JWT_SECRET=your-secret-key-here
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
# Optional: TAILSCALE_AUTHKEY=tskey-... (for secure networking)
```

### 3. Generate Authentication Tokens
```bash
python3 generate_tokens.py
```

### 4. Start the System
```bash
docker compose up --build -d
```

### 5. Configure MinIO (Optional)
If you need to customize CORS or bucket policies, use the provided configuration files:

```bash
# Apply CORS configuration (allows cross-origin requests)
mc admin policy add bloom-net cors-policy /path/to/cors.json

# Apply bucket policy (controls access to mart buckets)
mc admin policy add bloom-net bucket-policy /path/to/bucket-policy.json

# Attach policies to user (replace 'bloom-user' with your MinIO user)
mc admin policy attach bloom-net cors-policy --user=bloom-user
mc admin policy attach bloom-net bucket-policy --user=bloom-user
```

The provided configuration files (`cors.json` and `bucket-policy.json`) are templates that can be customized for your specific requirements.
### 6. Access the Portal
- **Portal**: http://localhost:3000
- **MinIO Console**: http://localhost:9001 (admin/minioadmin)
- **API Endpoints**: http://localhost:8001 (Kernel 1)

## Quick Reference

## Common Commands
```bash
# Start all services
docker compose up --build -d
```

```bash
# Quick system check
python3 check_health.py --verbose
```

```bash
# View logs
docker compose logs -f
```

```bash
# Restart services
docker compose restart
```

## Access URLs
- **Portal**: http://localhost:3000
- **MinIO Console**: http://localhost:9001 (admin/minioadmin)
- **API Endpoints**: http://localhost:8001 (Kernel 1)

## Development
```bash
# Regenerate tokens
python3 generate_tokens.py
```

```bash
# Run tests
./test_system.sh
```

---

## 🔧 Services

### Kernels (Port 8001-8003)
- **Registry Management**: Track datanodes and marts
- **Authentication**: JWT token validation
- **Presigned URLs**: MinIO upload URL generation
- **Replication Coordination**: Manage data replication with retry logic
- **Health Monitoring**: System health endpoints for monitoring

### Datanodes (Port 8101-8303)
- **Data Storage**: Store and serve data
- **Replication**: Sync with other nodes in mart
- **Health Monitoring**: Report status to kernels

### Portal (Port 3000)
- **File Upload**: Drag & drop interface
- **System Monitoring**: Real-time status dashboard
- **Registry Browser**: View system configuration

### MinIO (Port 9000/9001)
- **Object Storage**: S3-compatible storage
- **Data Buckets**: Organized by mart (photos, research, clients)

## 📊 Data Architecture

### Mart Structure
```
Photos Mart (RF=2)
├── Parent Node (photos-parent:8101)
├── Child A (photos-child-a:8102)
└── Child B (photos-child-b:8103)

Research Mart (RF=2)
├── Parent Node (research-parent:8201)
├── Child A (research-child-a:8202)
└── Child B (research-child-b:8203)

Clients Mart (RF=2)
├── Parent Node (clients-parent:8301)
├── Child A (clients-child-a:8302)
└── Child B (clients-child-b:8303)
```

### Replication Flow
1. **Upload**: Client → Parent Node → MinIO
2. **Replication**: Parent → Child Node (deterministic selection)
3. **Verification**: Child pulls from MinIO and confirms sync

## 🔐 Authentication

All services use JWT tokens for authentication:

### Token Types
- **Node Tokens**: For datanode-to-kernel communication
- **Portal Token**: For portal-to-kernel communication
- **Kernel Tokens**: For kernel-to-kernel communication

### Token Generation
```bash
python3 generate_tokens.py
```

## 🌐 API Endpoints

### Kernel API (http://localhost:8001)

#### Registry Management
```http
GET  /registry          # Get system registry
POST /declare_mart      # Declare new data mart
GET  /health           # Health check
```

#### Authentication
```http
POST /auth/generate    # Generate new tokens (dev only)
```

#### Storage
```http
POST /presign_upload   # Get MinIO presigned URL
POST /notify           # Notify upload completion
```

### Datanode API (http://localhost:8101)

#### Data Operations
```http
POST /write           # Upload file to mart
GET  /inventory       # List stored objects
GET  /health         # Health check
POST /sync           # Sync from MinIO
```

#### Registration
```http
POST /register       # Register with kernel
```

### Portal API (http://localhost:3000)

#### Data Management
```http
GET  /api/registry   # Get system registry
POST /api/presign    # Request upload URL
POST /api/notify     # Notify upload completion
```

## 📤 Data Ingestion

### Upload a File
```bash
# Upload to photos mart
curl -X POST -H "Authorization: Bearer $PHOTOS_PARENT_TOKEN" \
     -F "file=@photo.jpg" -F "key=my-photo.jpg" \
     http://localhost:8101/write
```

### Batch Upload
```bash
# Upload all sample data
./ingest_all.sh

# Upload to specific mart
./ingest_photos.sh
./ingest_research.sh
./ingest_clients.sh
```

## 🧪 Testing

### System Tests
```bash
./test_system.sh
```

### Manual API Tests
```bash
# Check kernel health
curl http://localhost:8001/health

# Check registry
curl http://localhost:8001/registry | jq .

# Check datanode inventory
curl http://localhost:8101/inventory | jq .
```

## 🔒 Security

### JWT Authentication
- All inter-service communication requires valid JWT tokens
- Tokens are validated against `KERNEL_JWT_SECRET`
- Different token types for different service roles

### Network Security (Optional)
- **Tailscale**: Encrypted overlay network
- **Docker Networks**: Isolated service communication
- **MinIO Security**: S3-compatible authentication

### Environment Variables
```env
# Required
KERNEL_JWT_SECRET=your-secret-key
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=password

# Optional (for Tailscale)
TAILSCALE_AUTHKEY=tskey-...
```

## 📈 Monitoring

### System Status
- **Portal Dashboard**: Real-time service health
- **Upload Progress**: Live upload tracking
- **Registry Updates**: Automatic refresh

### Health Checks
```bash
# All services
curl http://localhost:8001/health  # Kernel 1
curl http://localhost:8101/health  # Photos Parent
curl http://localhost:3000        # Portal
```

### Logs
```bash
# View all logs
docker compose logs

# Follow specific service
docker compose logs -f kernel1
docker compose logs -f portal
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Services Not Starting
```bash
# Check logs
docker compose logs

# Restart services
docker compose restart

# Rebuild if needed
docker compose up --build --force-recreate
```

#### 2. Authentication Errors
```bash
# Regenerate tokens
python3 generate_tokens.py

# Check token format
echo $PHOTOS_PARENT_TOKEN | cut -d'.' -f1 | base64 -d
```

#### 3. Upload Failures
```bash
# Check MinIO connectivity
curl http://localhost:9000/minio/health/ready

# Verify presigned URL
curl -I "your-presigned-url"
```

#### 4. Network Issues
```bash
# Check Docker networks
docker network ls

# Verify service discovery
docker compose exec kernel1 nslookup photos-parent
```

### Debug Commands
```bash
# Check container status
docker compose ps

# View container logs
docker compose logs kernel1
docker compose logs datanode

# Execute commands in container
docker compose exec kernel1 python3 -c "print('test')"
```

## 🔧 Configuration

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `KERNEL_JWT_SECRET` | JWT signing secret | Required |
| `MINIO_ROOT_USER` | MinIO admin username | minioadmin |
| `MINIO_ROOT_PASSWORD` | MinIO admin password | minioadmin |
| `TAILSCALE_AUTHKEY` | Tailscale auth key | Optional |

### Docker Compose Scaling
```yaml
# Scale specific services
docker compose up -d --scale kernel1=3 --scale datanode=9
```

## 📚 Architecture Details

### Fractal Design
BloomNet implements a fractal-inspired architecture:
- **Level 0**: 3 kernel nodes (registry + coordination)
- **Level 1**: 3 data marts (photos, research, clients)
- **Level 2**: 2 nodes per mart (parent + child)

### Replication Strategy
- **Replication Factor**: 2 (parent + 1 child)
- **Consistency Model**: Eventual consistency
- **Sync Mechanism**: Pull-based replication
- **Failure Handling**: Automatic failover

### Data Flow
1. **Write Path**: Client → Parent → MinIO → Child
2. **Read Path**: Client → Any Node → MinIO
3. **Replication**: Parent → MinIO → Child (background)

## 🚀 Production Deployment

### Requirements
- Kubernetes cluster (recommended)
- Persistent storage (NFS/EBS)
- Load balancer
- Monitoring stack (Prometheus/Grafana)

### Production Configuration
```yaml
# docker-compose.prod.yml
version: "3.9"
services:
  kernel1:
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
    volumes:
      - /persistent/kernel1:/app/data
```

### Security Hardening
- Enable TLS/HTTPS
- Use secrets management (Vault)
- Implement rate limiting
- Add audit logging

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🛠️ New Tools

### `check_health.py`
A comprehensive health check tool for the entire BloomNet system:

```bash
# Basic health check
python3 check_health.py

# Detailed output
python3 check_health.py --verbose

# Disable colored output
python3 check_health.py --no-color
```

### `init_marts.py`
Initialize and declare all marts in the system:

```bash
# Initialize all marts
python3 init_marts.py
```

## 📈 Monitoring

### System Health
Monitor the health of all services using the portal or the `check_health.py` script:

```bash
# Check system health
python3 check_health.py --verbose
```

### Logs
View logs for all services:

```bash
# View all logs
docker compose logs -f

# View logs for a specific service
docker compose logs -f kernel1
```

## 🆘 Support

- **Documentation**: See docs/ directory
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

---

**BloomNet** - A fractal approach to distributed storage 🌸
