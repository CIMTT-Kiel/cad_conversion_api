# CAD API Client

Python-Client für die CAD Preprocessing API Services.

## 🚀 Installation

```bash
cd client
pip install -e .
# oder mit uv
uv sync
```

## ⚙️ Konfiguration

Der Client unterstützt drei Konfigurationsmethoden (in Prioritätsreihenfolge):

### 1. Config-File (empfohlen)

Erstellen Sie `config.yaml` im client-Verzeichnis:

```yaml
# Server-IP oder Hostname
host: "172.20.0.1"

# Ports (optional, defaults: 8001, 8002, 8003)
ports:
  converter: 8001
  embedding: 8002
  analyser: 8003

# Timeout in Sekunden
timeout: 300
```

Für lokale Overrides können Sie `config.local.yaml` erstellen (wird nicht ins Git committed).

### 2. Umgebungsvariablen

```bash
# .env Datei erstellen
cp .env.example .env

# Bearbeiten
CAD_API_HOST=172.20.0.1
CAD_API_TIMEOUT=300
```

Oder direkt im Terminal:

```bash
export CAD_API_HOST=172.20.0.1
export CAD_CONVERTER_URL=http://172.20.0.1:8001
export CAD_EMBEDDING_URL=http://172.20.0.1:8002
export CAD_ANALYSER_URL=http://172.20.0.1:8003
```

### 3. Direkt im Code

```python
from client import CADConverterClient

# Mit Host-IP (einfachste Methode)
client = CADConverterClient(host="172.20.0.1")

# Oder mit vollständigen URLs
client = CADConverterClient(
    converter_url="http://172.20.0.1:8001",
    embedding_url="http://172.20.0.1:8002",
    analyser_url="http://172.20.0.1:8003"
)
```

## 📖 Verwendung

### Basis-Verwendung mit config.yaml

```python
from client import CADConverterClient

# Client initialisieren (liest config.yaml)
client = CADConverterClient()

# Services prüfen
status = client.get_service_status()
print(status)
```

### CAD-Datei konvertieren

```python
# STL-Konvertierung
stl_file = client.convert_to_stl("model.step", "output.stl")
print(f"STL erstellt: {stl_file}")

# PLY-Konvertierung (Punktwolke)
ply_file = client.convert_to_ply("model.step", "output.ply")
print(f"PLY erstellt: {ply_file}")

# VecSet Embedding generieren
vecset_file = client.convert_to_vecset("model.step", "embedding.npy")
print(f"Embedding erstellt: {vecset_file}")
```

### CAD-Datei analysieren

```python
# Geometrie-Analyse
analysis = client.analyse_cad("model.step")

print(f"Gefundene Flächen: {analysis['total_surfaces']}")
print(f"Gesamtfläche: {analysis['total_area']:.2f}")
print(f"Oberflächentypen: {analysis['surface_type_counts']}")

# Detaillierte Surface-Informationen
for surface in analysis['surfaces']:
    print(f"  - {surface['surface_type']}: {surface['area']:.2f}")
```

### Fehlerbehandlung

```python
from client import CADClientError

try:
    stl_file = client.convert_to_stl("model.step", "output.stl")
except CADClientError as e:
    print(f"Konvertierung fehlgeschlagen: {e}")
```

## 🎯 Beispiele

```bash
# Beispiel-Script ausführen
python example.py
```

## 🔧 Erweiterte Konfiguration

### Mehrere Server-Umgebungen

Erstellen Sie verschiedene Config-Files:

```bash
client/
├── config.yaml              # Default (localhost)
├── config.production.yaml   # Produktions-Server
├── config.development.yaml  # Entwicklungs-Server
```

Verwendung:

```python
# Produktions-Config verwenden
client = CADConverterClient(config_file="config.production.yaml")
```

### Timeout anpassen

```python
# Längerer Timeout für große Dateien
client = CADConverterClient(host="172.20.0.1", timeout=600)
```

### Nur bestimmte Services nutzen

```python
# Nur Converter Service
client = CADConverterClient(
    converter_url="http://172.20.0.1:8001",
    embedding_url=None,  # Nicht nutzen
    analyser_url=None    # Nicht nutzen
)
```

## 📊 API-Referenz

### CADConverterClient

#### `__init__(host=None, converter_url=None, embedding_url=None, analyser_url=None, timeout=None, config_file=None)`

Initialisiert den Client.

**Parameter:**
- `host`: Server-IP oder Hostname
- `converter_url`: Converter Service URL (überschreibt host)
- `embedding_url`: Embedding Service URL (überschreibt host)
- `analyser_url`: Analyser Service URL (überschreibt host)
- `timeout`: Request-Timeout in Sekunden
- `config_file`: Pfad zu Custom-Config-File

#### `convert_to_stl(input_file, output_file=None) -> Path`

Konvertiert CAD-Datei zu STL.

#### `convert_to_ply(input_file, output_file=None) -> Path`

Konvertiert CAD-Datei zu PLY (Punktwolke).

#### `convert_to_vecset(input_file, output_file=None) -> Path`

Generiert VecSet Embedding (.npy).

#### `analyse_cad(input_file) -> Dict`

Analysiert STEP-Datei und gibt Geometrie-Statistiken zurück.

#### `get_service_status() -> Dict`

Prüft Status aller konfigurierten Services.

## 🔍 Troubleshooting

### "Config file not found"

```python
# Prüfe, ob config.yaml existiert
from pathlib import Path
print(Path("config.yaml").exists())

# Verwende absolute Pfade
client = CADConverterClient(config_file="/absolute/path/to/config.yaml")
```

### "Service unreachable"

```bash
# Prüfe, ob Services laufen
curl http://172.20.0.1:8001/health
curl http://172.20.0.1:8002/health
curl http://172.20.0.1:8003/health

# Prüfe Firewall
sudo ufw status
```

### "PyYAML not installed"

```bash
pip install pyyaml
# oder
uv pip install pyyaml
```

## 📝 Beispiel-Output

```python
>>> client = CADConverterClient(host="172.20.0.1")
>>> status = client.get_service_status()
>>> print(status)
{
    'converter_service': {
        'status': 'healthy',
        'url': 'http://172.20.0.1:8001'
    },
    'embedding_service': {
        'status': 'healthy',
        'url': 'http://172.20.0.1:8002'
    },
    'analyser_service': {
        'status': 'healthy',
        'url': 'http://172.20.0.1:8003'
    }
}

>>> analysis = client.analyse_cad("sample.step")
>>> print(analysis['surface_type_counts'])
{
    'Plane': 12,
    'Cylinder': 8,
    'BSpline Surface': 22
}
```

## 📄 License

MIT License
