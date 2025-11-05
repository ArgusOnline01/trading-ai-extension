# Docker Quick Start Guide

**For Visual Trade Copilot Backend**

---

## First Time Setup

1. **Create `.env` file** (in root directory)
   ```bash
   # Copy the example
   cp .env.example .env
   ```
   
   Then edit `.env` and add your OpenAI API key:
   ```
   OPENAI_API_KEY=sk-your-api-key-here
   ```

2. **Build and start the server**
   ```bash
   docker-compose up --build
   ```

---

## Daily Use

### Start Server
```bash
docker-compose up
```

### Start in Background
```bash
docker-compose up -d
```

### Stop Server
```bash
docker-compose down
```

### View Logs
```bash
docker-compose logs -f
```

### Restart Server
```bash
docker-compose restart
```

---

## Troubleshooting

### Server won't start
- Check if port 8765 is already in use
- Check `.env` file exists and has OPENAI_API_KEY
- Check Docker is running: `docker ps`

### Code changes not reflecting
- Check volume mounts in docker-compose.yml
- Restart server: `docker-compose restart`

### View container logs
```bash
docker-compose logs backend
```

---

## What's Running

- **Backend:** http://127.0.0.1:8765
- **Container name:** vtc-backend
- **Network:** vtc-network

---

**That's it! One command to start everything.** 🚀

