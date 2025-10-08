GPP_PCM – Avalanche Simulation Model (Tyrol, Austria):

The GPP_PCM model is a Python-based workflow for simulating the entire avalanche process for different return periods in the Tyrolean Alps. It integrates multiple data sources and submodels, from potential release area detection to runout and flow-path modeling, within a single automated environment.
Developed as part of a Master's thesis, the model combines GIS-based raster processing with physical avalanche dynamics using the Perla–Cheng–McClung (PCM) approach.

Based on:



Key Features
Complete avalanche workflow
From release area and release depth estimation to runout distance and flow path simulation.
Meteorological data integration
Incorporates 72-hour snow depth differences and wind measurements from online APIs for dynamic release and drift-snow modeling.
Snow profile analysis
Utilizes snow profiles from the LAWIS database to represent weak layer fractures and avalanche volume expansion.
Dynamic friction modeling
Continuously adjusts Coulomb friction (μ) and turbulent friction (ξ) based on elevation and avalanche volume.
Friction calibration is aligned with RAMMS friction tables and model volume outputs.
2D flow simulation (PCM-MuXi)
Efficient raster-based propagation of maximum velocity (Vmax) and maximum pressure (Pmax).
Model validation
Compared with AvaFrame, Austrian hazard zone maps, and the original PCMMuXi implementation.
Practical GIS integration
Designed for use in QGIS or SAGA GIS with short computation times and optional real-time data integration.
Model Concept
The GPP_PCM model applies an iterative raster-based flow simulation:
Starting from identified release cells, the script propagates flow downslope using D8 topology.
Each active cell transfers velocity (Vmax) and pressure (Pmax) to lower neighboring cells.
Friction, slope, and relative elevation differences determine the energy transfer.
The process continues until no active flow cells remain, forming a complete flow path (FP).
Post-processing smooths isolated cells and ensures continuity in the resulting rasters.
This approach allows efficient computation of avalanche flow behavior on high-resolution terrain data.
Dependencies
The script runs in a Python GIS environment (recommended: QGIS Python console or standalone execution).
Core libraries

numpy
gdal
osgeo
math
time
Optional (depending on setup)
qgis.core
os
sys
Usage
1. Input Data
Digital Elevation Model (DEM)
Release area raster (potential release zones)
Snow depth data (from API or measurements)
Optional: snow profile dataset (LAWIS)
2. Execution
Run GPP_PCM.py from the QGIS Python console or as a standalone script.
Specify file paths and model parameters (μ, ξ, return period, etc.).
Output rasters include:
Vmax.tif – Maximum flow velocity
Pmax.tif – Maximum dynamic pressure
FP.tif – Flow path extent
3. Post-Processing
Visualize the results in QGIS and compare them with observed avalanche events or hazard zones.
Outputs
Output Raster	Description
Vmax	Maximum velocity (m/s) along the flow path
Pmax	Maximum dynamic pressure (kPa)
FP	Binary raster of the flow path (1 = flow cell)
Validation
Validation was performed through comparisons with:
AvaFrame simulations
RAMMS friction parameters
Austrian hazard zone maps
Results show plausible runout distances and flow path geometries across different return periods.
Limitations
Reduced accuracy for small avalanches in complex terrain
Limited lateral spreading representation
No direct simulation of flow depth
Region of Application
Developed and tested for Tyrol, Austrian Alps, but applicable to other alpine regions with suitable DEM and meteorological data.
Citation
If you use this model or parts of it in your research, please cite:
[Author Name]. (2025). Integration of measurement data and snow profiles into the simulation of potential avalanche release zones and runout lengths – Tyrol, Austria. Master’s Thesis, University of Innsbruck.
Repository Structure
GPP_PCM/
│
├── GPP_PCM.py              # Main model script
├── /data/                  # Example input datasets (DEM, release zones)
├── /output/                # Result rasters (Vmax, Pmax, FP)
└── README.md               # Documentation
Author
[Your Name]
University of Innsbruck – Department of Natural Hazards and Alpine Risk Engineering
Email: [your.email@example.com]
Website: [optional link]
Would you like me to include a short section explaining the parameterization of μ and ξ (e.g., how they vary with volume and altitude)? That would make the README more complete for users who want to reproduce or adapt your model.
