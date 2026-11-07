# SIM Stock & Sales Tracking Platform

A multi-tenant platform for Safaricom SIM card dealers to track stock from HQ intake through Branch distribution to Brand Ambassador (BA) sale, with reconciliation against Safaricom's daily line-connection reports.

## Architecture

```
Dealer (HQ)
   └── Branch (van / shop / individual)
          └── Brand Ambassador (BA)
```

## Tech Stack

- **Mobile App**: Flutter (Android first, Play Store)
- **Web App**: React + TypeScript (Vite)
- **Backend API**: Python + FastAPI
- **Database**: PostgreSQL 17
- **Background Jobs**: Celery + Redis
- **Object Storage**: S3-compatible
- **Auth**: JWT-based (access + refresh tokens)
- **Deployment**: Docker + Kubernetes (K3s)

## Project Structure

```
SIMCARDS/
├── backend/          # FastAPI backend, Celery workers
├── mobile/           # Flutter mobile app
├── web/              # React web app
├── infra/            # Docker, Kubernetes manifests
├── design.md         # Detailed design document
├── requirements.md   # Functional requirements
├── tasks.md          # Task breakdown by phase
└── README.md         # This file
```

## Development Approach

**Backend-first**: All backend work (Phases 0-10) must be completed before any frontend work begins. The backend gate ensures a solid, testable foundation before mobile and web development.

## Getting Started

See individual directory READMEs for setup instructions:
- `backend/` - Backend API and worker setup
- `mobile/` - Flutter mobile app setup
- `web/` - React web app setup
- `infra/` - Infrastructure and deployment

## Documentation

- `design.md` - Full system design, data model, workflows
- `requirements.md` - Functional requirements, acceptance criteria
- `tasks.md` - Detailed task breakdown by development phase

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
