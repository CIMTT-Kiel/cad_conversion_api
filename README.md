# CAD Preprocessing API

Microservices zur Vorverarbeitung von CAD-Daten für KI-Anwendungen. Das System besteht aus getrennten Services für: Konvertierung, Rendering, Embedding-Generierung und Analyse.

## 🎯 Features

- **CAD Konvertierung**: STEP, JT, OBJ → STL, PLY, Multiview (angelehnt an Rotationet), 3D-Mesh, Geometrische-Invarianten (nach RudolfKaiser-Paper), 
- **Embedding Generierung**: Vecset nach 3DShapeToVecset(SDF-Ansatz)
- **CAD Analyse**: Extraktion von Geometrie-Merkmalen (Flächen, Volumen, Oberflächentypen, ...)

## 🏗️ Architektur

```
┌─────────────────────────────────────────────┐
│         User Application / Client SDK       │
│         (Python Package im client/ Ordner)  │
└──────────────────┬──────────────────────────┘
                   │
                   │  REST API Calls
                   │
    ┌──────────────┼──────────────┬────────────────┐
    │              │              │                │
    v              v              v                v
┌──────────┐  ┌──────────┐  ┌──────────┐     ┌─────────┐
│Converter │  │ Embedding│  │ Analyser │     │ Docker  │
│ Service  │  │ Service  │  │ Service  │     │ Volumes │
│  :8001   │  │  :8002   │  │  :8003   │     │ (temp)  │
│          │  │  (GPU)   │  │(FreeCAD) │     └─────────┘
└──────────┘  └──────────┘  └──────────┘
     │             │              │
     └─────────────┴──────────────┘
              │
              v
      ┌───────────────┐
      │ Shared Storage│
      │  & Temp Files │
      └───────────────┘
```

## 🚀 Quick Start

### 1. Model Setup (für Embedding-Funktionalität)

```bash
# Erstelle models Verzeichnis
mkdir models

# Kopiere dein VecSet Model Checkpoint
cp /pfad/zu/checkpoint-110.pth models/
```

### 2. Services starten

```bash
# Alle Services mit Docker Compose (empfohlen)
docker compose up --build


## 📁 Projektstruktur

```
cad_conversion_api/
├── README.md                    # Diese Datei
├── docker-compose.yml          # Docker Orchestrierung
│
├── config/                      # Zentrale Konfiguration
│   └── client.yaml             # Client-Konfiguration
│
├── services/                    # Alle Microservices
│   ├── converter_service/       # CAD Konvertierungsservice
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── main.py              # FastAPI Anwendung
│   │   └── src/converter_service/
│   │       └── services/
│   │           └── cad_conversion.py # Konvertierungslogik
│   │
│   ├── embedding_service/       # Embedding Generierungsservice
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── main.py              # FastAPI Anwendung
│   │   └── src/embedding_service/
│   │       ├── models/          # ML Model Definitionen
│   │       │   ├── autoencoder.py
│   │       │   ├── bottleneck.py
│   │       │   └── utils.py
│   │       └── services/
│   │           └── vecset.py    # VecSet Embedding
│   │
│   ├── analyser_service/        # CAD Analyseservice (FreeCAD)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── main.py              # FastAPI Anwendung
│   │   └── src/analyser_service/
│   │       └── cad_stats.py     # FreeCAD Analyselogik
│   │
│   └── rendering_service/       # Rendering Service
│       ├── Dockerfile
│       ├── main.py
│       └── src/rendering_service/
│
├── client/                      # Python Client SDK
│   ├── pyproject.toml
│   └── src/client/
│       └── client.py            # Client Implementation
│
├── models/                      # Model Checkpoints
│   └── checkpoint-110.pth       # VecSet Model (manuell hinzufügen)
│
└── notebooks/                   # Beispiele und Demos
    └── example_usage.ipynb
```

### API-Dokumentation

Jeder Service bietet interaktive API-Dokumentation:

- http://localhost:8001/docs (Converter)
- http://localhost:8002/docs (Embedding)
- http://localhost:8003/docs (Analyser)
- http://localhost:8004/docs (Render)


