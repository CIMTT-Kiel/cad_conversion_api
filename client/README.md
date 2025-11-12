# CAD API Client

Python-Client für die CAD Preprocessing API Services.

## 🚀 Installation

```bash
cd client
uv sync
```

## ⚙️ Konfiguration

Der Client unterstützt drei Konfigurationsmethoden (in Prioritätsreihenfolge):

### 1. Config-File (empfohlen)

Erstellen Sie die Config-Datei im zentralen `/config` Verzeichnis des Projekts:

```bash
# Projekt-Root/config/client.yaml
```

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

Für lokale Overrides können Sie `config/client.local.yaml` erstellen (wird nicht ins Git committed).


### 3. Direkt im Code

```python
from client import CADConverterClient

client = CADConverterClient(host="172.20.0.1")

# Oder mit vollständigen URLs inklusive den Ports
client = CADConverterClient(
    converter_url="http://172.20.0.1:8001",
    embedding_url="http://172.20.0.1:8002",
    analyser_url="http://172.20.0.1:8003"
)
```

## 📖 Verwendung

### mit bestehender config.yaml

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

# VecSet Embedding generieren entsprechend sdf model aus 3DShapeToVecset Paper
vecset_file = client.convert_to_vecset("model.step", "embedding.npy")
print(f"Embedding erstellt: {vecset_file}")

...
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

Verwendung:

```python
# Produktions-Config verwenden
client = CADConverterClient(config_file="config/client.production.yaml")
```

## 📊 API-Referenz - CADConverterClient

**Parameter:**
- `host`: Server-IP oder Hostname
- `converter_url`: Converter Service URL (überschreibt host)
- `embedding_url`: Embedding Service URL (überschreibt host)
- `analyser_url`: Analyser Service URL (überschreibt host)
- `timeout`: Request-Timeout in Sekunden
- `config_file`: Pfad zu Custom-Config-File

#### `convert_to_stl(input_file, output_file=None) -> Path`

Konvertiert CAD-Datei zu 2D Oberflächenvernetzung -> STL.

#### `convert_to_ply(input_file, output_file=None) -> Path`

Konvertiert CAD-Datei zu PLY (Punktwolke).

#### `convert_to_vecset(input_file, output_file=None) -> Path`

Generiert VecSet Embedding (.npy).

#### `to_3D_mesh(input_file, output_file=None) -> Path`

Generiert eine 3D Vernetzung des gegebenen Bauteils. Netz wird mittels gmsh erstellt. Vernetzung komplexer Geometrien und Baugruppen kann zu unerwartetem Verhlten und falils führen. Netze sollten immer geprüft werden.  

#### `to_voxel(input_file, output_file, resolution) -> Path`

Generiet eine Voxel-Repräsentation des Bauteils in ein resolution^3 grid 

#### to_multiview(input_file, output_file, total_imgs, mode) -> Path`

Erstellt gerenderte Ansichten des Bauteils als .png files inklusive Daten zur Kameraposition. Die Ansichten werden Automatisch gleichmäßig um das Bauteil verteilt. total_img gibt an wie viele Bilder erzeugt werden sollen. 

#### to_technical_drawing_views(input_file, output_file) -> Path (.dxf)

Erstellt die drei Standardansichten entsprechend einer technischen Zeichnung. Es ist nur die Geometrie abgebildet, keine Maße. ACHTUNG: Funktioniert nicht zu 100% robust. Teils fehlen zB. einzelne Lininen oder Kreisbögen. 

#### `analyse_cad(input_file) -> Dict`

Analysiert STEP-Datei und gibt Geometrie-Statistiken zurück.

#### `get_service_status() -> Dict`

Prüft Status aller konfigurierten Services.

...
