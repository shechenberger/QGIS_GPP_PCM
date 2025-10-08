GPP_PCM – Avalanche Simulation Model (Tyrol, Austria):

Publication:
Hechenberger, S. (2025): Simulation of Potential Avalanche Release Zones and Runout Lengths in Tyrol
Including Optional Integration of Real-Time Weather Data and LAWIS Snow Profiles - Master’s Thesis, University of Innsbruck.

The GPP_PCM model is a Python-based workflow for simulating the entire avalanche process for different return periods in the Tyrolean Alps. It integrates multiple data sources and submodels, from potential release area detection to runout and flow-path modeling, within a single automated environment.
Developed as part of a Master's thesis, the model combines GIS-based raster processing with physical avalanche dynamics using the Perla–Cheng–McClung (PCM) approach.

Based on:
WICHMANN, V. (2017). The Gravitational Process Path (GPP) model (v1.0) – a GIS-based simulation framework for gravitational processes. Geoscientific Model Development, 10, S. 3309–3327.

VEITINGER, J., PURVES, R.S., & SOVILLA, B. (2016): Potential slab avalanche release area identification from estimated winter terrain: a multi-scale, fuzzy logic approach. In: Natural Hazards and Earth System Sciences, 16, S. 2211–2225.

MAGGIONI, M., & GRUBER, U. (2003): The influence of topographic parameters on avalanche release dimension and frequency. In: Cold Regions Science and Technology, 37, S. 407–419.

Key Features:
Complete avalanche workflow -> From release area and release depth estimation to runout distance and flow path simulation.
Meteorological data integration -> Incorporates 72-hour snow depth differences and wind measurements from online APIs 
Snow profile analysis -> Utilizes snow profiles from the LAWIS database to represent weak layer fractures and avalanche volume expansion.
Dynamic friction modeling -> Continuously adjusts Coulomb friction (μ) and turbulent friction (ξ) based on elevation and avalanche volume.
Model validation -> Compared with AvaFrame, Austrian hazard zone maps, and the original PCMMuXi implementation.
Practical GIS integration -> Designed for use in QGIS or SAGA GIS with short computation times and optional real-time data integration.
Dependencies -> The script runs in a Python Q-GIS environment (3.22.5-Białowieża).
Validation -> AvaFrame simulations, Austrian hazard zone maps; Results show plausible runout distances and flow path geometries across different return periods.

1. Input Data
Area of Interest from Digital Elevation Model Tirol (DEM 5m or 10m resolution).

3. Execution
Check dependencies and file paths.
Run GPP_PCM.py from the QGIS Python console.
Choose Parameter settings.

4. Outputs
Vmax	Maximum velocity (m/s) along the flow path
Pmax	Maximum dynamic pressure (kPa)
PRA.shp (potential release area)
Snow depth data (3 day snow max. or from meassurement from API)
LAWIS snow profile dataset 
