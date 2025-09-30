# CAD Preprocessing Service

Ein robuster Service zur Konvertierung von CAD-Dateien in verschiedene Formate für Machine Learning Pipelines. Der Service besteht aus zwei Microservices: einem CAD-Konvertierungsservice und einem VecSet-Encodierungsservice.

## 🎯 Features

- **CAD zu STL**: Konvertierung von STEP, JT, OBJ → STL
- **CAD zu PLY**: Generierung von Punktwolken mit 8192 Punkten
- **CAD zu VecSet**: Deep Learning basierte Vektorrepräsentation (1024x32)
- **Robuste Fehlerbehandlung**: Detaillierte Fehlermeldungen und Logging
- **Einfache REST API**: Intuitive Endpoints für alle Konvertierungen
- **Python Client SDK**: Einfache Integration in bestehende Workflows
- **Docker Support**: Containerisierte Services mit Non-Root-Usern

## 🏗️ Architektur

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client SDK    │ -> │  CAD Service    │ -> │ VecSet Service  │
│                 │    │  (Port 8001)    │    │  (Port 8001)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Model Setup (für VecSet-Funktionalität)

```bash
# Erstelle models Verzeichnis
mkdir models

# Kopiere dein VecSet Model Checkpoint
cp /pfad/zu/checkpoint-110.pth models/
```

### 2. Services starten

```bash
# Mit Docker Compose (empfohlen)
docker-compose up --build

# Oder einzeln für Development
cd cad_service && python main.py &
cd vecset_service && python main.py &
```

### 3. Service testen

```bash
# Health Check
curl http://localhost:8001/health
curl http://localhost:8000/health

# Beispiel-Konvertierung
curl -X POST \
  -F "file=@beispiel.stl" \
  -F "target_format=ply" \
  http://localhost:8001/convert
```

## 📦 Installation

### Voraussetzungen

- **Docker & Docker Compose** (empfohlen)
- **Python 3.11+** (für lokale Entwicklung)
- **CUDA GPU** (optional, für VecSet-Beschleunigung)

### Mit Docker (Empfohlen)

```bash
git clone <repository>
cd cad-preprocessing-service

# Model platzieren
mkdir models
cp checkpoint-110.pth models/

# Services starten
docker-compose up --build
```

### Lokale Entwicklung

```bash
# CAD Service
cd cad_service
pip install -e .
python main.py

# VecSet Service  
cd vecset_service
pip install -e .
python main.py
```

## 🐍 Python Client

### Installation

```python
# Client ist im Repository enthalten
from client import CADConverterClient
```

### Verwendung

```python
from client import CADConverterClient

# Client initialisieren
client = CADConverterClient(
    cad_url="http://localhost:8001",
    vecset_url="http://localhost:8000"  # Optional
)

# Verschiedene Konvertierungen
try:
    # STL Konvertierung
    stl_file = client.convert_to_stl("eingabe.step", "ausgabe.stl")
    print(f"STL erstellt: {stl_file}")
    
    # PLY Konvertierung  
    ply_file = client.convert_to_ply("eingabe.step", "ausgabe.ply")
    print(f"PLY erstellt: {ply_file}")
    
    # VecSet Konvertierung
    vecset_file = client.convert_to_vecset(
        "eingabe.step", 
        "ausgabe.npy",
        export_reconstruction=True  # Optional: STL Rekonstruktion
    )
    print(f"VecSet erstellt: {vecset_file}")
    
except CADClientError as e:
    print(f"Konvertierung fehlgeschlagen: {e}")

# Service Status prüfen
status = client.get_service_status()
print(f"Services: {status}")
```

## 🔧 API Reference

### CAD Service (Port 8001)

#### `POST /convert`
Konvertiert CAD-Dateien in verschiedene Formate.

**Parameter:**
- `file` (FormData): CAD-Datei (STEP, STP, JT, OBJ, STL)
- `target_format` (FormData): Zielformat (`stl`, `ply`, `vecset`)

**Response:**
```json
{
  "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
  "target_format": "stl",
  "file": "/tmp/output.stl", 
  "status": "completed"
}
```

**Fehler:**
- `400`: Ungültiges Format oder Datei
- `500`: Konvertierungsfehler

#### `GET /health`
Service-Gesundheitsstatus.

**Response:**
```json
{
  "status": "healthy",
  "service": "cad-converter"
}
```

### VecSet Service (Port 8000)

#### `POST /vecset`
Konvertiert PLY-Dateien zu VecSet-Repräsentation.

**Parameter:**
- `file` (FormData): PLY-Datei mit Punktwolke
- `export_reconstruction` (FormData, optional): Rekonstruktion als STL exportieren

**Response:**
```json
{
  "conversion_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "file": "/tmp/output.npy",
  "metadata": {
    "shape": [1024, 32],
    "dtype": "float32",
    "point_count": 8192
  }
}
```

## 📁 Projektstruktur

```
cad-preprocessing-service/
├── README.md                    # Diese Datei
├── docker-compose.yml          # Docker Orchestrierung
│
├── cad_service/                 # CAD Konvertierungsservice
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── main.py                  # FastAPI Anwendung
│   └── src/cad_service/
│       └── services/
│           └── cad_conversion.py # Konvertierungslogik
│
├── vecset_service/              # VecSet Encodierungsservice  
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── main.py                  # FastAPI Anwendung
│   └── src/vecset_service/
│       ├── models/              # ML Model Definitionen
│       │   ├── autoencoder.py
│       │   ├── bottleneck.py
│       │   └── utils.py
│       └── services/
│           └── vecset.py        # VecSet Konvertierung
│
├── client/                      # Python Client SDK
│   ├── __init__.py
│   └── client.py               # Client Implementation
│
├── models/                     # Model Checkpoints
│   └── checkpoint-110.pth     # VecSet Model (manuell hinzufügen)
│
└── notebooks/                  # Beispiele und Demos
    └── example_usage.ipynb
```

## ⚙️ Konfiguration

### Umgebungsvariablen

```bash
# CAD Service
CAD_LOG_LEVEL=INFO                    # Logging Level
CAD_MAX_FILE_SIZE_MB=100             # Max. Dateigröße

# VecSet Service  
VECSET_LOG_LEVEL=INFO                # Logging Level
CUDA_VISIBLE_DEVICES=0               # GPU Auswahl
```

### GPU-Unterstützung aktivieren

In `docker-compose.yml` auskommentieren:

```yaml
vecset-service:
  # ...
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

## 🔍 Troubleshooting

### Häufige Probleme

#### Model nicht gefunden
```
VecSetError: Model not found. Tried: [...]
```
**Lösung:** VecSet Model Checkpoint in `models/checkpoint-110.pth` platzieren.

#### CUDA Fehler
```
CUDA out of memory
```
**Lösungen:**
- GPU-Unterstützung in Docker aktivieren
- Kleinere Dateien verwenden
- CPU-Modus nutzen (automatischer Fallback)

#### Konvertierung fehlgeschlagen
```
CADConversionError: STL conversion failed
```
**Lösung:** Logs prüfen und Dateiformat validieren:
```bash
docker-compose logs cad-service
```

#### Service nicht erreichbar
```
CADClientError: CAD service not accessible
```
**Lösungen:**
- Services status prüfen: `docker-compose ps`
- Ports prüfen: `netstat -tlnp | grep 800`
- Services neustarten: `docker-compose restart`

### Debug-Modus

```bash
# Detaillierte Logs aktivieren
export CAD_LOG_LEVEL=DEBUG
export VECSET_LOG_LEVEL=DEBUG

# Services mit Logs starten
docker-compose up --build
```

### Performance-Tipps

1. **GPU nutzen**: Aktiviere CUDA für VecSet (10x schneller)
2. **SSD Storage**: Nutze SSD für bessere I/O Performance
3. **Memory**: Mehr RAM für große CAD-Dateien
4. **Batch Processing**: Mehrere Dateien nacheinander verarbeiten

## 🔒 Sicherheit

- **Non-Root Container**: Services laufen als `appuser` (UID 1000)
- **Input Validation**: Dateiformate und -größen werden validiert
- **Error Handling**: Keine sensiblen Daten in Logs
- **Temporary Files**: Automatische Bereinigung nach Verarbeitung

## 📊 Performance

### Typische Verarbeitungszeiten

| Dateiformat | Größe | CAD→STL | CAD→PLY | CAD→VecSet | Hardware |
|-------------|-------|---------|---------|------------|----------|
| STEP        | 10MB  | 2-5s    | 3-7s    | 15-30s (GPU) | 4 CPU cores, RTX 3080 |
| STL         | 50MB  | <1s     | 2-4s    | 10-20s (GPU) | 4 CPU cores, RTX 3080 |
| OBJ         | 25MB  | 1-3s    | 2-5s    | 12-25s (GPU) | 4 CPU cores, RTX 3080 |

*CPU-Modus ist ca. 10x langsamer für VecSet-Konvertierungen.*

## 🤝 Development

### Setup für Entwicklung

```bash
# Repository klonen
git clone <repository>
cd cad-preprocessing-service

# Dependencies installieren
cd cad_service && pip install -e .
cd ../vecset_service && pip install -e .

# Services einzeln starten
python cad_service/main.py &
python vecset_service/main.py &
```

### Code-Qualität

```bash
# Linting
flake8 cad_service/ vecset_service/ client/

# Type Checking
mypy cad_service/ vecset_service/ client/

# Tests (falls vorhanden)
pytest tests/
```

## 📝 Changelog

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