# CalMap

Nutrition tracker — FastAPI backend, Postgres, and a React Native (Expo) app.

## Running it

Three things need to be running. Each command below goes in its own terminal.
Docker Desktop must be open before you start.

### 1. Database

```powershell
cd C:\Users\raopr\School_Stuff\CalApp
docker compose up -d
```

Runs in the background and stays up until you stop it. You usually only do this once.

### 2. Backend (API)

```powershell
cd C:\Users\raopr\School_Stuff\CalApp\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

This terminal stays busy while the server runs. `Ctrl+C` stops it.

### 3. Frontend (mobile app)

```powershell
cd C:\Users\raopr\School_Stuff\CalApp\mobile-sdk54
npx expo start
```

Scan the QR code with your iPhone camera. Your phone and laptop must be on the same Wi-Fi.

## Checking it works

Open <http://localhost:8000/health> in a browser. You should see:

```json
{ "status": "ok", "database": "connected" }
```

<http://localhost:8000/docs> gives you a page where you can try out the API by hand.

## Stopping

- Backend and frontend: `Ctrl+C` in their terminals
- Database: `docker compose down` (data is kept), or leave it running

## If something breaks

**App says "unreachable"** — the backend isn't running, or your phone is on cellular
instead of Wi-Fi.

**`docker compose up` fails to connect** — Docker Desktop isn't open yet.

**`uvicorn` is not recognized** — the virtual environment isn't active. VS Code usually
activates it for you. To activate it manually:

```powershell
.\.venv\Scripts\Activate.ps1
```

**`ModuleNotFoundError: No module named 'app'`** — you're in the wrong folder. The uvicorn
command has to be run from `backend`.

## First-time setup

Only needed on a fresh machine.

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env

# Frontend
cd ..\mobile-sdk54
npm install
```

Your phone also needs the **Expo Go** app, and Windows Firewall needs to allow ports 8000
and 8081 on your private network:

```powershell
# Run once, in an Administrator PowerShell
New-NetFirewallRule -DisplayName "CalMap dev" -Direction Inbound -Protocol TCP `
  -LocalPort 8000,8081 -Action Allow -Profile Private -RemoteAddress LocalSubnet
```

## Project layout

| Folder | What's in it |
|---|---|
| `backend/` | FastAPI app, database models, migrations |
| `mobile-sdk54/` | Expo app (SDK 54) |
| `docs/` | Design spec |
