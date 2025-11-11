# CAD Preprocessing API

Eine robuste Microservice-Architektur zur Vorverarbeitung von CAD-Daten für KI-Anwendungen. Das System besteht aus drei spezialisierten Services: Konvertierung, Embedding-Generierung und Analyse.

## 🎯 Features

- **CAD Konvertierung**: STEP, JT, OBJ → STL, PLY
- **Embedding Generierung**: Deep Learning basierte Vektorrepräsentation (1024x32) mit GPU-Support
- **CAD Analyse**: Automatische Extraktion von Geometrie-Statistiken (Flächen, Volumen, Oberflächentypen)
- **Robuste Fehlerbehandlung**: Detaillierte Fehlermeldungen und strukturiertes Logging
- **REST API**: Intuitive Endpoints für alle Funktionen
- **Python Client SDK**: Einfache Integration in bestehende Workflows
- **Docker Support**: Containerisierte Services mit Non-Root-Usern und GPU-Support

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

**Erklärung:**
- **Client SDK**: Python-Bibliothek für einfache API-Nutzung (optional)
- **3 Microservices**: Unabhängige Docker-Container mit spezifischen Aufgaben
- **REST APIs**: Jeder Service bietet eigene HTTP-Endpoints
- **Shared Storage**: Temporäre Dateien für Konvertierungen

## 🎨 Services im Detail

### Converter Service (Port 8001)
Konvertiert CAD-Dateien zwischen verschiedenen Formaten.

**Unterstützte Formate:**
- Input: STEP (.step, .stp), JT (.jt), OBJ (.obj), STL (.stl)
- Output: STL (Mesh), PLY (Punktwolke)

**Technologie:**
- Python 3.11
- Open3D für Mesh-Verarbeitung
- CascadIO für STEP/JT Import
- Trimesh für Format-Konvertierung

**Use Cases:**
- CAD → 3D-Druck (STL)
- CAD → Punktwolke für ML (PLY)
- Format-Normalisierung

---

### Embedding Service (Port 8002)
Generiert Deep Learning Embeddings aus 3D-Geometrien.

**Funktionen:**
- VecSet Autoencoder (1024x32 Embedding)
- GPU-Beschleunigung (CUDA)
- Optional: Mesh-Rekonstruktion

**Technologie:**
- PyTorch
- CUDA 12.1
- Custom Autoencoder-Architektur
- Point Cloud Sampling (8192 Punkte)

**Use Cases:**
- 3D-Ähnlichkeitssuche
- Feature Extraction für ML
- Geometrie-Clustering
- CAD-Retrieval Systeme

---

### Analyser Service (Port 8003)
Analysiert CAD-Geometrien und extrahiert Statistiken.

**Funktionen:**
- Oberflächentyp-Erkennung (Ebene, Zylinder, BSpline, etc.)
- Flächenberechnung
- Schwerpunkt-Bestimmung
- Geometrie-Zusammenfassung

**Technologie:**
- FreeCAD 0.20.2 (headless)
- Python 3.11
- OpenCASCADE Kernel

**Use Cases:**
- Automatische Geometrie-Klassifizierung
- CAD-Qualitätsprüfung
- Feature-Extraktion für Fertigung
- Geometrie-basierte Kostenschätzung

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

# Oder einzeln für Development
cd services/converter_service && uv run python main.py &
cd services/embedding_service && uv run python main.py &
cd services/analyser_service && uv run python main.py &
```

### 3. Services testen

```bash
# Health Checks
curl http://localhost:8001/health  # Converter Service
curl http://localhost:8002/health  # Embedding Service
curl http://localhost:8003/health  # Analyser Service

# Beispiel: CAD-Datei konvertieren
curl -X POST \
  -F "file=@beispiel.step" \
  -F "target_format=stl" \
  http://localhost:8001/convert

# Beispiel: CAD-Datei analysieren
curl -X POST \
  -F "file=@beispiel.step" \
  http://localhost:8003/analyse
```

## 📦 Installation

### Voraussetzungen

- **Docker & Docker Compose** (empfohlen)
- **Python 3.11+** (für lokale Entwicklung)
- **uv** (schneller Python Package Manager)
- **CUDA GPU** (optional, für Embedding-Beschleunigung)
- **FreeCAD Python3** (automatisch im Analyser-Container installiert)

### Mit Docker (Empfohlen)

```bash
git clone <repository>
cd cad_conversion_api

# Model platzieren
mkdir models
cp checkpoint-110.pth models/

# Alle Services starten
docker compose up --build

# Oder einzelne Services starten
docker compose up --build converter-service
docker compose up --build embedding-service
docker compose up --build analyser-service
```

### Lokale Entwicklung

```bash
# uv installieren (falls nicht vorhanden)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Converter Service
cd services/converter_service
uv sync
uv run python main.py

# Embedding Service
cd services/embedding_service
uv sync
uv run python main.py

# Analyser Service
cd services/analyser_service
uv sync
# FreeCAD muss separat installiert werden
sudo apt-get install freecad-python3
uv run python main.py
```

## 🐍 Python Client

### Installation

```bash
cd client
uv sync
```

### Verwendung

```python
from client import CADConverterClient

# Client initialisieren
client = CADConverterClient(
    converter_url="http://localhost:8001",
    embedding_url="http://localhost:8002",
    analyser_url="http://localhost:8003"
)

# Verschiedene Operationen
try:
    # STL Konvertierung
    stl_file = client.convert_to_stl("eingabe.step", "ausgabe.stl")
    print(f"STL erstellt: {stl_file}")

    # PLY Konvertierung
    ply_file = client.convert_to_ply("eingabe.step", "ausgabe.ply")
    print(f"PLY erstellt: {ply_file}")

    # Embedding Generierung
    embedding_file = client.convert_to_embedding(
        "eingabe.step",
        "ausgabe.npy",
        export_reconstruction=True  # Optional: STL Rekonstruktion
    )
    print(f"Embedding erstellt: {embedding_file}")

    # CAD-Analyse
    analysis = client.analyse_cad("eingabe.step")
    print(f"Gefundene Flächen: {analysis['total_surfaces']}")
    print(f"Gesamtfläche: {analysis['total_area']:.2f}")
    print(f"Oberflächentypen: {analysis['surface_type_counts']}")

except Exception as e:
    print(f"Operation fehlgeschlagen: {e}")

# Service Status prüfen
status = client.get_service_status()
print(f"Services: {status}")
```

## 🔧 API Reference

### Converter Service (Port 8001)

#### `POST /convert`
Konvertiert CAD-Dateien in verschiedene Formate.

**Parameter:**
- `file` (FormData): CAD-Datei (STEP, STP, JT, OBJ, STL)
- `target_format` (FormData): Zielformat (`stl`, `ply`)

**Response:**
```
Binary file (STL/PLY)
```

**Fehler:**
- `400`: Ungültiges Format oder Datei
- `500`: Konvertierungsfehler

**Beispiel:**
```bash
curl -X POST \
  -F "file=@model.step" \
  -F "target_format=stl" \
  http://localhost:8001/convert \
  -o output.stl
```

#### `GET /health`
Service-Gesundheitsstatus.

**Response:**
```json
{
  "status": "healthy",
  "service": "cad-converter"
}
```

---

### Embedding Service (Port 8002)

#### `POST /vecset`
Generiert Deep Learning Embeddings aus PLY-Dateien.

**Parameter:**
- `file` (FormData): PLY-Datei mit Punktwolke
- `export_reconstruction` (FormData, optional): Rekonstruktion als STL exportieren

**Response:**
```
Binary file (NumPy .npy format)
Shape: (1024, 32)
```

**Fehler:**
- `400`: Ungültige PLY-Datei
- `500`: Model-Fehler

**Beispiel:**
```bash
curl -X POST \
  -F "file=@pointcloud.ply" \
  http://localhost:8002/vecset \
  -o embedding.npy
```

#### `GET /health`
Service-Gesundheitsstatus.

**Response:**
```json
{
  "status": "healthy",
  "service": "embedding-generator"
}
```

---

### Analyser Service (Port 8003)

#### `POST /analyse`
Analysiert STEP-Dateien und extrahiert Geometrie-Statistiken.

**Parameter:**
- `file` (FormData): STEP-Datei (.step, .stp)

**Response:**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "model.step",
  "total_surfaces": 42,
  "total_area": 1250.67,
  "surface_type_counts": {
    "Plane": 12,
    "Cylinder": 8,
    "BSpline Surface": 22
  },
  "surfaces": [
    {
      "object_name": "Shape",
      "face_index": 0,
      "surface_type": "Plane",
      "area": 100.5,
      "center_of_mass": [10.0, 20.0, 5.0]
    }
  ]
}
```

**Fehler:**
- `400`: Ungültige STEP-Datei
- `500`: FreeCAD Analysefehler

**Beispiel:**
```bash
curl -X POST \
  -F "file=@model.step" \
  http://localhost:8003/analyse \
  | jq .
```

#### `GET /health`
Service-Gesundheitsstatus.

**Response:**
```json
{
  "status": "healthy",
  "service": "cad-analyser"
}
```

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

## ⚙️ Konfiguration

### Umgebungsvariablen

```bash
# Converter Service
LOG_LEVEL=INFO                       # Logging Level
MAX_FILE_SIZE_MB=100                 # Max. Dateigröße

# Embedding Service
LOG_LEVEL=INFO                       # Logging Level
CUDA_VISIBLE_DEVICES=0               # GPU Auswahl
MODEL_PATH=/models/checkpoint-110.pth

# Analyser Service
LOG_LEVEL=INFO                       # Logging Level
PYTHONPATH=/usr/lib/freecad-python3/lib
```

### GPU-Unterstützung

GPU-Support ist bereits in `docker-compose.yml` für den Embedding Service konfiguriert:

```yaml
embedding-service:
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

**Voraussetzungen:**
- NVIDIA GPU
- NVIDIA Docker Runtime installiert
- CUDA-kompatible GPU-Treiber

## 🔍 Troubleshooting

### Häufige Probleme

#### Model nicht gefunden (Embedding Service)
```
Model not found at: /models/checkpoint-110.pth
```
**Lösung:** Model Checkpoint in `models/checkpoint-110.pth` platzieren.

#### FreeCAD Import Fehler (Analyser Service)
```
ModuleNotFoundError: No module named 'FreeCAD'
```
**Lösung:**
- Bei Docker: Container neu builden
- Lokal: `sudo apt-get install freecad-python3`
- PYTHONPATH prüfen

#### CUDA Fehler
```
CUDA out of memory
```
**Lösungen:**
- GPU-Unterstützung in Docker prüfen
- Kleinere Dateien verwenden
- CPU-Modus nutzen (automatischer Fallback)

#### Konvertierung fehlgeschlagen
```
Conversion failed: STL conversion failed
```
**Lösung:** Logs prüfen und Dateiformat validieren:
```bash
docker compose logs converter-service
docker compose logs embedding-service
docker compose logs analyser-service
```

#### Service nicht erreichbar
```
Connection refused
```
**Lösungen:**
- Services status prüfen: `docker compose ps`
- Ports prüfen: `netstat -tlnp | grep 800`
- Services neustarten: `docker compose restart`

### Debug-Modus

```bash
# Detaillierte Logs aktivieren
export LOG_LEVEL=DEBUG

# Services mit Logs starten
docker compose up --build

# Logs einzelner Services anzeigen
docker compose logs -f converter-service
docker compose logs -f embedding-service
docker compose logs -f analyser-service
```

### Performance-Tipps

1. **GPU nutzen**: CUDA für Embedding Service (10x schneller)
2. **SSD Storage**: SSD für bessere I/O Performance
3. **Memory**: Mindestens 8GB RAM für große CAD-Dateien
4. **Batch Processing**: Client SDK für mehrere Dateien nutzen
5. **uv verwenden**: Schnelleres Dependency Management

## 🔒 Sicherheit

- **Non-Root Container**: Services laufen als `appuser` (UID 1000)
- **Input Validation**: Dateiformate und -größen werden validiert
- **Error Handling**: Keine sensiblen Daten in Logs
- **Temporary Files**: Automatische Bereinigung nach Verarbeitung

## 📊 Performance

### Typische Verarbeitungszeiten

| Dateiformat | Größe | Converter | Embedding | Analyser | Hardware |
|-------------|-------|-----------|-----------|----------|----------|
| STEP        | 10MB  | 2-5s (STL)<br>3-7s (PLY) | 15-30s (GPU) | 5-10s | 4 CPU cores, RTX 3080 |
| STL         | 50MB  | <1s (copy)<br>2-4s (PLY) | 10-20s (GPU) | - | 4 CPU cores, RTX 3080 |
| OBJ         | 25MB  | 1-3s (STL)<br>2-5s (PLY) | 12-25s (GPU) | - | 4 CPU cores, RTX 3080 |

**Hinweise:**
- CPU-Modus ist ca. 10x langsamer für Embedding-Generierung
- Analyser Service benötigt STEP-Dateien
- Performance variiert je nach Komplexität der Geometrie

## 🤝 Development

### Setup für Entwicklung

```bash
# Repository klonen
git clone <repository>
cd cad_conversion_api

# uv installieren
curl -LsSf https://astral.sh/uv/install.sh | sh

# Services separat entwickeln
cd services/converter_service
uv sync
uv run python main.py

cd ../embedding_service
uv sync
uv run python main.py

cd ../analyser_service
uv sync
# FreeCAD muss separat installiert sein
uv run python main.py
```

### Service-URLs im Development

- Converter: http://localhost:8001
- Embedding: http://localhost:8002
- Analyser: http://localhost:8003

### API-Dokumentation

Jeder Service bietet interaktive API-Dokumentation:

- http://localhost:8001/docs (Converter)
- http://localhost:8002/docs (Embedding)
- http://localhost:8003/docs (Analyser)

### Code-Qualität

```bash
# Linting (falls konfiguriert)
ruff check services/ client/

# Type Checking
mypy services/ client/

# Tests (falls vorhanden)
pytest tests/
```

## 📝 Changelog

### Version 2.0.0 (Aktuell)
- ✅ **Drei unabhängige Microservices**: Converter, Embedding, Analyser
- ✅ **Analyser Service**: FreeCAD-basierte Geometrie-Analyse
- ✅ **uv Package Manager**: Schnelleres Dependency Management
- ✅ **Optimierte Docker Images**: Lightweight, headless FreeCAD
- ✅ **Konsistente API**: Alle Services mit FastAPI
- ✅ **Verbesserte Dokumentation**: Vollständige API-Referenz

### Version 1.0.0
- ✅ Robuste Fehlerbehandlung mit Custom Exceptions
- ✅ Englische Code-Dokumentation
- ✅ Non-Root Docker Container
- ✅ Strukturiertes Logging
- ✅ Health Check Endpoints
- ✅ Python Client SDK mit Retry-Logic
- ✅ Input-Validierung und Sanitization

## 📄 License

MIT License - siehe LICENSE Datei für Details.

## 📞 Support

Für Fragen und Support:
- **Issues**: GitHub Issues für Bug Reports
- **Diskussionen**: GitHub Discussions für Fragen
- **Email**: [Support Email falls verfügbar]