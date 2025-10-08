## GPP-PCM Avalanchen Simulation

## Hechenberger, S. (2025): 
## Simulation of Potential Avalanche Release Zones and Runout Lengths in Tyrol,
## Including Optional Integration of Real-Time Weather Data and LAWIS Snow Profiles.
## Master’s Thesis, University of Innsbruck.

## Simulaiton potenzielle Lawinenanbruchgebiete und Auslauflängen in Tirol,
## Inklusive der optionalen Integraiton von Echtzeitwetterdaten und LAWIS-Schneeprofilen.

## Bedreut durch Rudolf Sailer, UIBk. 
## Eingereicht Oktober 2025.

## Grundelgende Skripts (von Rudolf Sailer):
## QGIS_REL_gpp_v2.py   -> potenzielle Anbruchgebiete (PRA)
## QGIS_PCM_MuXi.py     -> Fließpfade, max. Velocity, max. Pressure

## Modelleigenschaften:
## 1.Berechnung PRAs basierend auf dem DGM-Tirol 5m oder 10m Auflösung.
## 2.Selektion der Schneehöhenmessung, LAWIS-Schneeprofilen
## 3.Fließpfadsimulation - max. Geschwindikgeit und Spitzendruck (DGM-Tirol 5m oder 10m Auflösung).

#################################################################################
## PREPERATION ##################################################################

## Install imports, set timer and interface 
import time

## Start  timer
Prep_start_time = time.time()
# Add this function to track detailed timing
def log_detail(message, start_time=None):
    current_time = time.time()
    if start_time is not None:
        elapsed = current_time - start_time
        print(f"  {message}: {elapsed:.6f} seconds")
        return current_time
    else:
        return current_time

## system depending imports - check how your system handels this imports
import pip
pip.main(['install','geopy'])
import geopy.distance, numpy as np, osgeo.gdal
import math, os, glob, csv, json, requests, shutil, statistics, rasterio, io, base64, tempfile
import geopandas as gpd
import sys
import re
import os
import shutil

from qgis.analysis import *
from scipy import ndimage
from scipy.ndimage import gaussian_filter
from PyQt5 import QtGui
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
from qgis.core import QgsProject, QgsDistanceArea, QgsFields, QgsField, QgsVectorFileWriter, QgsWkbTypes, QgsCoordinateReferenceSystem, QgsFeature, QgsGeometry, QgsPointXY, QgsCoordinateTransform, QgsLayerTreeGroup, QgsApplication
from qgis.core import QgsDistanceArea, QgsCoordinateReferenceSystem, QgsProject, QgsPointXY
from qgis.PyQt.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout, QPushButton, QComboBox
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QFormLayout, QLineEdit, QLabel, QCheckBox, QHBoxLayout, QPushButton
from PyQt5.QtCore import QDate
from collections.abc import Iterable, Mapping
from qgis.utils import iface
from urllib import response
from statistics import mean
from osgeo import gdal, osr
from rasterio.transform import from_origin
from rasterio.features import geometry_mask
from shapely.geometry import Point

try:
    from osgeo import gdal
except ImportError:
    import gdal
     
try:
    from osgeo import ogr
except ImportError:
    import ogr
    
iface.mainWindow().blockSignals(True)
qfd = QFileDialog()

## Open simulation parts & saving options interface
class Simulation_Saving_Select_Dialog(QDialog):
    def __init__(self, parent=None):
        super(Simulation_Saving_Select_Dialog, self).__init__(parent)
        self.setWindowTitle("Simulation Parts and Saving Options")
        
        ## Main layout 
        layout = QVBoxLayout()
        
        ## First section - Simulation parts
        sim_section_label = QLabel("<b>Choose simulation parts:</b>")
        layout.addWidget(sim_section_label)
        
        ## Simulation options in horizontal layout
        sim_options_layout = QHBoxLayout()
        
        self.run_PRA_PCM = QCheckBox("Run PRA & PCM")
        self.run_PRA = QCheckBox("Only run PRA")
        self.run_PCM = QCheckBox("Only run PCM")
        
        sim_options_layout.addWidget(self.run_PRA_PCM)
        sim_options_layout.addWidget(self.run_PRA)
        sim_options_layout.addWidget(self.run_PCM)
        
        layout.addLayout(sim_options_layout)
        
        ## Add spacing  
        layout.addSpacing(10)
        
        ## Second section - Saving options 
        save_label = QLabel("<b>Choose to create a new folder or overwrite an existing one:</b>")
        layout.addWidget(save_label)
        
        ## Saving options in horizontal layout
        save_layout = QHBoxLayout()
        
        self.make_new_folder_checkbox = QCheckBox("Make New Folder")
        self.overwrite_folder_checkbox = QCheckBox("Overwrite Folder")
        
        save_layout.addWidget(self.make_new_folder_checkbox)
        save_layout.addWidget(self.overwrite_folder_checkbox)
        
        layout.addLayout(save_layout)
        
        ## Add spacing  
        layout.addSpacing(10)
        
        ## Button layout with proper positioning
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        ## Add spacer 
        button_layout.addStretch()
        
        ## Cancel button first
        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumWidth(80)
        cancel_button.setMinimumHeight(25)
        cancel_button.setStyleSheet("QPushButton:focus { outline: none; }")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        ## Run button second
        run_button = QPushButton("Run")
        run_button.setMinimumWidth(80)
        run_button.setMinimumHeight(25)
        run_button.clicked.connect(self.accept)
        run_button.setDefault(True)  # Make it the default button
        run_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        button_layout.addWidget(run_button)
        
        layout.addLayout(button_layout)
        
        ## Set the main layout
        self.setLayout(layout)
        
        ## Connect checkbox handlers
        self.run_PRA.clicked.connect(self.handle_run_PRA)
        self.run_PCM.clicked.connect(self.handle_run_PCM)
        self.run_PRA_PCM.clicked.connect(self.handle_run_PRA_PCM)
        
        self.make_new_folder_checkbox.clicked.connect(self.handle_new_folder_checkbox)
        self.overwrite_folder_checkbox.clicked.connect(self.handle_overwrite_checkbox)
        
        ## Set default selections
        self.run_PRA_PCM.setChecked(True)  
        self.selection = 1  
        self.make_new_folder_checkbox.setChecked(True)  
        self.saving = 1  
    
    def handle_run_PRA_PCM(self):
        self.selection = 1  
        self.run_PRA.setChecked(False)
        self.run_PCM.setChecked(False)
    
    def handle_run_PRA(self):
        self.selection = 2  
        self.run_PRA_PCM.setChecked(False)
        self.run_PCM.setChecked(False)
    
    def handle_run_PCM(self):
        self.selection = 3  
        self.run_PRA.setChecked(False)
        self.run_PRA_PCM.setChecked(False)
    
    def handle_new_folder_checkbox(self):
        self.saving = 1  
        self.overwrite_folder_checkbox.setChecked(False)
        self.make_new_folder_checkbox.setChecked(True)
    
    def handle_overwrite_checkbox(self):
        self.saving = 2  
        self.make_new_folder_checkbox.setChecked(False)
        self.overwrite_folder_checkbox.setChecked(True)

## Create and show the dialog
dialog = Simulation_Saving_Select_Dialog()
result = dialog.exec_()

if result == QDialog.Rejected:
    print("")
    print("PRA/PCM stopped by user")
    print("")
    raise Exception("Script execution stopped by user")

saving_option = dialog.saving
selected_parts = dialog.selection

## Print saving and simulation parts parameters
print("---------------------------------------------------------------")
print("+++ Selected saving options and simulation components +++")

if saving_option == 1:
    print("\tsaving_option \t", saving_option)
    print("\tResults get written to a new folder")
    print("")
else:
    print("\tsaving_option \t", saving_option)
    print("\tExisting resultfolder gets overwritten")
    print("")

if selected_parts == 1:
    print("\tselected_parts \t", selected_parts)
    print("\tPRA and PCM run")
if selected_parts == 2:
    print("\tselected_parts \t", selected_parts)
    print("\tOnly release areas get simulated")
if selected_parts == 3:
    print("\tselected_parts \t", selected_parts)
    print("\tOnly PCM avalanche runout gets simulated")

print("---------------------------------------------------------------")

### Open PRA parameter interface
if selected_parts != 3:
    class PRA_Dialog(QDialog):
        def __init__(self, parent=None):
            super(PRA_Dialog, self).__init__(parent)
            self.setWindowTitle("Release Area Parameters")
            self.setMinimumWidth(450)
            
            ## Default parameter
            self.rp = 150
            self.wind = 0
            self.k = 10
            self.slo_min = 27
            self.slo_max = 55
            self.fac_min = 100
            self.fac_lim = 500
            self.area_min = 3000
            self.s_rad = 2
            self.e_rad = 2
            self.th_sieve = 3

            ## Main layout 
            layout = QVBoxLayout()
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(10)

            ## Parameter group box
            parameter_groupbox = QGroupBox("Choose Parameters for PRA definition:")
            parameter_groupbox.setStyleSheet("QGroupBox { font-weight: bold; }")
            parameter_layout = QFormLayout(parameter_groupbox)
            parameter_layout.setSpacing(8)
            parameter_layout.setContentsMargins(10, 15, 10, 10)
            
            ## Set consistent field width
            field_width = 120

            ## Return Period Dropdown
            self.rp_value = QComboBox()
            self.rp_value.addItems(["150", "30", "100", "300", "72h"])
            self.rp_value.setMinimumWidth(field_width)
            self.rp_value.setToolTip("Return period. '72h' uses 3-day snow accumulation (real-time).")
            parameter_layout.addRow("Return Period (RP):", self.rp_value)
            
            ## Define the wind parameter dropdown
            self.wind_value = QComboBox()
            self.wind_value.addItems(["0", "30", "50", "rtw"])
            self.wind_value.setMinimumWidth(field_width)
            self.wind_value.setToolTip("Wind parameter [m/s]. 'rtw' uses real-time meteorological data for wind speed and direction.")
            parameter_layout.addRow("Wind Parameter (wind):", self.wind_value)

            ## Smoothing Factor
            self.smoothing_value = QLineEdit(str(self.k))
            self.smoothing_value.setMinimumWidth(field_width)
            self.smoothing_value.setToolTip("Enter the smoothing factor [k]. For DTM 5m -> k = 10. For DTM 10m -> k = 7.")
            parameter_layout.addRow("Smoothing Factor (k):", self.smoothing_value)

            ## Slope Limits
            self.slo_min_value = QLineEdit(str(self.slo_min))
            self.slo_min_value.setMinimumWidth(field_width)
            self.slo_min_value.setToolTip("Enter the minimum slope degree for pixel inside PRA; def. 27°.")
            parameter_layout.addRow("Slope Lower Limit (slo_min):", self.slo_min_value)
            
            self.slo_max_value = QLineEdit(str(self.slo_max))
            self.slo_max_value.setMinimumWidth(field_width)
            self.slo_max_value.setToolTip("Enter the maximum slope degree for pixel inside PRA; def. 55°.")
            parameter_layout.addRow("Slope Upper Limit (slo_max):", self.slo_max_value)

            ## Ridge Distance
            self.fac_min_value = QLineEdit(str(self.fac_min))
            self.fac_min_value.setMinimumWidth(field_width)
            self.fac_min_value.setToolTip("Enter the minimum distance [m] to ridge. The effect starts at 100 m and prevents overlapping of simulations.")
            parameter_layout.addRow("Ridgedistance Minimum (fac_min):", self.fac_min_value)
            
            self.fac_lim_value = QLineEdit(str(self.fac_lim))
            self.fac_lim_value.setMinimumWidth(field_width)
            self.fac_lim_value.setToolTip("Enter the maximum distance [m] to ridge. Choose values from 300m to 500m.")
            parameter_layout.addRow("Ridgedistance Maximum (fac_lim):", self.fac_lim_value)

            ## Area Minimum
            self.area_min_value = QLineEdit(str(self.area_min))
            self.area_min_value.setMinimumWidth(field_width)
            self.area_min_value.setToolTip("Enter the PRA-area minimum [m2]; def. 3000.")
            parameter_layout.addRow("PRA Minimum Area (area_min):", self.area_min_value)

            ## Shrink and Expand Radius
            self.s_rad_value = QLineEdit(str(self.s_rad))
            self.s_rad_value.setMinimumWidth(field_width)
            self.s_rad_value.setToolTip("Enter the shrink radius, choose between 1 or 2.")
            parameter_layout.addRow("Shrink Radius (s_rad):", self.s_rad_value)
            
            self.e_rad_value = QLineEdit(str(self.e_rad))
            self.e_rad_value.setMinimumWidth(field_width)
            self.e_rad_value.setToolTip("Enter the expand radius, choose between 2 or 3.")
            parameter_layout.addRow("Expand Radius (e_rad):", self.e_rad_value)

            ## Sieve Threshold
            self.th_sieve_value = QLineEdit(str(self.th_sieve))
            self.th_sieve_value.setMinimumWidth(field_width)
            self.th_sieve_value.setToolTip("Enter the sieve threshold GPP (removes Speckles); Def. 3")
            parameter_layout.addRow("Sieve Threshold GPP (th_sieve):", self.th_sieve_value)

            layout.addWidget(parameter_groupbox)

            ## Button layout with proper positioning
            button_layout = QHBoxLayout()
            button_layout.setSpacing(8)
            
            ## Add spacer to push buttons to the right
            button_layout.addStretch()
            
            ## Cancel button first
            cancel_button = QPushButton("Cancel")
            cancel_button.setMinimumWidth(80)
            cancel_button.setMinimumHeight(25)
            cancel_button.clicked.connect(self.reject)
            button_layout.addWidget(cancel_button)
            
            ## Run button second
            run_button = QPushButton("Run")
            run_button.setMinimumWidth(80)
            run_button.setMinimumHeight(25)
            run_button.clicked.connect(self.accept)
            run_button.setDefault(True)  # Make it the default button
            run_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            button_layout.addWidget(run_button)
            
            layout.addLayout(button_layout)
            
            self.setLayout(layout)

        def accept(self):
            ## Save parameter values
            self.rp = self.rp_value.currentText()
            self.wind = self.wind_value.currentText()
            self.k = int(self.get_value_from_line_edit(self.smoothing_value))
            self.slo_min = int(self.get_value_from_line_edit(self.slo_min_value))
            self.slo_max = int(self.get_value_from_line_edit(self.slo_max_value))
            self.fac_min = int(self.get_value_from_line_edit(self.fac_min_value))
            self.fac_lim = int(self.get_value_from_line_edit(self.fac_lim_value))
            self.area_min = int(self.get_value_from_line_edit(self.area_min_value))
            self.s_rad = int(self.get_value_from_line_edit(self.s_rad_value))
            self.e_rad = int(self.get_value_from_line_edit(self.e_rad_value))
            self.th_sieve = int(self.get_value_from_line_edit(self.th_sieve_value))

            super(PRA_Dialog, self).accept()

        def get_value_from_line_edit(self, line_edit):
            return line_edit.text()

    dialog = PRA_Dialog()
    result = dialog.exec_()

    if result == QDialog.Rejected:
        print("")
        print("PRA/PCM stopped by user")
        print("")
        raise Exception("Script execution stopped by user")
    
    rp = dialog.rp
    wind = dialog.wind
    k = dialog.k
    slo_min = dialog.slo_min
    slo_max = dialog.slo_max
    fac_min = dialog.fac_min
    fac_lim = dialog.fac_lim
    area_min = dialog.area_min
    s_rad = dialog.s_rad
    e_rad = dialog.e_rad
    th_sieve = dialog.th_sieve
    
    ## print PRA simulation parameters
    print("+++ PRA user parameter +++")
    print("\tReturn period (RP)\t\t\t\t\t", dialog.rp)
    print("\t""ind factor (wind)\t\t\t\t\t", dialog.wind)
    print("\tSmothing factor (k)\t\t\t\t\t", dialog.k)
    print("\tSlope Lower Limit (slo_min)\t\t\t", dialog.slo_min)
    print("\tSlope Upper Limit (slo_max)\t\t\t", dialog.slo_max)
    print("\tRidgedistance Minimum (fac_min)\t\t", dialog.fac_min)
    print("\tRidgedistance Maximum (fac_lim)\t\t", dialog.fac_lim)
    print("\tPRA Minimum Area (area_min)\t\t\t", dialog.area_min)
    print("\tShrink Radius (s_rad)\t\t\t\t", dialog.s_rad)
    print("\tExpand Radius (e_rad)\t\t\t\t", dialog.e_rad)
    print("\tSieve Threshold GPP (th_sieve)\t\t", dialog.th_sieve)

    ## Open LAWIS & HYDRO parameter interface
if selected_parts != 3:
    class LawisDataParametersDialog(QDialog):
        def __init__(self, parent=None):
            super(LawisDataParametersDialog, self).__init__(parent)
            self.setWindowTitle("LAWIS / HYDRO Parameters")
            
            ## Get the current date
            current_date = QDate.currentDate()
            
            ## Set default values for start_date and end_date
            self.start_date = QDate(current_date.year(), 1, 1)
            self.end_date = current_date
            self.elevation_range = None
            self.hydro_elevation_range = None
            layout = QVBoxLayout()

            ## Make the header
            main_label = QLabel('<b>Please choose the Parameters for LAWIS - Snowprofile collection</b>')
            layout.addWidget(main_label)
            
            ## Define start date
            start_date_label = QLabel("Start Date:")
            layout.addWidget(start_date_label)

            start_date_layout = QHBoxLayout()
            start_day_combo = QComboBox()
            start_month_combo = QComboBox()
            start_year_combo = QComboBox()

            ## Add items to day, month, and year 
            days = [str(i).zfill(2) for i in range(1, 32)]
            months = [str(i).zfill(2) for i in range(1, 13)]
            years = [str(i) for i in range(2010, 2031)]
            start_day_combo.addItems(days)
            start_month_combo.addItems(months)
            start_year_combo.addItems(years)

            ## Set default values for start date
            start_day_combo.setCurrentIndex(self.start_date.day() - 1)
            start_month_combo.setCurrentIndex(self.start_date.month() - 1)
            start_year_combo.setCurrentIndex(self.start_date.year() - 2010)
            start_date_layout.addWidget(start_day_combo)
            start_date_layout.addWidget(start_month_combo)
            start_date_layout.addWidget(start_year_combo)

            layout.addLayout(start_date_layout)

            ## Define end date
            end_date_label = QLabel("End Date:")
            layout.addWidget(end_date_label)

            end_date_layout = QHBoxLayout()
            end_day_combo = QComboBox()
            end_month_combo = QComboBox()
            end_year_combo = QComboBox()

            end_day_combo.addItems(days)
            end_month_combo.addItems(months)
            end_year_combo.addItems(years)

            ## Set default values for end_date_combos
            end_day_combo.setCurrentIndex(self.end_date.day() - 1)
            end_month_combo.setCurrentIndex(self.end_date.month() - 1)
            end_year_combo.setCurrentIndex(self.end_date.year() - 2010)

            end_date_layout.addWidget(end_day_combo)
            end_date_layout.addWidget(end_month_combo)
            end_date_layout.addWidget(end_year_combo)

            layout.addLayout(end_date_layout)

            ## Create LAWIS Elevation Range (+/-)
            elevation_range_label = QLabel("Elevation Range +/-:")
            layout.addWidget(elevation_range_label)

            elevation_range_combo = QComboBox()
            elevation_values = [str(i) for i in range(500, 49, -50)]
            elevation_range_combo.addItems(elevation_values)
            layout.addWidget(elevation_range_combo)

            ## Create HYDRO section with bold heading
            hydro_label = QLabel('<b>Please choose the Parameters for HYDRO station collection</b>')
            layout.addWidget(hydro_label)

            hydro_elevation_range_label = QLabel("Elevation Range +/-:")
            layout.addWidget(hydro_elevation_range_label)
            
            hydro_elevation_range_combo = QComboBox()
            hydro_elevation_values = [str(i) for i in range(500, 49, -50)]
            hydro_elevation_range_combo.addItems(hydro_elevation_values)
            layout.addWidget(hydro_elevation_range_combo)
            
            ## Button layout with proper positioning
            button_layout = QHBoxLayout()
            button_layout.setSpacing(8)
            
            ## Add spacer to push buttons to the right
            button_layout.addStretch()
            
            ## Cancel button first
            cancel_button = QPushButton("Cancel")
            cancel_button.setMinimumWidth(80)
            cancel_button.setMinimumHeight(25)
            cancel_button.setStyleSheet("QPushButton:focus { outline: none; }")
            cancel_button.clicked.connect(self.reject)
            button_layout.addWidget(cancel_button)
            
            ## OK button
            ok_button = QPushButton("OK")
            ok_button.setMinimumWidth(80)
            ok_button.setMinimumHeight(25)
            ok_button.clicked.connect(self.accept)
            ok_button.setDefault(True)  # Make it the default button
            ok_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
            button_layout.addWidget(ok_button)
            
            layout.addLayout(button_layout)

            self.setLayout(layout)
            self.start_date_combos = (start_day_combo, start_month_combo, start_year_combo)
            self.end_date_combos = (end_day_combo, end_month_combo, end_year_combo)
            self.elevation_range_combo = elevation_range_combo
            self.hydro_elevation_range_combo = hydro_elevation_range_combo
            self.set_default_date_values()

            ## Set default Values
        def set_default_date_values(self):
            ## Set default values for start_date_combos
            self.start_date_combos[0].setCurrentIndex(self.start_date.day() - 1)
            self.start_date_combos[1].setCurrentIndex(self.start_date.month() - 1)
            self.start_date_combos[2].setCurrentIndex(self.start_date.year() - 2010)

            ## Set default values for end_date_combos
            self.end_date_combos[0].setCurrentIndex(self.end_date.day() - 1)
            self.end_date_combos[1].setCurrentIndex(self.end_date.month() - 1)
            self.end_date_combos[2].setCurrentIndex(self.end_date.year() - 2010)

        def accept(self):
            ## Retrieve selected values and store in variables
            start_day = self.start_date_combos[0].currentText()
            start_month = self.start_date_combos[1].currentText()
            start_year = self.start_date_combos[2].currentText()
            self.start_date = QDate(int(start_year), int(start_month), int(start_day))

            end_day = self.end_date_combos[0].currentText()
            end_month = self.end_date_combos[1].currentText()
            end_year = self.end_date_combos[2].currentText()
            self.end_date = QDate(int(end_year), int(end_month), int(end_day))

            self.elevation_range = self.elevation_range_combo.currentText()
            self.hydro_elevation_range = self.hydro_elevation_range_combo.currentText()
            super(LawisDataParametersDialog, self).accept()

    ## Create and show the LAWIS-data dialog
    dialog = LawisDataParametersDialog()
    result = dialog.exec_()

    if result == QDialog.Rejected:
        print("")
        print("PRA/PCM stopped by user")
        print("")
        raise Exception("Script execution stopped by user")

    ## Get selected parameters
    start_date = dialog.start_date.toString("dd.MM.yyyy")
    end_date = dialog.end_date.toString("dd.MM.yyyy")
    elevation_range = dialog.elevation_range
    hydro_elevation_range = dialog.hydro_elevation_range

    print("---------------------------------------------------------------")
    print("+++ LAWIS - HYDRO user parameter +++")
    print("\tStart Date:\t\t\t\t", start_date)
    print("\tEnd Date:\t\t\t\t", end_date)
    print("\tLAWI_Elevation Range:\t", elevation_range)
    print("\tHYDRO_Elevation Range:\t", hydro_elevation_range)
    print("---------------------------------------------------------------")

## Get basic data befor starting PRA or PCM:
lyrs = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
if len(lyrs) == 0:
    print("\n>>> DEM RASTER NEEDS TO BE LOADED! <<<\n")
    title = 'Open DGM'
    path = ''
    f_z = QFileDialog.getOpenFileName(qfd,title,path)
    fileInfo = QFileInfo(f_z[0])
    rLabel = fileInfo.baseName()
    dem = iface.addRasterLayer(f_z[0],rLabel,'gdal')
    
## Check DTM inputlayer and get homepath
dem = iface.activeLayer()

## Check if the selected layer is valid
if dem is not None:
    ## Check if the selected layer is a raster layer
    if dem.type() == QgsMapLayer.RasterLayer:
        print("+++ File information +++")
        print('\nQGIS actives DEM:\t', dem.name())
        
        ## Get the data provider
        if dem:
            data_provider = dem.dataProvider() 
            file_info = data_provider.dataSourceUri()
            aoi_rLabel = os.path.basename(file_info)
            
        ## Set CRS and EXT
        crsSrc = qgis.utils.iface.activeLayer().crs().authid()
        crsSrctxt = crsSrc
        crsSrc = dem.crs()
        QgsProject.instance().setCrs(crsSrc)
        print('CRS: \t\t\t\t',crsSrctxt)
        
        ## Extend
        ext = dem.extent()
        ext = dem.extent().toString()

        ## Create homepath
        infile_z = str(dem.dataProvider().dataSourceUri())
        home_path =  str(os.path.split(infile_z)[0] + "/")
        home_name = os.path.split(infile_z)[1]
        home_path_name = (home_path,home_name)
        f_z = "".join(home_path_name)
        param_string = str("")
        
    else:
        print("Wrong input data, please choose a DEM with 5 or 10 meter resolution")
        pass

else:
    print("No layer selected, please select a layer as input")
    pass
    
##Get rp from PRA if only PCM runs
if selected_parts == 3:
    ## set rp to none
    rp = None
    class PRASelectionDialog(QDialog):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Select PRA Layer")
            self.setLayout(QVBoxLayout())
            
            self.label = QLabel("Please select a PRA layer in the Layers panel.\nOnly polygon layers are allowed.")
            self.layout().addWidget(self.label)
            
            self.select_button = QPushButton("Confirm Selection")
            self.layout().addWidget(self.select_button)
            
            self.select_button.clicked.connect(self.check_layer)
            self.show()

        def check_layer(self):
            ## Ensure rp is assigned globally
            global rp
            
            layer = iface.activeLayer()
            if not layer:
                self.label.setText("No layer selected. Please select a layer.")
                return
            if layer.geometryType() != QgsWkbTypes.PolygonGeometry:
                self.label.setText("Invalid layer! Select a polygon layer.")
                return

            ## Get file path
            source_path = layer.source()

            ## Extract rp value
            match = re.search(r'D(\d+)', source_path)
            if match:
                rp = int(match.group(1))
                iface.messageBar().pushMessage("PRA Selected", f"Layer valid. rp = {rp}", level=Qgis.Success)
                print(f"Extracted rp: {rp}")  # Debugging
                self.accept()  # Close the dialog
            else:
                self.label.setText("D value not found in file path.")

    ## Run the dialog and wait for selection
    dialog = PRASelectionDialog()
    dialog.exec_()  # Ensure the script waits for user input

    if rp is None:
        print("Error: No valid PRA layer selected. Exiting script.")
    else:
        print(f"Proceeding with rp = {rp}")
    
    ## Function for creating new working directory
    def create_new_folder(prefix):
        i = 0
        while True:
            new_folder_path = os.path.join(home_path, f"{prefix}_{dem.name()}_{i}_D{rp}_{wind}")
            if not os.path.exists(new_folder_path):
                print(f"\nCurrent {prefix} Folder:")
                print(new_folder_path)
                os.makedirs(new_folder_path)
                return new_folder_path
            i += 1

    ## Function for overwriting current working directory
    def overwrite_existing_folder(prefix):
        parent_dir = os.path.dirname(home_path)
        folders = [f for f in os.listdir(parent_dir) if f.startswith(f"{prefix}_{dem.name()}_") and f.split("_")[-1].isdigit()]
        if folders:
            folders.sort(key=lambda x: int(x.split("_")[-1]), reverse=True)  # Sort by the numeric part
            last_folder_number = int(folders[0].split("_")[-1])
            folder_to_delete = os.path.join(parent_dir, folders[0])
            print(f"Deleting data from previous {prefix} folder:")
            print(folder_to_delete)
            print("")
            shutil.rmtree(folder_to_delete)
            new_folder_number = last_folder_number
        else:
            print(f"No existing {prefix} folder found.")
            new_folder_number = 1

        new_folder_path = os.path.join(parent_dir, f"{prefix}_{dem.name()}_{new_folder_number}")
        print("New results will be written to the following folder:")
        print(new_folder_path)
        os.makedirs(new_folder_path)
        return new_folder_path
    
## Create new directory or overwrite existing ############################
## Function for creating new working directory
def create_new_folder(prefix):
    i = 0
    while True:
        if wind == 30 or wind == 50:
            new_folder_path = os.path.join(home_path, f"{prefix}_{dem.name()}_{i}_D{rp}_w{wind}")
        elif wind == "rtw":
            new_folder_path = os.path.join(home_path, f"{prefix}_{dem.name()}_{i}_D{rp}_{wind}")
        else:
            new_folder_path = os.path.join(home_path, f"{prefix}_{dem.name()}_{i}_D{rp}")

        if not os.path.exists(new_folder_path):
            print(f"\nCurrent {prefix} Folder:")
            print(new_folder_path)
            os.makedirs(new_folder_path)
            return new_folder_path
        i += 1

## Function for overwriting current working directory
def overwrite_existing_folder(prefix):
    parent_dir = os.path.dirname(home_path)
    folders = [f for f in os.listdir(parent_dir) if f.startswith(f"{prefix}_{dem.name()}_") and f.split("_")[-1].isdigit()]
    if folders:
        folders.sort(key=lambda x: int(x.split("_")[-1]), reverse=True)  # Sort by the numeric part
        last_folder_number = int(folders[0].split("_")[-1])
        folder_to_delete = os.path.join(parent_dir, folders[0])
        print(f"Deleting data from previous {prefix} folder:")
        print(folder_to_delete)
        print("")
        shutil.rmtree(folder_to_delete)
        new_folder_number = last_folder_number
    else:
        print(f"No existing {prefix} folder found.")
        new_folder_number = 1
    
    new_folder_path = os.path.join(parent_dir, f"{prefix}_{dem.name()}_{new_folder_number}")
    print("New results will be written to the following folder:")
    print(new_folder_path)
    os.makedirs(new_folder_path)
    return new_folder_path

## Find DEM in Group to get RELEAS AREA Nr.
def find_group_for_file(infile_z):
    root = QgsProject.instance().layerTreeRoot()
    groups = root.children()

    for group in groups:
        for child_node in group.children():
            if isinstance(child_node, QgsLayerTreeLayer):
                layer = child_node.layer()
                if layer is not None and layer.source() == infile_z:
                    group_name_parts = group.name().split(":")
                    group_name = group_name_parts[-1].strip()
                    return group_name

    return "File not found in any group"
    
## End prep. time 
Prep_end_time  = time.time()

### trace_value function for second code
#def trace_value(row, col, value):
#    with open("/Users/simonhechenberger/Desktop/Masterarbeit_GIS/Untersuchungsgebiete/Galtür/Simulationen/vb1_vb0.txt", "a") as f:
#        f.write(f"Cell [{row},{col}]: {value}\n")
#        
### trace_value function for second code
#def trace_value_V1(row, col, value):
#    with open("/Users/simonhechenberger/Desktop/Masterarbeit_GIS/Untersuchungsgebiete/Galtür/Simulationen/depo.txt", "a") as f:
#        f.write(f"Cell [{row},{col}]: {value}\n")




#def trace_step(message):
#    global trace_step_counter
#    trace_step_counter += 1
#    with open("/Users/simonhechenberger/Desktop/Masterarbeit_GIS/Untersuchungsgebiete/Galtür/infinity_check.txt", "a") as f:
#        f.write(f"Step {trace_step_counter}: {message}\n")
#                
################################################################################
## B. Function for calculating potential release areas ########################
###############################################################################
##trace_step_counter = 0

class SimulationData:
    def __init__(self):
        self.kPa_b0_list = []
        self.Vb1_list = []
        self.Vb0_list = []
        self.crowcol = []

sim_data = SimulationData()

def run_script(script_type, folder_path):
    ## Start PRA_timer
    PRA_start_time = time.time()
    
    ## Ensure function is able to redrive values, use global variable
    global rp
    global wind
    global k
    global slo_min
    global slo_max
    global fac_min
    global fac_lim
    global area_min
    global s_rad
    global e_rad
    global th_sieve
    global crsSrctxt
    global crsSrc 
    global ext
    global infile_z
    global f_z

    if script_type == "PRA":
########### B.1 create file paths for PRA calculation files ####################
        print("---------------------------------------------------------------")
        print("+++ Potential release areas (PRA) simulation +++")
        
        ## construct filename, Name of AOI and Nr of run
        split_folder_path = folder_path.split('/')
        folder_name = split_folder_path[-1]
        split_folder_name = folder_name.split('_')
    
        ## names for LAWIS and HYDRO layers
        dataset_name = '_'.join(split_folder_name[2:])
        group_name = '_'.join(split_folder_name[2:]) 
        ## hillshade
        outfile_hsd = os.path.join(folder_path, f"{dataset_name}_HSD.tif")
        ## dem_aspect
        outfile_dem_aspect = os.path.join(folder_path, f"{dataset_name}_dem_aspect.tif")
        ## slope
        outfile_dem_slo = os.path.join(folder_path, f"{dataset_name}_SLOPE.tif")
        ## flowacc
        outfile_flo = os.path.join(folder_path, f"{dataset_name}_FLOWACC.sdat")
        ## curvature
        outfile = os.path.join(folder_path, f"{dataset_name}_CURV{k}{param_string}.sdat")
        outfile_del = os.path.join(folder_path, f"{dataset_name}_CURV{param_string}.sdat")
        ## combflow
        outfile_comb = os.path.join(folder_path, f"{dataset_name}_COMBFLOW{param_string}.sdat")
        outfile_comb_del = os.path.join(folder_path, f"{dataset_name}_COMBFLOW.*")
        ## PRA grid
        outfile_PRA = os.path.join(folder_path, f"{dataset_name}_PRA{param_string}.sdat")
        outfile_PRA_del = os.path.join(folder_path, f"{dataset_name}_PRA{param_string}.*")
        ## PRA saga grid
        outfile_PRA_sgrd = os.path.join(folder_path, f"{dataset_name}_PRA{param_string}.sgrd")
        outfile_PRA_sgrd_del = os.path.join(folder_path, f"{dataset_name}_PRA{param_string}.*")
        ## PRA polygonized
        outfile_PRA_poly = os.path.join(folder_path, f"{dataset_name}_PRA{param_string}_poly.shp")
        ## PRA polygones without holes
        outfile_PRA_poly_cleaned = os.path.join(folder_path, f"{dataset_name}_PRA{param_string}_poly_cleaned.shp")        
        ## PRA polygones generalized 1.2
        outfile_PRA_gen = os.path.join(folder_path, f"{dataset_name}_PRA{param_string}_gen.shp")
        ## PRA polygones organized columns 1.3
        outfile_PRA_final = os.path.join(folder_path, f"{dataset_name}_PRA{param_string}_final.shp")

        ## PRA rev. Center Path
        outfile_PRA_final_center = os.path.join(folder_path, f"{dataset_name}_PRA{param_string}_final_center.shp")
        ## PRA_rev. Center coordinates
        outfile_PRA_final_center_coord = os.path.join(folder_path, f"{dataset_name}_PRA{param_string}_final_center_coord.shp")
        ## PRA Points in WGS84
        outfile_PRA_pt_wgs84 = os.path.join(folder_path, f"{dataset_name}_PRA{param_string}_pt_wgs84.shp")
        ## PRA GPP
        outfile_PRA_GPP = os.path.join(folder_path, f"{dataset_name}_GPP{param_string}.sdat")
        ## LAWIS profiles
        epsg4326_lawislayer_path = os.path.join(folder_path, f"{dataset_name}_LAWISprofile_EPSG4326{param_string}.shp")
        ## HYDRO stations
        hydro_station_path = os.path.join(folder_path, f"{dataset_name}_HYDROstations{param_string}.shp")
        ## tirol_station_d30_28
        tirol_station_d30_28_path = os.path.join(folder_path, f"{dataset_name}_tirol_station_d30_28_crs31254{param_string}.shp")
        ## ZAMG_stations_2019
        ZAMG_stationslist2019_path = os.path.join(folder_path, f"{dataset_name}_ZAMGstations_2019_crs31254{param_string}.shp")
        ## PRA buffer for mean aspect and slope
        outfile_PRA_buffer = os.path.join(folder_path, f"{dataset_name}_PRA_buffer{param_string}.shp")
        ## Cliped Dem for mean aspect and slope
        PRA_final_clip = os.path.join(folder_path, f"{dataset_name}_PRA_clip{param_string}.tif")
        ## PRA aspect
        PRA_final_aspect = os.path.join(folder_path, f"{dataset_name}_PRA_aspect{param_string}.tif")
        ## PRA slope
        PRA_slope = os.path.join(folder_path, f"{dataset_name}_PRA_slope{param_string}.tif")
        ## Center_coordinates of PRA in WGS84
        outfile_PRA_pt_wgs84_final_center_coord = os.path.join(folder_path, f"{dataset_name}_PRA_pt_wgs84_final_center_coord{param_string}.shp")
        ## PRA ZAMG distance
        outfile_PRA_ZAMG_dist = os.path.join(folder_path, f"{dataset_name}_PRA_ZAMG_dist{param_string}.csv")
        ## PRA aspect values as points
        PRA_final_aspect_points = os.path.join(folder_path, f"{dataset_name}_PRA_aspect_points{param_string}.shp")
        ## PRA mean altitude
        outfile_PRA_mean_alt = os.path.join(folder_path, f"{dataset_name}_PRA_mean_alt{param_string}.csv")
        ## Outpath for reprojected LAWISprofile Layer
        epsg31254_lawislayer_path = os.path.join(folder_path, f"{dataset_name}_LAWISprofile{param_string}.shp")

        print("\nPreperational steps:")
        print("\t1. Write filepaths  ✓")
        
        ## Github link
        repo_url = "https://api.github.com/repos/shechenberger/QGIS_GPP_PCM"
        
        if rp != "72h":
########## B.2 fetch data from GitHub #########################################
########## B.2.1 ZAMG station list data from GitHub (D0 calculations) #########
            ## define repository URL and file path
            repo_url = "https://api.github.com/repos/shechenberger/QGIS_GPP_PCM"
            file_path = "/ZAMG_Stationsliste_20190101.csv"

            ## get request to the GitHub API to retrieve file contents
            response = requests.get(f"{repo_url}/contents/{file_path}")

            if response.status_code == 200:
                # Decode the content from base64 encoding
                content = response.json()["content"]
                content = base64.b64decode(content).decode("utf-8")

                # Parse the CSV content
                csv_data = csv.reader(io.StringIO(content))
                print("\t2. ZAMG_Stationsliste_2019 download  ✓")
#                if printpaths == "Y":
#                    print(f"\n{repo_url}/contents/{file_path}")

                    
            else:
                print("Failed to retrieve file contents")

            ## create memory layer for points
            csvlayer = QgsVectorLayer("Point?crs=epsg:4326", "Points", "memory")
            ## define attributes for ZAMG stations layer
            zamg_fields = QgsFields()
            zamg_fields.append(QgsField("NAME", QVariant.String))
            zamg_fields.append(QgsField("STATIONSHOEHE", QVariant.Int))
            ## add fields to the layer
            csvlayer.dataProvider().addAttributes(zamg_fields)
            csvlayer.updateFields()
            ## skip headerline
            next(csv_data)

            ## create features
            for row in csv_data:
                ## extract latitude and longitude values
                longitude = float(row[0].split(';')[8])
                latitude = float(row[0].split(';')[9])
                ## extract ZAMG name and height
                ZAMG_name = str(row[0].split(';')[1])
                ZAMG_height = int(row[0].split(';')[5])  # Corrected variable name
                ## create a QgsFeature
                feature = QgsFeature()
                geometry = QgsGeometry.fromPointXY(QgsPointXY(longitude, latitude))
                feature.setGeometry(geometry)
                ## set attributes
                feature.setAttributes([ZAMG_name, ZAMG_height])
                ## add feature to layer
                csvlayer.dataProvider().addFeatures([feature])

            ## reproject LAWISprofiles layer
            ## processing.algorithmHelp("native:reprojectlayer")
            reproject_ZAMGstations = {
                'INPUT' : csvlayer,
                'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:31254'),
                'OPERATION':'+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=push +v_3 +step +proj=cart +ellps=WGS84 +step +inv +proj=helmert +x=577.326 +y=90.129 +z=463.919 +rx=5.137 +ry=1.474 +rz=5.297 +s=2.4232 +convention=position_vector +step +inv +proj=cart +ellps=bessel +step +proj=pop +v_3 +step +proj=tmerc +lat_0=0 +lon_0=10.3333333333333 +k=1 +x_0=0 +y_0=-5000000 +ellps=bessel',
                'OUTPUT':ZAMG_stationslist2019_path
            }
            reprojected_ZAMG = processing.run("native:reprojectlayer", reproject_ZAMGstations)

            ## Add ZAMG stations Layer (EPSG 31254)
            ZAMG_list_2019_crs31254 = iface.addVectorLayer(ZAMG_stationslist2019_path, "ZAMGstations_2019", "ogr")

            ## Write fieldvalues in list
            ZAMG_station_name_height = []
            ## Iterate over features
            for feature in QgsProject.instance().mapLayersByName('ZAMGstations_2019')[0].getFeatures():
                ## Extract the values
                name = feature['NAME']
                #height = feature['ZAMG_H']
                height = feature['STATIONSHO']
                
                ## Append values
                ZAMG_station_name_height.append([name, height])
    
        if rp != "150" and rp != "72h":
########## B.2.2 Fetch 3TNSS_100j_HÖLZL_crs31254 file #############################
            ## Download shp file from github
            response_shp = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_100j_HÖLZL_2022.shp")
            response_shx = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_100j_HÖLZL_2022.shx")
            response_cpg = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_100j_HÖLZL_2022.cpg")
            response_dbf = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_100j_HÖLZL_2022.dbf")
            response_prj = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_100j_HÖLZL_2022.prj")
            response_qmd = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_100j_HÖLZL_2022.qmd")

            ## Write shp data
            if response_shp.status_code == 200:
                ## Path 
                shp_path = os.path.join(folder_path, f"3TNSS_100j_HÖLZL_crs31254{param_string}.shp")
                print("\t3. 3TNSS_100j_HÖLZL_2022 download\t\t ✓")
#                if printpaths == "Y":
#                    print(shp_path)

                ## Save the shapefile to disk
                with open(shp_path, "wb") as f:
                    f.write(response_shp.content)
                    
            ## Write shx data
            if response_shx.status_code == 200:
                ## Path 
                shx_path = os.path.join(folder_path, f"3TNSS_100j_HÖLZL_crs31254{param_string}.shx")

                ## Save the shapefile to disk
                with open(shx_path, "wb") as f:
                    f.write(response_shx.content)

            ## Write cpg data
            if response_cpg.status_code == 200:
                ## Path 
                cpg_path = os.path.join(folder_path, f"3TNSS_100j_HÖLZL_crs31254{param_string}.cpg")

                ## Save the shapefile to disk
                with open(cpg_path, "wb") as f:
                    f.write(response_cpg.content)

            ## Write dbf data
            if response_dbf.status_code == 200:
                ## Path 
                dbf_path = str(folder_path +"ZAMG_100j3TNS_crs31254.dbf")
                dbf_path = os.path.join(folder_path, f"3TNSS_100j_HÖLZL_crs31254{param_string}.dbf")

                
                ## Save the shapefile to disk
                with open(dbf_path, "wb") as f:
                    f.write(response_dbf.content)
                    
            ## Write prj data
            if response_prj.status_code == 200:
                ## Path 
                prj_path = os.path.join(folder_path, f"3TNSS_100j_HÖLZL_crs31254{param_string}.prj")

                ## Save the shapefile to disk
                with open(prj_path, "wb") as f:
                    f.write(response_prj.content)

            ## Write qmd data
            if response_qmd.status_code == 200:
                ## Path 
                qmd_path = os.path.join(folder_path, f"3TNSS_100j_HÖLZL_crs31254{param_string}.qmd")

                ## Save the shapefile to disk
                with open(qmd_path, "wb") as f:
                    f.write(response_qmd.content)

            ## Load 3TNSS_100j_HÖLZL_crs31254
            ZONES_3TNSS_100j_HÖLZL_2022 = iface.addVectorLayer(shp_path, "3TNSS_100j_HÖLZL_crs31254", "ogr")
        
        if rp == "150":
            ## 3TNSS_150j_HÖLZL_crs31254
            ## Download shp file from github
            response_shp = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_150j_HÖLZL_2022.shp")
            response_shx = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_150j_HÖLZL_2022.shx")
            response_cpg = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_150j_HÖLZL_2022.cpg")
            response_dbf = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_150j_HÖLZL_2022.dbf")
            response_prj = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_150j_HÖLZL_2022.prj")
            response_qmd = requests.get("https://raw.githubusercontent.com/shechenberger/QGIS_GPP_PCM/main/3TNSS_150j_HÖLZL_2022.qmd")

            ## Write shp data
            if response_shp.status_code == 200:
                ## Path 
                shp_path = os.path.join(folder_path, f"3TNSS_150j_HÖLZL_crs31254{param_string}.shp")
                print("\t3. 3TNSS_150j_HÖLZL_2022 download  ✓")

                ## Save the shapefile to disk
                with open(shp_path, "wb") as f:
                    f.write(response_shp.content)
                    
            ## Write shx data
            if response_shx.status_code == 200:
                ## Path 
                shx_path = os.path.join(folder_path, f"3TNSS_150j_HÖLZL_crs31254{param_string}.shx")

                ## Save the shapefile to disk
                with open(shx_path, "wb") as f:
                    f.write(response_shx.content)

            ## Write cpg data
            if response_cpg.status_code == 200:
                ## Path 
                cpg_path = os.path.join(folder_path, f"3TNSS_150j_HÖLZL_crs31254{param_string}.cpg")

                ## Save the shapefile to disk
                with open(cpg_path, "wb") as f:
                    f.write(response_cpg.content)

            ## Write dbf data
            if response_dbf.status_code == 200:
                ## Path 
                dbf_path = str(folder_path +"ZAMG_150j3TNS_crs31254.dbf")
                dbf_path = os.path.join(folder_path, f"3TNSS_150j_HÖLZL_crs31254{param_string}.dbf")

                
                ## Save the shapefile to disk
                with open(dbf_path, "wb") as f:
                    f.write(response_dbf.content)
                    
            ## Write prj data
            if response_prj.status_code == 200:
                ## Path 
                prj_path = os.path.join(folder_path, f"3TNSS_150j_HÖLZL_crs31254{param_string}.prj")

                ## Save the shapefile to disk
                with open(prj_path, "wb") as f:
                    f.write(response_prj.content)

            ## Write qmd data
            if response_qmd.status_code == 200:
                ## Path 
                qmd_path = os.path.join(folder_path, f"3TNSS_150j_HÖLZL_crs31254{param_string}.qmd")

                ## Save the shapefile to disk
                with open(qmd_path, "wb") as f:
                    f.write(response_qmd.content)

            ## Load ZAMG_150j3TNS_crs31254 layer
            ZONES_3TNSS_150j_HÖLZL_2022 = iface.addVectorLayer(shp_path, "3TNSS_150j_HÖLZL_crs31254", "ogr")


########## B.2.3 Fetch style files for LAWIS and HYDRO data ####################
        ## Define HYDRO_style path and LAWIS_style path
        hydro_style_file_path = "/HYDRO_style.qml"
        lawis_style_file_path = "/LAWIS_style.qml"

        ## GET request to the GitHub API to retrieve file contents
        HYDRO_style_response = requests.get(f"{repo_url}/contents/{hydro_style_file_path}")
        LAWIS_style_response = requests.get(f"{repo_url}/contents/{lawis_style_file_path}")

        ## Check if the request was successful (status code 200)
        if HYDRO_style_response.status_code == 200:
            ## Decode the response content from base64 encoding
            H_style_content = HYDRO_style_response.json()["content"]
            HYDRO_style_file_content = base64.b64decode(H_style_content).decode("utf-8")
            print("\t4. HYDRO style file downolad  ✓")
        else:
            ## Print an error message if the request failed
            print(f"Failed to retrieve HYDRO file. Status code: {HYDRO_style_response.status_code}")

        ## Check if the request was successful (status code 200)
        if LAWIS_style_response.status_code == 200:
            ## Decode the response content from base64 encoding
            L_style_content = LAWIS_style_response.json()["content"]
            LAWIS_style_file_content = base64.b64decode(L_style_content).decode("utf-8")
            print("\t5. LAWIS style file downolad  ✓")
        else:
            ## Print an error message if the request failed
            print(f"Failed to retrieve LAWIS file. Status code: {LAWIS_style_response.status_code}")
            
######## B.3 potential releas area calculation ################################
######## B.3.1 Calculate necessary data #######################################
        print("\nCalculation of PRA polygons:")
        print("\t1. HSD, FLOWACC, SLOPE, ASPECT  ✓")
        
        f_hsd = outfile_hsd
        f_exist = os.path.exists(f_hsd)
        if (f_exist == False):
            #processing.algorithmHelp("qgis:hillshade")
            exp = {'INPUT': dem,
                'OUTPUT': f_hsd
            }
            result = processing.run("qgis:hillshade",exp )

        fileInfo = QFileInfo(f_hsd)
        rLabel = fileInfo.baseName()

        ##hsd = iface.addRasterLayer(f_hsd,rLabel,'gdal')
        ##hsd.setCrs(crsSrc)

        ## Calculate FLOWACC
        f_flo = outfile_flo
        f_exist = os.path.exists(f_flo)
        if (f_exist == False):
            exp = {'ELEVATION': dem,
                'METHOD': 1,
                'LENGTH': f_flo
            }
            result = processing.run("saga:flowpathlength", exp)
            ##print('\tFLOWACC WURDE ERZEUGT')
#        else:
#            print(str('\tFLOWACC:\tBESTEHENDES ' + f_flo + '\tWURDE VERWENDET\n'))
#
        ## Calculate slope
        f_slo = outfile_dem_slo
        f_exist = os.path.exists(f_slo)
        if (f_exist == False):
            exp = {
                'INPUT': dem,
                'OUTPUT': f_slo,
                'BAND': 1,
                'SCALE': 1,
                'AS_PERCENT': False,
                'COMPUTE_EDGES': False,
                'ZEVENBERGEN': False
            }
            result = processing.run("gdal:slope", exp)
        
        f_asp = outfile_dem_aspect
        exp_aspect = {
            'INPUT': dem,
            'OUTPUT': f_asp,
            'BAND': 1,
            'ZERO_FLAT': False,  # Don't assign 0 to flat areas
            'COMPUTE_EDGES': False,
            'NO_DATA': -99999.0  # Assign -99999 to flat areas
        }
        processing.run("gdal:aspect", exp_aspect)
            
        ## Curvature and combinations
        print("\t2. Curvature, Combinations  ✓")
        src_ds = osgeo.gdal.Open(infile_z) 
        os.system("gdalinfo "+ infile_z) 
        src_slo = osgeo.gdal.Open(f_slo) 
        src_flo = osgeo.gdal.Open(f_flo)
        src_asp = osgeo.gdal.Open(f_asp)
        
        x = src_ds.RasterXSize 
        y = src_ds.RasterYSize 
        nc = x*y 
        x_slo = src_slo.RasterXSize 
        y_slo = src_slo.RasterYSize
        xdisp = int(x / 2)
        ydisp = int(y / 2)
        
        src_ar = src_ds.ReadAsArray()
        src_slo = src_slo.ReadAsArray()
        src_flo = src_flo.ReadAsArray()
        
        dst_ar = src_ds.ReadAsArray()
        dst_comb = src_ds.ReadAsArray()
        dst_PRA = src_ds.ReadAsArray()

        cellSizeX = src_ds.GetGeoTransform()[1]
        cellSizeY = src_ds.GetGeoTransform()[5]
        no=src_ds.GetRasterBand(1).GetNoDataValue()

########## B.3.2 Write data as "SAGA" #########################################
        def WriteRaster (dst_filename, raster):
                format = "MEM"
                driver = gdal.GetDriverByName( format )
                dst_ds = driver.Create( dst_filename, len(raster[0]), len(raster),\
                1,gdal.GDT_Float32)
                dst_ds.SetGeoTransform( src_ds.GetGeoTransform() )
                dst_ds.GetRasterBand(1).SetNoDataValue(-99999) ## set a NoData value
                dst_ds.GetRasterBand(1).WriteArray( raster)
                format = 'SAGA' ##specifie format for the new datase
                driver = gdal.GetDriverByName(format)
                dst_ds_new = driver.CreateCopy(dst_filename, dst_ds) ##creates a copy in SAGA GIS format
                dst_ds = None
                
        max_val = 0
        min_val = 9000
        zaehler = 0
        curv = 0
        
        ## resample aspect
        aspect_array = src_asp.GetRasterBand(1).ReadAsArray()
        
        aspect_rad = np.deg2rad(aspect_array)
        aspect_sin = np.sin(aspect_rad)
        aspect_cos = np.cos(aspect_rad)

        ## Apply Gaussian smoothing to sine and cosine
        smoothed_sin = gaussian_filter(aspect_sin, sigma=3)
        smoothed_cos = gaussian_filter(aspect_cos, sigma=3)

        ## Construct smoothed aspect
        smoothed_aspect = (np.rad2deg(np.arctan2(smoothed_sin, smoothed_cos)) + 360) % 360
        
        def reshape_to_match(src, target_shape, fill_value=0):
            """Crop or pad a numpy array to match target shape."""
            target_rows, target_cols = target_shape
            src_rows, src_cols = src.shape

            # Crop if necessary
            trimmed = src[:target_rows, :target_cols]

            # Pad if necessary
            result = np.full((target_rows, target_cols), fill_value, dtype=src.dtype)
            rows = min(trimmed.shape[0], target_rows)
            cols = min(trimmed.shape[1], target_cols)
            result[:rows, :cols] = trimmed[:rows, :cols]

            return result
        
        target_shape = src_ar.shape

        if src_flo.shape != target_shape:
            print(f"Fixing src_flo shape from {src_flo.shape} to {target_shape}")
            src_flo = reshape_to_match(src_flo, target_shape)

        if src_slo.shape != target_shape:
            print(f"Fixing src_slo shape from {src_slo.shape} to {target_shape}")
            src_slo = reshape_to_match(src_slo, target_shape)


        
        print("\t3. Conditions Check, write PRA Raster  ✓")
########## B.3.3 Pixel Value Evaluation and Conditions Check #################
        for i in range(y):
            for j in range(x):
                if (src_ar[i,j] < min_val and src_ar[i,j] > max_val and i > k and j > k and i < (y-k) and j < (x-k)):
                    z5 = src_ar[i,j]
                    z2 = src_ar[i-k,j]
                    z4 = src_ar[i,j-k]
                    z6 = src_ar[i,j+k]
                    z8 = src_ar[i+k,j]

                    # Calculate Curvature
                    hd1 = (z4+z6)/2-z5;
                    he1 = (z2+z8)/2-z5;
                    # Avoiding division by 0
                    if (hd1 == 0 or he1 == 0):
                        dst_ar[i,j] = 0
                    else:
                        s2 = math.pow((2*k*cellSizeX),2);
                        d1 = (s2/(8*hd1) + hd1/2) * -1;
                        e1 = (s2/(8*he1) + he1/2) * -1;

                        curv = (d1+e1)/2;
                        dst_ar[i,j] = curv;

                ## Integrate aspect curve parameter
                aspect = smoothed_aspect[i,j]
                
                if(curv < 0 and src_flo[i,j] > fac_min and src_flo[i,j] <= fac_lim and src_slo[i,j] >= slo_min and src_slo[i,j] <= slo_max):
                    if (aspect >= 315 or aspect < 45): # North
                        dst_comb[i,j] = curv;
                        dst_PRA[i,j] = 100
                    elif (aspect >= 45 and aspect < 135): ## East
                        dst_comb[i,j] = curv;
                        dst_PRA[i,j] = 101
                    elif (aspect >= 135 and aspect < 225): ## South
                        dst_comb[i,j] = curv;
                        dst_PRA[i,j] = 102
                    else: ## West
                        dst_comb[i,j] = curv;
                        dst_PRA[i,j] = 103

                else:
                    dst_comb[i,j] = -99999.0
                    dst_PRA[i,j] = -99999.0
                
        WriteRaster (outfile, dst_ar);
        WriteRaster (outfile_comb, dst_comb)
        WriteRaster (outfile_PRA, dst_PRA)
        debug_PRA_expo = outfile_PRA.replace(".sdat", "_expo_debug.sdat")
        WriteRaster(debug_PRA_expo, dst_PRA)

########## B.3.4 Shrink and expand ############################################
        ## processing.algorithmHelp("saga:shrinkandexpand")
        exp = {'INPUT': outfile_PRA,
            'OPERATION': 0,
            'CIRCLE': 1,
            'RADIUS': s_rad,
            'RESULT': outfile_PRA
        }
        result = processing.run("saga:shrinkandexpand",exp )
        layer_shrink = QgsRasterLayer(outfile_PRA, 'outfile_PRA_shrink')
        ##QgsProject.instance().addMapLayer(layer_shrink)

        exp = {'INPUT': outfile_PRA,
            'OPERATION': 1,
            'CIRCLE': 1,
            'RADIUS': e_rad,
            'EXPAND': 0,
            'RESULT': outfile_PRA
        }
        result = processing.run("saga:shrinkandexpand",exp )
        layer_expand = QgsRasterLayer(outfile_PRA, 'outfile_PRA_expand')
        ##QgsProject.instance().addMapLayer(layer_expand)

        ## Shrink and expand 2nd
        #processing.algorithmHelp("saga:shrinkandexpand")
        exp = {'INPUT': outfile_PRA,
            'OPERATION': 3,
            'CIRCLE': 1,
            'RADIUS': 2,
            'RESULT': outfile_PRA
        }
        result = processing.run("saga:shrinkandexpand",exp )
        layer_final = QgsRasterLayer(outfile_PRA, 'outfile_PRA_final')
        ##QgsProject.instance().addMapLayer(layer_final)

        print("\t4. Implement aspect PRA raster  ✓")
########## B.3.5 reevaluate small parts and single pixels #####################
        ## Organize shrinked raster
        def custom_connected_components(array):
            """
            Find connected components in the array, treating pixels with values 100-103 as valid.
            Components are separated by both connectivity and value.
            Single pixels surrounded by different values are also considered as components.
            """
            ## Create a mask for valid data (values 100-103 are valid)
            valid_mask = (array >= 100) & (array <= 103)
            
            ## Initialize labeled array and component count
            labeled_array = np.zeros_like(array, dtype=int)
            current_label = 1
            total_valid_pixels = 0
            
            ## Process each value separately
            for value in range(100, 104):
                value_mask = (array == value)
                value_labeled, num_features = ndimage.label(value_mask)
                
                ## Add labeled components to the final labeled array
                labeled_array[value_labeled > 0] = value_labeled[value_labeled > 0] + current_label - 1
                current_label += num_features
                total_valid_pixels += np.sum(value_mask)
            
            ## Total number of components
            total_components = current_label - 1
            
            ## Get component sizes
            component_sizes = np.bincount(labeled_array.ravel())[1:]  # Exclude background
            
            ## Count single-pixel components
            single_pixel_count = np.sum(component_sizes == 1)
            
            return labeled_array, total_components

        src_PRA = osgeo.gdal.Open(outfile_PRA)
        shrinked_PRA = src_PRA.ReadAsArray()
        labeled_array, num_components = custom_connected_components(shrinked_PRA)


########## B.3.6 merge small areas #############################################        
        def merge_small_areas(dst_PRA, labeled_array, num_components, area_min, cellSizeX, cellSizeY, max_distance=5):
            """Merge small areas with adjacent larger areas, prioritizing the most dominant neighbor."""
            ##print(f"Dilatation Algorithm starts with area_min: {area_min}")
            
            changes_made = 0
            ## Create a mask of all small areas
            small_areas_mask = np.zeros_like(labeled_array, dtype=bool)
            
            ## First pass: identify all small areas
            for label in range(1, num_components + 1):
                component = labeled_array == label
                nr_of_cells = np.sum(component)
                area_in_sqm = nr_of_cells * (cellSizeX * cellSizeY * -1)
                
                if area_in_sqm < area_min:
                    small_areas_mask |= component
            
            ## Second pass: process all small areas
            if np.any(small_areas_mask):
                # Create a structure for 8-connectivity
                structure = np.ones((3, 3), dtype=bool)
                
                ## Label all small areas
                small_labels, num_small = ndimage.label(small_areas_mask, structure=structure)
                
                for small_label in range(1, num_small + 1):
                    current_small_area = small_labels == small_label
                    
                    ## Initialize neighbor counting
                    neighbor_values = {}
                    
                    ## Create increasingly dilated versions of the small area
                    dilated = current_small_area
                    for _ in range(max_distance):
                        dilated = ndimage.binary_dilation(dilated, structure=structure)
                        border = dilated & ~current_small_area
                        
                        ## Count neighbor values
                        for x, y in zip(*np.where(border)):
                            val = dst_PRA[x, y]
                            if 100 <= val <= 103:  # Valid values
                                neighbor_values[val] = neighbor_values.get(val, 0) + 1
                        
                        if neighbor_values:
                            break
                    
                    if neighbor_values:
                        ## Choose the most common neighbor value
                        most_common = max(neighbor_values.items(), key=lambda x: x[1])[0]
                        dst_PRA[current_small_area] = most_common
                        changes_made += 1
                        ##print(f"Merged small area with value {most_common} (neighbor counts: {neighbor_values})")
                    else:
                        ## Check for no-data neighbors
                        no_data_neighbors = np.any((dst_PRA[border] == -99999))
                        if no_data_neighbors:
                            dst_PRA[current_small_area] = -99999
                            changes_made += 1
                            ##print("Merged small area with no-data value (-99999)")
            
            ##print(f"Total number of areas merged: {changes_made}")
            return dst_PRA
    
        component_PRAs = merge_small_areas(shrinked_PRA, labeled_array, num_components, area_min, cellSizeX, cellSizeY, max_distance=1)
        WriteRaster (outfile_PRA, component_PRAs)

        
        print("\t5. Polygonize PRA raster, revise polygons  ✓")
########## B.3.7 Polygonize PRA raster & revise Polygons ######################
        ##processing.algorithmHelp("gdal:polygonize")
        exp = {
            'INPUT': outfile_PRA,
            'BAND': 1,
            'OUTPUT': outfile_PRA_poly
        }
        result = processing.run("gdal:polygonize",exp )
        
        layer_path = outfile_PRA_poly
        PRA_poly_layer = QgsVectorLayer(layer_path, "PRA_poly", "ogr")

        ## Add "area" field if it does not exist
        if "area" not in [field.name() for field in PRA_poly_layer.fields()]:
            with edit(PRA_poly_layer):
                PRA_poly_layer.dataProvider().addAttributes([QgsField("area", QVariant.Double)])
                PRA_poly_layer.updateFields()
        
        with edit(PRA_poly_layer):
            for feature in PRA_poly_layer.getFeatures():
                geom = feature.geometry()
                area = geom.area()
                feature["area"] = area
                PRA_poly_layer.updateFeature(feature)
        PRA_poly_layer = iface.addVectorLayer(outfile_PRA_poly,"", "ogr")
        PRA_poly_layer.setCrs(crsSrc)

        ## Print a summary of all calculated areas
        ## Verify updated values
        for feature in PRA_poly_layer.getFeatures():
            updated_area = feature["area"]
            ##print(f"Feature ID: {feature.id()}, Updated Area: {updated_area}")
        
        ## Delete PRAs < area_min
        with edit(PRA_poly_layer):
            area_min = str(area_min)
            area_exp = str('"area" <=' + area_min)
            request = QgsFeatureRequest().setFilterExpression(area_exp)
            request.setSubsetOfAttributes([])
            request.setFlags(QgsFeatureRequest.NoGeometry)

            ## loop over the features and delete
            for f in PRA_poly_layer.getFeatures(request):
                PRA_poly_layer.deleteFeature(f.id())

            ## Prep. for later snowdepth calculations
            dn_field = PRA_poly_layer.fields().indexFromName('DN')
            PRA_poly_layer.dataProvider().deleteAttributes([dn_field])
        PRA_poly_layer.updateFields()

        ## Generate filepaths
        outfile_PRA_poly_txt = str(dataset_name + "_PRA_poly.shp")
        outfile_PRA_poly_cleaned_txt = str(dataset_name + "_PRA_poly_cleaned.shp")
        outfile_PRA_final_txt = str(dataset_name + "_PRA_final.shp")
        outfile_PRA_final_center_txt = str(dataset_name + "_PRA_final_center.shp")
        outfile_PRA_final_center_coord_txt = str(dataset_name + "_PRA_final_center_coord.shp")
        outfile_PRA_pt_wgs84_txt = str(dataset_name + "_PRA_pt_wgs84.shp")
        outfile_PRA_sgrd_txt = str(dataset_name + "_PRA.sgrd")
        outfile_PRA_GPP_txt = str(dataset_name + "_GPP.sgrd")

        ## Delet PRAs holes
        ## processing.algorithmHelp("native:deleteholes")
        outfile_PRA_poly_path = (os.path.join(folder_path, (str(outfile_PRA_poly_txt))))

        clean = {
            'INPUT' : outfile_PRA_poly_path,
            'MIN_AREA': 2000,
            'OUTPUT': outfile_PRA_poly_cleaned
        }
        PRA_cleaned = processing.run("native:deleteholes",clean)

        ## Generalize PRAs
        ## processing.algorithmHelp("grass7:v.generalize")
        outfile_PRA_poly_cleaned_path = (os.path.join(folder_path, (str(outfile_PRA_poly_cleaned_txt))))

        generalize = {
            'input' : outfile_PRA_poly_cleaned_path,
            'type' : [2],
            'cats' : '',
            'where' : '',
            'method' : 10,
            'threshold' : 150,
            'look_ahead' : 15,
            'reduction' : 50,
            'slide' : 0.5,
            'angle_thresh' : 3,
            'degree_thresh' : 0,
            'closeness_thresh' : 0,
            'betweeness_thresh' : 0,
            'alpha' : 1,
            'beta' : 1,
            'iterations' : 1,
            '-t' : False,
            '-l' : True,
            'output' : outfile_PRA_gen,
            'error' : 'TEMPORARY_OUTPUT',
            'GRASS_REGION_PARAMETER' : None,
            'GRASS_SNAP_TOLERANCE_PARAMETER' : 1,
            'GRASS_MIN_AREA_PARAMETER' : 0.0001,
            'GRASS_OUTPUT_TYPE_PARAMETER' : 3,
            'GRASS_VECTOR_DSCO' : '',
            'GRASS_VECTOR_LCO' : '',
            'GRASS_VECTOR_EXPORT_NOCAT' : False
        }

        PRA_rev = processing.run("grass7:v.generalize",generalize)
        nlayer = iface.addVectorLayer(outfile_PRA_gen,"", "ogr")
        nlayer.setCrs(crsSrc)

        print("\t6. Add attribute fields & layerstyle  ✓")
########## B.3.8 Add & organize PRAs attribute fields #########################
        newlayer_pr = nlayer.dataProvider()
        newlayer_pr.addAttributes([QgsField("ID",QVariant.Int),
                                   QgsField("g3TNSS_RP",QVariant.Double),
                                   QgsField("b3TNSS_RP",QVariant.Int),
                                   QgsField("alti [hm]",QVariant.Int),
                                   QgsField("exposition",QVariant.String),
                                   QgsField("slope [°]",QVariant.String),
                                   QgsField("vol[m^3]",QVariant.Int)])
        nlayer.updateFields()
        
        ## fields for RP == 30
        if rp == "30" and wind == "0":
            newlayer_pr.addAttributes([QgsField("D30",QVariant.Double)])
            nlayer.updateFields()
        if rp == "30" and wind == "30":
            newlayer_pr.addAttributes([QgsField("D30_30",QVariant.Double)])
            nlayer.updateFields()
        if rp == "30" and wind == "50":
            newlayer_pr.addAttributes([QgsField("D30_50",QVariant.Double)])
            nlayer.updateFields()
        if rp == "30" and wind == "rtw":
            newlayer_pr.addAttributes([QgsField("D30_rtw",QVariant.Double),
                                       QgsField("WS",QVariant.Int),
                                       QgsField("WS_G",QVariant.Int),
                                       QgsField("WD",QVariant.String)])
            nlayer.updateFields()
        
        ## fields for RP == 100
        if rp == "100" and wind == "0":
            newlayer_pr.addAttributes([QgsField("D100",QVariant.Double)])
            nlayer.updateFields()
        if rp == "100" and wind == "30":
            newlayer_pr.addAttributes([QgsField("D100_30",QVariant.Double)])
            nlayer.updateFields()
        if rp == "100" and wind == "50":
            newlayer_pr.addAttributes([QgsField("D100_50",QVariant.Double)])
            nlayer.updateFields()
        if rp == "100" and wind == "rtw":
            newlayer_pr.addAttributes([QgsField("D100_rtw",QVariant.Double),
                                       QgsField("WS",QVariant.Int),
                                       QgsField("WS_G",QVariant.Int),
                                       QgsField("WD",QVariant.String)])
            nlayer.updateFields()

        ## fields for RP == 150
        if rp == "150" and wind == "0":
            newlayer_pr = nlayer.dataProvider()
            newlayer_pr.addAttributes([QgsField("D150",QVariant.Double)])
            nlayer.updateFields()
        if rp == "150" and wind == "30":
            newlayer_pr.addAttributes([QgsField("D150_30",QVariant.Double)])
            nlayer.updateFields()
        if rp == "150" and wind == "50":
            newlayer_pr.addAttributes([QgsField("D150_50",QVariant.Double)])
            nlayer.updateFields()
        if rp == "150" and wind == "rtw":
            newlayer_pr.addAttributes([QgsField("D150_rtw",QVariant.Double),
                                       QgsField("WS",QVariant.Int),
                                       QgsField("WS_G",QVariant.Int),
                                       QgsField("WD",QVariant.String)])
            nlayer.updateFields()

        ## fields for RP == 300
        if rp == "300" and wind == "0":
            newlayer_pr.addAttributes([QgsField("D300",QVariant.Double)])
            nlayer.updateFields()
        if rp == "300" and wind == "30":
            newlayer_pr.addAttributes([QgsField("D300_30",QVariant.Double)])
            nlayer.updateFields()
        if rp == "300" and wind == "50":
            newlayer_pr.addAttributes([QgsField("D300_50",QVariant.Double)])
            nlayer.updateFields()
        if rp == "300" and wind == "rtw":
            newlayer_pr.addAttributes([QgsField("D300_rtw",QVariant.Double),
                                       QgsField("WS",QVariant.Int),
                                       QgsField("WS_G",QVariant.Int),
                                       QgsField("WD",QVariant.String)])
            nlayer.updateFields()

        ## fields for rtw
        if rp == "72h" and wind == "rtw":
            newlayer_pr.addAttributes([QgsField("D72h",QVariant.Int),
                                       QgsField("D72h_rtw",QVariant.Int),
                                       QgsField("WS",QVariant.Int),
                                       QgsField("WS_G",QVariant.Int),
                                       QgsField("WD",QVariant.String),
                                       QgsField("vol_w[m^3]",QVariant.Int)])
            nlayer.updateFields()
        
        ## fields for rtw
        if rp == "72h" and wind == "0":
            newlayer_pr.addAttributes([QgsField("D72h",QVariant.Int)])
            nlayer.updateFields()
        
        if rp == "72h" and wind == "30":
            newlayer_pr.addAttributes([QgsField("D72h_30",QVariant.Int)])
            nlayer.updateFields()

        if rp == "72h" and wind == "50":
            newlayer_pr.addAttributes([QgsField("D72h_50",QVariant.Int)])
            nlayer.updateFields()
        
        ## Delet cat field (default from grass7:v.generalize)
        with edit(nlayer): 
            my_field = nlayer.fields().indexFromName('cat')
            nlayer.dataProvider().deleteAttributes([my_field])
        nlayer.updateFields()

        with edit(nlayer):
            for i, feature in enumerate(nlayer.getFeatures()):
                feature.setAttribute('ID', f'{i+1}')
                nlayer.updateFeature(feature)
        
        ## get field names
        PRA_field_names = [field.name() for field in nlayer.fields()]

        ## Organzie PRAs columns standard version
        if wind != "rtw":
            newtabel = {
                'INPUT' : outfile_PRA_gen,
                'FIELDS_MAPPING':[
                {'expression': '"ID"',             'length': 23, 'name': 'ID',               'precision': 0,'type': 6},
                {'expression': '"area"',           'length': 9,  'name': 'area [m^2]',       'precision': 0,'type': 2},
                {'expression': '"g3TNSS_RP"',      'length': 23, 'name': 'g3TNSS_RP',        'precision': 15,'type': 6},
                {'expression': '"b3TNSS_RP"',      'length': 9,  'name': 'b3TNSS_RP',        'precision': 0,'type': 2},
                {'expression': '"alti [hm]"',      'length': 9,  'name': 'alti [hm]',        'precision': 0,'type': 2},
                {'expression': '"exposition"',     'length': 80, 'name': 'exposition',       'precision': 0,'type': 10},
                {'expression': '"slope [°]"',      'length': 9,  'name': 'slope [°]',        'precision': 0,'type': 2},
                {'expression': PRA_field_names[8], 'length': 23, 'name': PRA_field_names[8], 'precision': 0,'type': 6},
                {'expression': '"vol[m^3]"',       'length': 80, 'name': 'vol[m^3]',         'precision': 0,'type': 2}],
                'OUTPUT':outfile_PRA_final
            }
            
            PRA_final_newtabel = processing.run("native:refactorfields", newtabel) 

        ## Organzie PRAs columns -> if real time wind is used
        if rp != "72h" and wind == "rtw":
            newtabel = {
                'INPUT': outfile_PRA_gen,
                'FIELDS_MAPPING': [
                    {'expression': '"ID"',              'length': 23, 'name': 'ID',         'precision': 0,  'type': 2},
                    {'expression': '"area"',            'length': 9,  'name': 'area [m^2]', 'precision': 0,  'type': 2},
                    {'expression': '"g3TNSS_RP"',       'length': 23, 'name': 'g3TNSS_RP',  'precision': 15, 'type': 6},
                    {'expression': '"b3TNSS_RP"',       'length': 9,  'name': 'b3TNSS_RP',  'precision': 0,  'type': 2},
                    {'expression': '"alti [hm]"',       'length': 9,  'name': 'alti [hm]',  'precision': 0,  'type': 2},
                    {'expression': '"exposition"',      'length': 80, 'name': 'exposition', 'precision': 0,  'type': 10},
                    {'expression': '"slope [°]"',       'length': 9,  'name': 'slope [°]',  'precision': 0,  'type': 2},
                    {'expression': f'"D{rp}"',        'length': 23, 'name': f'D{rp}',   'precision': 0, 'type': 2},
                    {'expression': '"vol[m^3]"',        'length': 80, 'name': 'vol[m^3]',   'precision': 0,  'type': 10},
                    {'expression': '"WS"',              'length': 23, 'name': 'WS',         'precision': 0,  'type': 2},
                    {'expression': '"WS_G"',            'length': 23, 'name': 'WS_G',       'precision': 0,  'type': 2},
                    {'expression': '"WD"',              'length': 80, 'name': 'WD',         'precision': 0,  'type': 10},
                    {'expression': f'"D{rp}_rtw"',    'length': 23, 'name': f'D{rp}_rtw','precision': 0, 'type': 2},
                    {'expression': '"vol_w[m^3]"',      'length': 80, 'name': 'vol_w[m^3]', 'precision': 0,  'type': 2}],
                'OUTPUT': outfile_PRA_final
            }
            
            PRA_final_newtabel = processing.run("native:refactorfields", newtabel) 
            
        ## Organzie PRAs columns -> if real time wind is used
        if rp == "72h" and wind == "rtw":
            newtabel = {
                'INPUT': outfile_PRA_gen,
                'FIELDS_MAPPING': [
                    {'expression': '"ID"',         'length': 23, 'name': 'ID',         'precision': 0,  'type': 2},
                    {'expression': '"area"',       'length': 9,  'name': 'area [m^2]', 'precision': 0,  'type': 2},
                    {'expression': '"g3TNSS_RP"',  'length': 23, 'name': 'g3TNSS_RP',  'precision': 15, 'type': 6},
                    {'expression': '"b3TNSS_RP"',  'length': 9,  'name': 'b3TNSS_RP',  'precision': 0,  'type': 2},
                    {'expression': '"alti [hm]"',  'length': 9,  'name': 'alti [hm]',  'precision': 0,  'type': 2},
                    {'expression': '"exposition"', 'length': 80, 'name': 'exposition', 'precision': 0,  'type': 10},
                    {'expression': '"slope [°]"',  'length': 9,  'name': 'slope [°]',  'precision': 0,  'type': 2},
                    {'expression': '"D72h"',     'length': 23, 'name': 'D72h',     'precision': 0,  'type': 2},
                    {'expression': '"vol[m^3]"',   'length': 80, 'name': 'vol[m^3]',   'precision': 0,  'type': 10},
                    {'expression': '"WS"',         'length': 23, 'name': 'WS',         'precision': 0,  'type': 2},
                    {'expression': '"WS_G"',       'length': 23, 'name': 'WS_G',       'precision': 0,  'type': 2},
                    {'expression': '"WD"',         'length': 80, 'name': 'WD',         'precision': 0,  'type': 10},
                    {'expression': '"D72h_rtw"',   'length': 23, 'name': 'D72h_rtw',   'precision': 0,  'type': 2},
                    {'expression': '"vol_w[m^3]"', 'length': 80, 'name': 'vol_w[m^3]', 'precision': 0,  'type': 2}],
                'OUTPUT': outfile_PRA_final
            }

            PRA_final_newtabel = processing.run("native:refactorfields", newtabel) 
            
########## B.3.9 Add PRA layer, set symbology & labels ########################
        ## add layer
        newlayer = iface.addVectorLayer(outfile_PRA_final,"", "ogr")
        newlayer.setCrs(crsSrc)
        
        ## PRA symbology
        hex_color = "#ff1601"
        PRA_color = QColor()
        PRA_color.setNamedColor(hex_color)
        
        ## Set transparency
        alpha = 90  ## Transparency value (0-255)
        PRA_color.setAlpha(alpha)

        ## Set the renderer to a single symbol renderer
        PRA_renderer = QgsSingleSymbolRenderer(newlayer.renderer().symbol().clone())
        PRA_renderer.symbol().setColor(PRA_color)

        ## Apply the new renderer to the layer
        newlayer.setRenderer(PRA_renderer)
        
        ## Create a new label
        PRA_label = QgsPalLayerSettings()
        PRA_label.fieldName = 'ID'
        PRA_label.enabled = True
        PRA_label.fontSize = 10

        ## Create buffer
        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.bufferSize = 1
        buffer_hex_color = "#ffffff"
        buffer_color = QColor()
        buffer_color.setNamedColor(buffer_hex_color)
        buffer_settings.bufferColor = buffer_color  # Set buffer color to white
        

        ## Set placement around centroid
        PRA_label.placement = QgsPalLayerSettings.AroundPoint

        ## Create the labeling style
        text_format = QgsTextFormat()
        text_format.setFont(QFont("Helvetica", 10))  # Set font and size
        text_format.setSize(10)  # Set font size
        text_format.setColor(QColor("black"))# Set font color
        text_format.setBuffer(buffer_settings)
    
        ## Apply the labeling style to the label
        text_format.setBuffer(buffer_settings)
        PRA_label.setFormat(text_format)

        ## Set the labeling settings to the layer
        layer_settings = QgsVectorLayerSimpleLabeling(PRA_label)
        newlayer.setLabelsEnabled(True)
        newlayer.setLabeling(layer_settings)

        ## Refresh the layer to see the changes
        newlayer.triggerRepaint()
        
        ## Write PRAname and area to list for SH calc.
        PRA_values = QgsVectorLayerUtils.getValues(newlayer, 'ID')[0] 
        PRA_values.sort() 
        area_values = QgsVectorLayerUtils.getValues(newlayer, 'area')[0]
        PRA_area_list = []
        
        ## write PRAname and area to list for SH calc.
        for i in range(len(PRA_values)):
            PRA_area_list.append(dict(zip(PRA_values, area_values)))
            break
            

## PRA finished
###############################################################################


###############################################################################
## C. CALCULATION OF SNOWDEPTH (D30, D100, D150, D300) ###############################
###############################################################################
        print("\nCalculation of snow depth:")
        print("\t1. Find the closest weather station  ✓")

        ## C.1 Find the closest ZAMG station ##################################
        ## Calculation of PRAs center coordinates
        PRA_final_path = (os.path.join(folder_path, (str(outfile_PRA_final_txt))))

        ## processing.algorithmHelp("native:centroids")
        center = {
            'INPUT' : PRA_final_path,
            'ALL_PARTS' : False,
            'OUTPUT' : outfile_PRA_final_center
        }
        PRA_center = processing.run("native:centroids", center)
        PRA_center_path = (os.path.join(folder_path, (str(outfile_PRA_final_center_txt))))

        ## processing.algorithmHelp("qgis:exportaddgeometrycolumns")
        coords = {
            'INPUT': PRA_center_path,
            'CALC_METHOD' : 0,
            'OUTPUT' : outfile_PRA_final_center_coord
        }
        PRA_center_coordinates = processing.run("qgis:exportaddgeometrycolumns", coords)

        ## Reproject PRA center coordinates to WGS84
        PRA_center_coord_path = (os.path.join(folder_path, (str(outfile_PRA_final_center_coord_txt))))

        ## Reproject to WGS84 for distance to LAWIS and HYDRO data
        ## processing.algorithmHelp("native:reprojectlayer")
        reproject = {
            'INPUT' : PRA_center_coord_path,
            'TARGET_CRS' : QgsCoordinateReferenceSystem('EPSG:4326'),
            'OPERATION' : '+proj=pipeline +step +inv +proj=tmerc +lat_0=0 +lon_0=10.3333333333333 +k=1 +x_0=0 +y_0=-5000000 +ellps=bessel +step +proj=push +v_3 +step +proj=cart +ellps=bessel +step +proj=helmert +x=577.326 +y=90.129 +z=463.919 +rx=5.137 +ry=1.474 +rz=5.297 +s=2.4232 +convention=position_vector +step +inv +proj=cart +ellps=WGS84 +step +proj=pop +v_3 +step +proj=unitconvert +xy_in=rad +xy_out=deg',
            'OUTPUT' : outfile_PRA_pt_wgs84
        }

        reproject_PRA_points = processing.run("native:reprojectlayer", reproject) 
            
        ## processing.algorithmHelp("qgis:exportaddgeometrycolumns")
        coords_wgs84 = {
            'INPUT': outfile_PRA_pt_wgs84,
            'CALC_METHOD' : 0,
            'OUTPUT' : outfile_PRA_pt_wgs84_final_center_coord
        }
        PRA_center_coordinates_wgs84 = processing.run("qgis:exportaddgeometrycolumns", coords_wgs84)

        ## Add PRAs center points
        wgs84_pt_layer = iface.addVectorLayer(outfile_PRA_pt_wgs84_final_center_coord, "", "ogr")
        wgs84_pt_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

        if rp != "72h":
    ########## C.1.1 Calculation of Distance - PRAs Center and ZAMG Center ########
            ##if rp != "30":
                ## processing.algorithmHelp("qgis:distancetonearesthubpoints")
            close = {
                'INPUT' : PRA_center_coord_path,
                'HUBS' : ZAMG_stationslist2019_path,
                'FIELD' : 'NAME',
                'UNIT' : 0,
                'OUTPUT' : outfile_PRA_ZAMG_dist
            }

            PRA_Zamg_dist_pt = processing.run("qgis:distancetonearesthubpoints", close)

    ########## C.1.3 Find closest ZAMG Station for PRAs ###########################
            PRA_ZAMG = []
            with open((os.path.join(folder_path, (str(outfile_PRA_ZAMG_dist)))), newline='', encoding='utf-8') as fdist:
                reader = csv.reader(fdist, delimiter=',')
                ## get nearest station name
                header = next(reader)
                ## Find the indices of 'PRA_ID' and 'HubName'
                try:
                    pra_id_index = header.index('ID')
                    hub_name_index = header.index('HubName')
                except ValueError:
                    print("Error: 'ID' or 'HubName' not found in header.")
                    pra_id_index, hub_name_index = None, None
                
                ## Read the rows and extract the desired columns based on the indices
                if pra_id_index is not None and hub_name_index is not None:
                    for row in reader:
                        ## Append the values for 'ID' and 'HubName' from each row
                        PRA_ZAMG.append([row[pra_id_index], row[hub_name_index]])
            
            if rp != "72h":
                ## Compare ZAMG name and get ZAMG altitude value
                for PRA_station in PRA_ZAMG:
                    for zamg_station in ZAMG_station_name_height:
                        if PRA_station[1] == zamg_station[0]:
                            PRA_station.append(zamg_station[1])
                            
        print("\t3. Altitude difference PRA - weather station  ✓")
########## C.1.2 Calculation of mean PRA Altitude #############################
        ## processing.algorithmHelp("native:zonalstatisticsfb")
        mean_a = {
            'INPUT' : PRA_final_path,
            'INPUT_RASTER' : dem,
            'RASTER_BAND' : 1,
            'COLUMN_PREFIX' : '_',
            'STATISTICS' : [2],
            'OUTPUT': outfile_PRA_mean_alt
        }
        mean_altidue = processing.run("native:zonalstatisticsfb", mean_a)
        
########## C.2 Altitude difference (PRAs - ZAMG station), PRAs slope ##########
        ## Open CSV file with PRA alititude and prepair data

        PRA_alti = []
        PRA_alti_path = (os.path.join(folder_path, (str(outfile_PRA_mean_alt))))
        with open(PRA_alti_path, newline='', encoding='utf-8') as mean_a:
            reader = csv.reader(mean_a, delimiter=',')
            for row in reader:
                PRA_alti.append(row[-1])
                
        ## Delete unneeded data
        del PRA_alti[0] 
        PRA_alt_lists = []
        for alti in PRA_alti:
            PRA_alt_lists.append([alti])
                
            ## Convert to float
        def maybeMakeNumber(s):
            if not s:
                return s
            try:
                f = float(s)
                i = int(f)
                return i if f == i else f
            except ValueError:
                return s
            
            ## Help def for iteration
        def convertEr(iterab):
            if isinstance(iterab, str):
                return maybeMakeNumber(iterab)
            if isinstance(iterab, Mapping):
                return iterab
            if isinstance(iterab, Iterable):
                return  iterab.__class__(convertEr(p) for p in iterab)

        PRA_alt_converted = convertEr(PRA_alt_lists)
        ##print("PRA_alt_converted:", PRA_alt_converted)

            ## Convert float to int
        PRA_alt_int = []
        for alt_float in PRA_alt_converted:
            PRA_alt_int.append([int(alt_float[0])])

    ########## C.2.1 Subtraction of PRA mean altitude and ZAMG altitude ###########
            ## get PRA_alti
        if rp != "72h":
            PRA_array = []
            for ar in PRA_alt_int:
                PRA_array.append(np.array(ar[0]))
            ## get ZAMG alti
            ZAMG_array = [] 
            for arr in PRA_ZAMG:
                ZAMG_array.append(np.array(arr[2]))
                
            ## Subtraction to get alti difference
            subtracted_array = np.subtract(PRA_array, ZAMG_array)
            alt_dif = list(subtracted_array)

        print("\t4. PRA mean slope & slope factor ✓")
########## C.2.2 Calculation of PRA mean slope #################################
        ## SLOPE dO AND dO*
        rad_28 = ((28*(math.pi))/180)
            
        ## Make a PRA-buffer
        ## processing.algorithmHelp("native:buffer")
        PRA_buffer = {
            'INPUT' : PRA_final_path,
            'DISTANCE' : 0,
            'SEGMENTS' : 5,
            'END_CAP_STYLE' : 0,
            'JOIN_STYLE' : 0,
            'MITER_LIMIT' : 2,
            'DISSOLVE' : False, 
            'OUTPUT' : outfile_PRA_buffer
        }
        processing.run("native:buffer", PRA_buffer) 
        
        buffer_layer = iface.addVectorLayer(outfile_PRA_buffer,"", "ogr")

        ## Initialize lists
        fψ_list = []
        mean_slope = []
        layers_to_remove = []
        
        for feat in buffer_layer.getFeatures():
            feat_id = feat.id()  ## Get the feature ID

            ## Select the current feature by ID
            buffer_layer.selectByIds([feat_id])
            selected_feat = list(buffer_layer.selectedFeatures())
            if not selected_feat:
                print(f"No feature selected for ID {feat_id}. Skipping...")
                continue


            # Define the output path for the clipped raster
            PRA_cliped_slo_path = os.path.join(folder_path, f"{dataset_name}_PRA_slope_{feat_id}.tif")

            # Define the parameters for the clipping process
            PRA_slo_param = {
                'INPUT': outfile_dem_slo,
                'MASK': QgsProcessingFeatureSourceDefinition(
                    outfile_PRA_buffer,
                    selectedFeaturesOnly=True,  # Use the selected feature from the buffer layer
                    featureLimit=-1,
                    geometryCheck=QgsFeatureRequest.GeometryAbortOnInvalid
                ),
                'ALPHA_BAND': False,
                'CROP_TO_CUTLINE': True,  # Crop to the selected feature
                'DATA_TYPE': 0,
                'EXTRA': '',
                'KEEP_RESOLUTION': False,
                'MULTITHREADING': False,
                'NODATA': None,
                'OPTIONS': '',
                'OUTPUT': 'TEMPORARY_OUTPUT',
                'SET_RESOLUTION': False,
                'SOURCE_CRS': None,
                'TARGET_CRS': None,
                'X_RESOLUTION': None,
                'Y_RESOLUTION': None
            }

            ##print("Clipping parameters:", PRA_slo_param)

            ## Run the clipping process
            try:
                PRA_final_slo = processing.run("gdal:cliprasterbymasklayer", PRA_slo_param)
                ## Check if the process result is valid and contains the 'OUTPUT' key
                if PRA_final_slo and 'OUTPUT' in PRA_final_slo:
                    ## Retrieve the temporary output path
                    temp_output = PRA_final_slo['OUTPUT']

                    ## Add the temporary raster to QGIS as a layer
                    PRA_cliped_slope_layer = iface.addRasterLayer(temp_output, f'PRA_cliped_slope_{feat_id}')
                    
                    ## Check if the layer is valid
                    if not PRA_cliped_slope_layer.isValid():
                        print(f"Failed to add temporary raster for feature ID {feat_id}.")
                else:
                    print(f"Clipping failed for feature ID {feat_id}.")
            except Exception as e:
                print(f"Error clipping slope for feature ID {feat_id}: {e}")
            
            ## Remove the current feature selection
            buffer_layer.removeSelection()
            
            layers_to_remove.append(PRA_cliped_slope_layer)
            
            provider = PRA_cliped_slope_layer.dataProvider()
            ext = PRA_cliped_slope_layer.extent()
            
            ## Get mean statistic for mean slope
            stats = provider.bandStatistics(1,QgsRasterBandStats.All,ext,0)
            
            ## mean slope
            degree = (stats.mean)
            mean_slope.append((feat.attribute('ID'), degree))
            
            ## Turn degrees into radians
            PRA_mean_slope = math.radians(degree)
            
            ## Calculate fψ for the current feature
            ## SLOPE FACTOR ()Salm et al., 1990):
            ##print("PRA_mean_slope =", PRA_mean_slope)
            
            fψ = (0.291 / (math.sin(PRA_mean_slope) - 0.202 * math.cos(PRA_mean_slope)))
            
            ## Append the result to the list
            fψ_list.append({"ID": feat.attribute('ID'), "fψ": fψ})
            ##print("fψ_list 1959", fψ_list)

        with edit(newlayer):
            for feature in newlayer.getFeatures():
                for pra_slo in mean_slope:
                    m_slope = pra_slo[1]
                    if feature["ID"] == pra_slo[0]:
                        feature["slope [°]"] = m_slope
                        newlayer.updateFeature(feature)

        ## Function to remove a layer if it exists
        def remove_layer(layer):
            if layer is not None:
                QgsProject.instance().removeMapLayer(layer.id())

                
        ## Remove all PRA slope tifs
        for pra_s_tif in layers_to_remove:
            remove_layer(pra_s_tif)
        ## Delete buffer
        remove_layer(buffer_layer)
            
        print("\t5. 3TNSS for rp", rp,"  ✓")
######## C.3 Calculation of 3 days snow accumulation (30, 100, 150, 300 years return periode)########             

        ## Parameters 3TNSS (Hölzl. et al., 2022)
        ## Equation for elevation-dependent 3TNSS:
        
            ## 3TNSS_RP = g3TNSS_RP * z + b3TNSS_RP

                ## g3TNSS_RP = elevation gradient
                ## b3TNSS_RP = basic snowdepth for this zone
                ## z = station elevation

        ## Equation values for RP = 100
        ## ZONE 1: 0.03 ∗ z + 60
        ## ZONE 2: 0.06 ∗ z + 46
        ## ZONE 3: 0.09 ∗ z + 32
        ## ZONE 4: 0.12 ∗ z + 18
        ## ZONE 5: 0.15 ∗ z + 4
        ## ZONE 6: 0.18 ∗ z −10
        
        ## Equation values for RP = 150
        ## ZONE 1: 0.03 ∗ z + 65
        ## ZONE 2: 0.06 ∗ z + 50
        ## ZONE 3: 0.09 ∗ z + 36
        ## ZONE 4: 0.12 ∗ z + 22
        ## ZONE 5: 0.15 ∗ z + 8
        ## ZONE 6: 0.18 ∗ z − 6

        ## Wind accumulation (in m)
        if wind == "30":
            wind_30 = 0.30
        if wind == "50":
            wind_50 = 0.50

###############################################################################
## Calc d100
        if rp != "150" and rp != "72h":
        ## Get feature idx of ZONES_3TNSS_100j_HÖLZL_2022
            ZONES_3TNSS_100j_HÖLZL_2022_idx = QgsSpatialIndex(ZONES_3TNSS_100j_HÖLZL_2022.getFeatures())

    ########## C.3.1 Check PRAs precipitation area #############
            with edit(newlayer):
                for PRA_feature in newlayer.getFeatures():
                    for zone_feature_id in ZONES_3TNSS_100j_HÖLZL_2022_idx.intersects(PRA_feature.geometry().boundingBox()): 
                        zone_feature = ZONES_3TNSS_100j_HÖLZL_2022.getFeature(zone_feature_id)
                        if PRA_feature.geometry().intersects(zone_feature.geometry()):
                
                            PRA_feature['g3TNSS_RP'] = zone_feature['g3TNSS100j'] 
                            PRA_feature['b3TNSS_RP'] = zone_feature['b3TNSS100J']
                            newlayer.updateFeature(PRA_feature) 
                            break
                            
            g3TNSS100j = newlayer.aggregate(QgsAggregateCalculator.ArrayAggregate, "g3TNSS_RP")[0]
            b3TNSS100j = newlayer.aggregate(QgsAggregateCalculator.ArrayAggregate, "b3TNSS_RP")[0]
            
            ## Additional snow accumulaiton due elevation-difference between PRAs and closest weaher station
            add = []
            for alt in alt_dif:
                for h in g3TNSS100j:
                    add.append((alt/100)*(h*100))
                    break
                        
            ## Include angle for calculation
            add_28 = []
            for a in add:
                add_28.append(a*(math.cos(rad_28)))
                            
            ## Calculation of basic snow depth
            dSt_3T100 = [] ## d0 at station
            for (a_h, z, b) in zip(g3TNSS100j, PRA_ZAMG, b3TNSS100j):
                dSt_3T100.append((a_h * z[2])+b) ## equation dSt = g3TNSS100j * z + b3TNSS100j
                            
            ## Calculation of basic snow depth at angle rad_28
            dSt_28_3T100 = [] ## d0* at station
            for d in dSt_3T100:
                dSt_28_3T100.append(math.cos(rad_28)*d)
            
    ########## C.3.2 Calculation of snow accumulation, write to fields ############
            with edit(newlayer):
                for i,PRA_feature in enumerate(newlayer.getFeatures()):
                    feat_id = PRA_feature['ID']
                    ## Find the corresponding fψ for this feature
                    fψ_value = next((item["fψ"] for item in fψ_list if item["ID"] == feat_id), None)
                                        
                    ## D30 (rp = 30years)
                    if rp == "30" and wind == "0":
                        PRA_feature['D30'] = float(round(((dSt_28_3T100[i] + add_28[i]) * fψ_value)*0.83))
                        newlayer.updateFeature(PRA_feature)
                    ## rtw - wind
                    if rp == "30" and wind == "rtw":
                        PRA_feature['D30'] = float(round(((dSt_28_3T100[i] + add_28[i]) * fψ_value)*0.83))
                        newlayer.updateFeature(PRA_feature)
                    ## 30 cm wind
                    if rp == "30" and wind == "30":
                        PRA_feature['D30_30'] = float(round(((dSt_28_3T100[i] + add_28[i] + wind_30 * 100) * fψ_value)*0.83))
                        newlayer.updateFeature(PRA_feature)
                    ## 50 cm wind
                    if rp == "30" and wind == "50":
                        PRA_feature['D30_50'] = float(round(((dSt_28_3T100[i] + add_28[i] + wind_50 * 100) * fψ_value)*0.83))
                        newlayer.updateFeature(PRA_feature)
                    
                    ## D100 (rp = 100)
                    if rp == "100" and wind == "0":
                        PRA_feature['D100'] = float(round((dSt_28_3T100[i] + add_28[i]) * fψ_value))
                        newlayer.updateFeature(PRA_feature)
                    ## rtw - wind
                    if rp == "100" and wind == "rtw":
                        PRA_feature['D100'] = float(round((dSt_28_3T100[i] + add_28[i]) * fψ_value))
                        newlayer.updateFeature(PRA_feature)
                    ## 30 cm wind
                    if rp == "100" and wind == "30":
                        PRA_feature['D100_30'] = float(round((dSt_28_3T100[i] + add_28[i] + wind_30 * 100) * fψ_value))
                        newlayer.updateFeature(PRA_feature)
                    ## 50 cm wind
                    if rp == "100" and wind == "50":
                        PRA_feature['D100_50'] = float(round((dSt_28_3T100[i] + add_28[i] + wind_50 * 100) * fψ_value))
                        newlayer.updateFeature(PRA_feature)
                                        
                    ## D300 (rp = 300)
                    if rp == "300" and wind == "0":
                        PRA_feature['D300'] = float(round(((dSt_28_3T100[i] + add_28[i]) * fψ_value)*1.16))
                        newlayer.updateFeature(PRA_feature)
                    ## rtw - wind
                    if rp == "300" and wind == "rtw":
                        PRA_feature['D300'] = float(round(((dSt_28_3T100[i] + add_28[i]) * fψ_value)*1.16))
                        newlayer.updateFeature(PRA_feature)
                    ## 30 cm wind
                    if rp == "300" and wind == "30":
                        PRA_feature['D300_30'] = float(round(((dSt_28_3T100[i] + add_28[i] + wind_30 * 100) * fψ_value)*1.16))
                        newlayer.updateFeature(PRA_feature)
                    ## 50 cm wind
                    if rp == "300" and wind == "50":
                        PRA_feature['D300_50'] = float(round(((dSt_28_3T100[i] + add_28[i] + wind_50 * 100) * fψ_value)*1.16))
                        newlayer.updateFeature(PRA_feature)
                        
            ## Delet 'H_Gradient' field 
            ## -> this can cause: OGR error deleting field -1: Invalid field index
            with edit(newlayer): 
                del_field1 = newlayer.fields().indexFromName('g3TNSS_RP')
                del_field2 = newlayer.fields().indexFromName('b3TNSS_RP')
                newlayer.dataProvider().deleteAttributes([del_field1, del_field2])
            newlayer.updateFields()
            
            ## PRA_volume
            with edit(newlayer):
                for PRA_feature in newlayer.getFeatures():
                    area_value = PRA_feature['area [m^2]']
                    
                    ## Find correct depth field for RP (D30, D100, D300)
                    depth_prefixes = ['D30','D100', 'D150', 'D300']
                    depth_field = None
                    depth_value = None
                    
                    ## Try to find the field in order of preference
                    for prefix in depth_prefixes:
                        ## Look for exact match first
                        if prefix in [field.name() for field in newlayer.fields()]:
                            depth_field = prefix
                            depth_value = PRA_feature[depth_field]
                            break
                        
                        ## If exact match not found, look for fields that start with this prefix
                        matching_fields = [field.name() for field in newlayer.fields() if field.name().startswith(prefix)]
                        if matching_fields:
                            depth_field = matching_fields[0]  # Take the first matching field
                            depth_value = PRA_feature[depth_field]
                            break
                
                    ## Calculate volume 
                    PRA_VOL = float(area_value) * (float(depth_value)/100)
                    depth_1 = (float(depth_value)/100)
                    
                    PRA_feature['vol[m^3]'] = PRA_VOL
                    newlayer.updateFeature(PRA_feature)
                    
            print("\t5. Volume calculation ✓")

###############################################################################
## D150 #######################################################################

        if rp == "150":
        ## Get feature idx of ZONES_3TNSS_150j_HÖLZL_2022
            ZONES_3TNSS_150j_HÖLZL_2022_idx = QgsSpatialIndex(ZONES_3TNSS_150j_HÖLZL_2022.getFeatures())

            ## Check PRAs precipitation
            with edit(newlayer):
                for PRA_feature in newlayer.getFeatures():#
                    for zone_feature_id in ZONES_3TNSS_150j_HÖLZL_2022_idx.intersects(PRA_feature.geometry().boundingBox()): 
                        zone_feature = ZONES_3TNSS_150j_HÖLZL_2022.getFeature(zone_feature_id)
                        if PRA_feature.geometry().intersects(zone_feature.geometry()): 
                            PRA_feature['g3TNSS_RP'] = zone_feature['g3TNSS150j'] 
                            PRA_feature['b3TNSS_RP'] = zone_feature['b3TNSS150J'] ###!!!!!!!!!!!!1
                            newlayer.updateFeature(PRA_feature) 
                            break
                            
            g3TNSS150j = newlayer.aggregate(QgsAggregateCalculator.ArrayAggregate, "g3TNSS_RP")[0]
            b3TNSS150j = newlayer.aggregate(QgsAggregateCalculator.ArrayAggregate, "b3TNSS_RP")[0]
            
            ## Additional snow accumulaiton -
            ## due elevation-difference between PRAs and closest weaher station
            add = []
            for alt in alt_dif:
                for h in g3TNSS150j:
                    add.append((alt/100)*(h*100))
                    break

            ## Include angle for calculation
            add_28 = []
            for a in add:
                add_28.append(a*(math.cos(rad_28)))
                            
            ## Calculation of basic snow depth
            dSt_3T150 = [] ## d0 at station
            for (a_h, z, b) in zip(g3TNSS150j, PRA_ZAMG, b3TNSS150j):
                dSt_3T150.append((a_h * z[2])+b) ## equation dSt = g3TNSS150j * z + b3TNSS150j
                        
            ## Calculation of basic snow depth at angle rad_28
            dSt_28_3T150 = [] ## d0* at station
            for d in dSt_3T150:
                dSt_28_3T150.append(math.cos(rad_28)*d)
            
            ## C.3.2 Calculation of d0, write to fields
            with edit(newlayer):
                for i,PRA_feature in enumerate(newlayer.getFeatures()): 
                    feat_id = PRA_feature['ID']

                    ## Find the corresponding fψ for this feature
                    fψ_value = next((item["fψ"] for item in fψ_list if item["ID"] == feat_id), None)

                    ## D150 (3day maximum - 150years event)
                    if rp == "150" and wind == "0":
                        ## Print the types of the variables
                        PRA_feature['D150'] = float(round((dSt_28_3T150[i] + add_28[i]) * fψ_value))
                        newlayer.updateFeature(PRA_feature)
                        
                    if rp == "150" and wind == "30":
                        PRA_feature['D150_30'] = float(round((dSt_28_3T150[i] + add_28[i] + wind_30 * 100) * fψ_value))
                        newlayer.updateFeature(PRA_feature)
                        
                    if rp == "150" and wind == "50":
                        PRA_feature['D150_50'] = float(round((dSt_28_3T150[i] + add_28[i] + wind_50 * 100) * fψ_value))
                        newlayer.updateFeature(PRA_feature)
                        
                    if rp == "150" and wind == "rtw":
                        PRA_feature['D150'] = float(round((dSt_28_3T150[i] + add_28[i]) * fψ_value))
                        newlayer.updateFeature(PRA_feature)

            ## Delet 'H_Gradient' field
            with edit(newlayer): 
                del_field1 = newlayer.fields().indexFromName('g3TNSS_RP')
                del_field2 = newlayer.fields().indexFromName('b3TNSS_RP')
                newlayer.dataProvider().deleteAttributes([del_field1, del_field2])
            newlayer.updateFields() 
            
            ## PRA_volume
            with edit(newlayer):
                for PRA_feature in newlayer.getFeatures():
                    area_value = PRA_feature['area [m^2]']
                    
                    ## Find corrrect D150 field, name could also be D150_30 or D150_50
                    depth_field = next((field.name() for field in newlayer.fields() if field.name().startswith('D150')), None)
                    depth_value = PRA_feature[depth_field]
                    
                    ## Calculate volume if we have valid values
                    PRA_VOL = float(area_value) * (float(depth_value)/100)
                    PRA_feature['vol[m^3]'] = PRA_VOL
                    newlayer.updateFeature(PRA_feature)
                    
        ## 3TNNS calculation is finished


################################################################################
## Acquisation of LAWIS- snowprofile ###########################################

        ## Prepairation of PRA_alti & aspect data
        print("\nLAWIS snow profile:")
        print("\t1. PRA aspect as point layer   ✓")
        
        ## Get PRA alti
        PRA_alt_int_list = []
        for altit in PRA_alt_int:
            PRA_alt_int_list.append(altit[0])
            
        ## get PRA alti
        with edit(newlayer):
            h = 0
            for feature in newlayer.getFeatures():
                try:
                    _ = feature.setAttribute('alti [hm]', PRA_alt_int_list[int(h)])
                    h += 1
                    _ = newlayer.updateFeature(feature)
                    
                except IndexError:
                    _ =feature.setAttribute('alti [hm]', PRA_alt_int_list[-1])
                    _ =newlayer.updateFeature(feature)

        ## Calculation of PRA_ASPECT
        ## processing.algorithmHelp("gdal:cliprasterbymasklayer")
        PRA_clip = {
            'INPUT' : dem,
            'MASK' : outfile_PRA_buffer,
            'SOURCE_CRS' : QgsCoordinateReferenceSystem('EPSG:31254'),
            'TARGET_CRS' : QgsCoordinateReferenceSystem('EPSG:31254'),
            'NODATA' : None,
            'ALPHA_BAND' : False,
            'CROP_TO_CUTLINE' : True,
            'KEEP_RESOLUTION' : False,
            'SET_RESOLUTION' : False,
            'X_RESOLUTION' : None,
            'Y_RESOLUTION' : None,
            'MULTITHREADING' : False,
            'OPTIONS' : '',
            'DATA_TYPE' : 0,
            'EXTRA' : '',
            'OUTPUT' : PRA_final_clip
        }
        PRA_final_clip = processing.run("gdal:cliprasterbymasklayer", PRA_clip)

        ## Path to cliped DEM
        clip_path = list(PRA_final_clip.values())
        PRA_final_clip_path = (os.path.join(folder_path, (str(clip_path[0]))))

        ## Write PRA_ASPECT
        ## processing.algorithmHelp("native:aspect")
        PRA_aspect = {
            'INPUT' : PRA_final_clip_path, 
            'Z_FACTOR' : 1,
            'OUTPUT' : PRA_final_aspect
        }
        PRA_final_aspect = processing.run("native:aspect", PRA_aspect)
            
        ## Path to PRA_ASPECT
        aspect_path = list(PRA_final_aspect.values())
        PRA_final_aspect_path = (os.path.join(folder_path, (str(aspect_path[0]))))

        ## Convert PRA_ASPECT to points
        ## processing.algorithmHelp("native:pixelstopoints")
        aspect_points = {
            'INPUT_RASTER' : PRA_final_aspect_path,
            'RASTER_BAND':1,
            'FIELD_NAME':'VALUE',
            'OUTPUT':PRA_final_aspect_points
        }
        PRA_final_aspect_points_TEST = processing.run("native:pixelstopoints", aspect_points)

        aspect_points_layer = iface.addVectorLayer(PRA_final_aspect_points,"", "ogr")
        aspect_points_layer.setCrs(crsSrc)

        print("\t2. Write memory layer for LAWIS data  ✓")
       
       ## add memory layer
        lawislayer = QgsVectorLayer('Point?crs = epsg:4326', 'lawisprofiles', 'memory') #memory layer needs to be saved as shp
        _writer = QgsVectorFileWriter.writeAsVectorFormat(lawislayer,epsg4326_lawislayer_path,'utf-8',driverName='ESRI Shapefile')
        
        ## lawis points in wgs84
        PRA_LAWIS_profiles = QgsVectorLayer(epsg4326_lawislayer_path, dataset_name + "_LAWISprofile_EPSG4326", "ogr")

        ## Check if the layer loaded successfully
        if not PRA_LAWIS_profiles.isValid():
            print("Error: LAWIS WGS84 Layer failed to load!")
        else:
            ## Access the data provider of the layer
            lawisprovider = PRA_LAWIS_profiles.dataProvider()
            
            ## Define the fields to be added
            fields = [
                QgsField("PRA_ID", QVariant.String),
                QgsField("ID", QVariant.Int),
                QgsField("NAME", QVariant.String),
                QgsField("DATE", QVariant.String),
                QgsField("ALTIDUDE", QVariant.Int),
                QgsField("ASPECT", QVariant.String),
                QgsField("SLOPE", QVariant.Int),
                QgsField("SD", QVariant.Int),
                QgsField("ECT", QVariant.Int),
                QgsField("COMMENTS", QVariant.String),
                QgsField("PDF", QVariant.String)
            ]
            
            ## Add the fields to the layer
            lawisprovider.addAttributes(fields)
            
            ## Update the fields
            PRA_LAWIS_profiles.updateFields()

        ## Data needed for LAWIS PROFILE selection
        lyrPts = QgsProject.instance().mapLayersByName(str(dataset_name + "_PRA_aspect_points"))[0]
        lyrPoly = QgsProject.instance().mapLayersByName(str(dataset_name + "_PRA_final"))[0]

        ###############################################################################
        ## THIS PART CALCULATES CLOSEST LAWIS PROFILE, CHECKS FOR SAME EXPOSITION AND 
        ## HIGHT AND WRITES THE RESULTS TO A NEW POINTFEATURE. IN THE ATTRIBUTES OF THIS
        ## LAYER IS THE DATA FROM THE CLOSEST LAWIS SNOWPROFILE
        ###############################################################################

        ## Define the aspect_to_compass function
        def aspect_to_compass(aspect_degrees):
            ## Handle no-data values
            if aspect_degrees == -9999:
                return -9999
                
            compass_directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW', 'N']
            compass_index = int((aspect_degrees + 11.25) / 45) % 8
            return compass_directions[compass_index]
        
        print("\t3. Check elevation and aspect  ✓")

        ## list for rtw data collection
        pra_aspect_list = []
        
        ##Select aspect points inside PRA
        ftsPoly = newlayer.getFeatures()
        for feat in ftsPoly:
            ## get feat id
            feat_id = feat[0]

            ## elevation range for lawis profiles
            PRA_H = feat['alti [hm]']
            PRA_ID = feat['ID']
            heightmin = PRA_H - int(elevation_range)
            heightmax = PRA_H + int(elevation_range)
            
            ## prep. for calc.
            geomPoly = feat.geometry()
            bbox = geomPoly.boundingBox()
            req = QgsFeatureRequest()
            filterRect = req.setFilterRect(bbox)
            featsPnt = lyrPts.getFeatures(filterRect)
            for featPnt in featsPnt:
                if featPnt.geometry().within(geomPoly):
                    selectet_points = lyrPts.select(featPnt.id())
                    
            ## get value from selected aspect points and calc. mean
            temp_layer = lyrPts.materialize(QgsFeatureRequest().setFilterFids(lyrPts.selectedFeatureIds()))    
            aspect_value = QgsVectorLayerUtils.getValues(temp_layer, "VALUE")[0]
            
            ## move degrees to move all north values into one class
            aspect_value_337 = [i + 337.6 if i < 22.4 else i for i in aspect_value] #need to add 337.6 to values from 0-22.4. for mean to work in northexposition
            
            ## calculate median
            median_aspect = (statistics.median(aspect_value_337))
            
            ## add to list for rtw calculations
            pra_aspect_list.append((PRA_ID, median_aspect)) 
            lyrPts.removeSelection()
            
            ## turn aspect degrees into points of compas(needed to compare with LAWIS Aspect)
            PRA_aspect_comp = aspect_to_compass(median_aspect)
            

            ## edit PRA
            layer_provider = newlayer.dataProvider()
            newlayer.startEditing()
            id = feat.id()
            
            ## write ASPECT to PRA layer
            aspect_idx = newlayer.fields().lookupField('exposition')
            PRA_aspect_value = {aspect_idx : PRA_aspect_comp} 
            
            ## check aspect
            if PRA_aspect_value is None:
                ##In case LAWIS data has no aspect
                print("exposition field contains no data.")
            layer_provider.changeAttributeValues({id:PRA_aspect_value})
            newlayer.commitChanges()
        
            ## get data from LAWIS API
            lawisresponse = requests.get(f'https://lawis.at/lawis_api/public/profile?startDate={start_date}&endDate={end_date}&heightMin={heightmin}&heightMax={heightmax}&region=Tirol')
            data = lawisresponse.json() 
            
            ## get LAWIS data
            vl_all = QgsVectorLayer("Point?crs=EPSG:4326", "LAWIS_all_profiles", "memory")
            prov_all = vl_all.dataProvider()
            prov_all.addAttributes([
                QgsField("ID", QVariant.Int),
                QgsField("Name", QVariant.String),
                QgsField("Elev", QVariant.Int),
                QgsField("Aspect", QVariant.String)
            ])
            vl_all.updateFields()
            
            ## Get all LAWIS coordinates and aspect
            all_lawis_coordinates = []
            for dic in data:
                id = dic.get('id')
                name = dic.get('location').get('name')
                elevation = dic.get('location').get('elevation')
                longitude = dic.get('location').get('longitude')
                latitude = dic.get('location').get('latitude')
                aspect = dic.get('location').get('aspect')
                
                ## LAWIS coordinates
                if longitude and latitude:
                    feat = QgsFeature()
                    feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(longitude, latitude)))
                    feat.setAttributes([
                        dic.get('id'),
                        dic.get('location').get('name'),
                        dic.get('location').get('elevation'),
                        dic.get('location').get('aspect').get('text') if dic.get('location').get('aspect') else None
                    ])
                    prov_all.addFeature(feat)

                ## Check if LAWIS profile is valid data
                if aspect == None:
                    aspect = None
                    print("LAWIS data is not valid")
                    print("no aspect found in Profile:", id)
            
                ## Get aspect data
                else:
                    aspect = aspect.get('text')
                    
                if name == None:
                    name = None
                    print("no name found in Profile:", id)
                    
                if elevation == None:
                    elevation = None
                    print("no elevation found in Profile:", id)

                if longitude == None:
                    longitude = None
                    print("no longitude found in Profile:", id)

                if latitude == None:
                    latitude = None
                    print("no latitude found in Profile:", id)
                    
                all_lawis_coordinates.append((id, name, elevation, longitude, latitude, aspect),)
            
            ## Filter the lawis coordinates based on PRA_aspect (PRA and LAWIS prifle must have same Aspect)
            lawis_PRA_aspect = [profile for profile in all_lawis_coordinates if profile[5] == PRA_aspect_comp]            
            
            ## update field - aspect value
            vl_aspect = QgsVectorLayer("Point?crs=EPSG:4326", "LAWIS_matching_aspect", "memory")
            prov_aspect = vl_aspect.dataProvider()
            prov_aspect.addAttributes(vl_all.fields())
            vl_aspect.updateFields()

            for tup in lawis_PRA_aspect:
                feat = QgsFeature()
                feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(tup[3], tup[4])))  # lon, lat
                feat.setAttributes([
                    tup[0],  ## ID
                    tup[1],  ## Name
                    tup[2],  ## Elevation
                    tup[5]   ## Aspect
                ])
                prov_aspect.addFeature(feat)
                        
            ## Skip to the next PRA feature if no matching LAWIS Aspect is found
            if not lawis_PRA_aspect:
                print("No LAWIS profile found in elevation and aspect range")
                print("skiping PRA feature:", feat_id)
                continue
               
            ## Find the center feature with the same ID as the current polygon
            center_feature = None
            for center_feat in wgs84_pt_layer.getFeatures():
                if center_feat['ID'] == feat_id:
                    center_feature = center_feat
                    break

            wgs84_PRA_long_lat = []
            if center_feature is not None:
                ## Append the coordinates of the center feature to the list
                center_coords = (center_feature['xcoord_2'], center_feature['ycoord_2'])
                wgs84_PRA_long_lat.append(center_coords)

            ## Get Lawis profile coordinates and IDs
            lawis_coords = [(long_lat[3], long_lat[4]) for long_lat in lawis_PRA_aspect]
            lawis_ids = [long_lat[0] for long_lat in lawis_PRA_aspect]

            ## Calculate distance between LAWIS and PRA
            da = QgsDistanceArea()
            da.setEllipsoid('WGS84')
            da.setSourceCrs(QgsCoordinateReferenceSystem('EPSG:4326'),
                            QgsProject.instance().transformContext())

            alldistances = []
            for PRA_wgs84_coords in wgs84_PRA_long_lat:
                p1 = QgsPointXY(float(PRA_wgs84_coords[0]), float(PRA_wgs84_coords[1]))
                for lawislonlat in lawis_coords:
                    p2 = QgsPointXY(float(lawislonlat[0]), float(lawislonlat[1]))
                    d_m = da.measureLine(p1, p2)
                    alldistances.append(d_m)

            ## Combine Lawis profile IDs and distances
            ID_Distance_join = list(zip(lawis_ids, alldistances))
            
            ## Sort by distance to find the closest Lawis profile
            sortformin = sorted(ID_Distance_join, key=lambda x: x[-1])
            
            ## Get closest Lawis profile
            closest_lawis_profile = sortformin[0]

            ## get LAWIS ID
            PRA_Lawis_profile_data = []
            ID = closest_lawis_profile[0]
            
            ## Get target data from closest LAWIS profile
            PRA_lawis_profile = requests.get(f'https://lawis.at/lawis_api/public/profile/{ID}?startDate={start_date}&endDate={end_date}&heightMin={heightmin}&heightMax={heightmax}&region=Tirol&lang=en&format=json')
            PRA_Lawis_profile_data.append(PRA_lawis_profile.json())

            ## get LAWIS coords.
            lawisprofile_coordinates = []
            for dictionary in PRA_Lawis_profile_data:
                lawisprofile_long = dictionary.get('location').get('longitude')
                lawisprofile_lat = dictionary.get('location').get('latitude')
                lawisprofile_coordinates.append((lawisprofile_long, lawisprofile_lat), )
            
            ## get LAWIS id
            for dictionary in PRA_Lawis_profile_data:
                LAWIS_id = dictionary.get('id')    
                
            ## get LAWIS name
            for dictionary in PRA_Lawis_profile_data:
                LAWIS_NAME = dictionary.get('location').get('name')
                
            ## get LAWIS aspect
            for dictionary in PRA_Lawis_profile_data:
                LAWIS_ASPECT = dictionary.get('location').get('aspect').get('text')
            
            ## get LAWIS slope
            for dictionary in PRA_Lawis_profile_data:
                LAWIS_SLOPE = dictionary.get('location').get('slope_angle')

            ## get LAWIS snow depth
            for dictionary in PRA_Lawis_profile_data:
                LAWIS_profile = dictionary.get('profile')
                LAWIS_maxmin = (LAWIS_profile[len(LAWIS_profile) - 1]['height'])
                LAWIS_SD = LAWIS_maxmin['max']
            
            ## get LAWIS alti
            for dictionary in PRA_Lawis_profile_data:
                LAWIS_ALTIDUDE = dictionary.get('location').get('elevation')
          
            ## get LAWIS date
            for dictionary in PRA_Lawis_profile_data:
                LAWIS_DATE = dictionary.get('date')

            ## get LAWIS comments
            for dictionary in PRA_Lawis_profile_data:
                LAWIS_COMMENTS = dictionary.get('comments')
                ##print(LAWIS_COMMENTS)
                
            ## get LAWIS ECT
            ECT_list = []
            for dictionary in PRA_Lawis_profile_data:
                LAWIS_ECT = dictionary.get('stability_tests')
                if LAWIS_ECT is not None:
                    for r in LAWIS_ECT:
                        hait = r.get('height')
                        if hait is not None:
                            ECT_list.append(hait)
                    
            ## Get ECTN
            ECT_Nr = [*range(len(ECT_list))]
            if len(ECT_Nr)== 1:
                LAWIS_ECT = ECT_list[ECT_Nr [0]]

            ## get PDF link from profile
            for dictionary in PRA_Lawis_profile_data:
                LAWIS_name = dictionary.get('files')
                files = dictionary.get('files').get('pdf')
                pdf_split = files.split("/")[-8:]
                del pdf_split[:3]
                woriking_pdf_link = ['https://lawis.at']
            for part in pdf_split:
                woriking_pdf_link.append(part)
                LAWIS_PDFlink = '/'.join([str(x) for x in woriking_pdf_link])

            ## get field ID from LAWIS_LAYER 
            PRA_id_idx = PRA_LAWIS_profiles.fields().lookupField('PRA_ID')
            id_idx = PRA_LAWIS_profiles.fields().lookupField('ID')
            name_idx = PRA_LAWIS_profiles.fields().lookupField('NAME')
            date_idx = PRA_LAWIS_profiles.fields().lookupField('DATE')
            l_alti_idx = PRA_LAWIS_profiles.fields().lookupField('ALTIDUDE')
            l_aspect_idx = PRA_LAWIS_profiles.fields().lookupField('ASPECT')
            l_slo_idx = PRA_LAWIS_profiles.fields().lookupField('SLOPE')
            l_sd_idx = PRA_LAWIS_profiles.fields().lookupField('SD')
            l_ect_idx1 = PRA_LAWIS_profiles.fields().lookupField('ECT')
            com_idx = PRA_LAWIS_profiles.fields().lookupField('COMMENTS')
            pdf_idx = PRA_LAWIS_profiles.fields().lookupField('PDF')
                    
            ## add features to lawis_Pts.
            PRA_LAWIS_profiles.startEditing()
            lawisfeat = QgsFeature()
            lawisfeat.setGeometry( QgsGeometry.fromPointXY(QgsPointXY(lawisprofile_long,lawisprofile_lat)))
            lawisprovider.addFeatures([lawisfeat])
            PRA_LAWIS_profiles.commitChanges()
                    
            ## Update fields
            featnr = PRA_LAWIS_profiles.featureCount()
            featlist = list(range(featnr))
            wanted_feat = [featlist[-1]]
            PRA_LAWIS_profiles.select(wanted_feat)
            selection = PRA_LAWIS_profiles.selectedFeatures()

            ## Change values of selected feature
            PRA_LAWIS_profiles.startEditing()
            for lfeat in selection:
                PRA_LAWIS_profiles.changeAttributeValue(lfeat.id(), PRA_id_idx, PRA_ID)
                PRA_LAWIS_profiles.changeAttributeValue(lfeat.id(), id_idx, LAWIS_id)
                PRA_LAWIS_profiles.changeAttributeValue(lfeat.id(), name_idx, LAWIS_NAME)
                PRA_LAWIS_profiles.changeAttributeValue(lfeat.id(), date_idx, LAWIS_DATE)
                PRA_LAWIS_profiles.changeAttributeValue(lfeat.id(), l_alti_idx, LAWIS_ALTIDUDE)
                PRA_LAWIS_profiles.changeAttributeValue(lfeat.id(), l_aspect_idx, LAWIS_ASPECT)
                PRA_LAWIS_profiles.changeAttributeValue(lfeat.id(), l_slo_idx, LAWIS_SLOPE)
                PRA_LAWIS_profiles.changeAttributeValue(lfeat.id(), l_sd_idx, LAWIS_SD)
                PRA_LAWIS_profiles.changeAttributeValue(lfeat.id(), l_ect_idx1, LAWIS_ECT)
                PRA_LAWIS_profiles.changeAttributeValue(lfeat.id(), com_idx, LAWIS_COMMENTS)
                PRA_LAWIS_profiles.changeAttributeValue(lfeat.id(), pdf_idx, LAWIS_PDFlink)
            PRA_LAWIS_profiles.commitChanges()
            PRA_LAWIS_profiles.removeSelection()

        ## Reproject LAWISprofiles layer
        ## processing.algorithmHelp("native:reprojectlayer")
        reproject_LAWISprofiles = {
            'INPUT' : epsg4326_lawislayer_path,
            'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:31254'),
            'OPERATION':'+proj=pipeline +step +proj=unitconvert +xy_in=deg +xy_out=rad +step +proj=push +v_3 +step +proj=cart +ellps=WGS84 +step +inv +proj=helmert +x=577.326 +y=90.129 +z=463.919 +rx=5.137 +ry=1.474 +rz=5.297 +s=2.4232 +convention=position_vector +step +inv +proj=cart +ellps=bessel +step +proj=pop +v_3 +step +proj=tmerc +lat_0=0 +lon_0=10.3333333333333 +k=1 +x_0=0 +y_0=-5000000 +ellps=bessel',
            'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:31254'),
            'OUTPUT':epsg31254_lawislayer_path
        }
        reprojected_LAWIS = processing.run("native:reprojectlayer", reproject_LAWISprofiles)
        
        ## add LAWISprofile Layer (EPSG 31254)
        LAWIS_profiles_EPSG31254 = iface.addVectorLayer(epsg31254_lawislayer_path, dataset_name + "_LAWISprofile", "ogr")

        ## Write the style content to a temporary file
        LAWIS_temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".qml")
        LAWIS_temp_file.write(LAWIS_style_file_content)
        LAWIS_temp_file.close()

        ## Apply the style to the layer
        if LAWIS_profiles_EPSG31254 is not None:
            success = LAWIS_profiles_EPSG31254.loadNamedStyle(LAWIS_temp_file.name)
            os.unlink(LAWIS_temp_file.name)
            if success:
                LAWIS_profiles_EPSG31254.triggerRepaint()
                L_root = QgsProject.instance().layerTreeRoot()
                lawis_node = L_root.findLayer(LAWIS_profiles_EPSG31254.id())
                if lawis_node:
                    lawis_node.layer().triggerRepaint()
                else:
                    print("Failed to find layer in the layer tree.")
            else:
                print("Failed to apply the style.")
        
        print("\t4. Find closest profile  ✓")
        print("\t5. Get profile data  ✓")
        print("\t5. Add features, update fields  ✓")
        print("\t6. Reproject layer, add layerstyle  ✓")
        
        ###########################################################################    
        ## Get snow precipitation measurement from weather stations (HydroOnline Tirol)

        print("\nHYDRO data - real time wind and snwo measurements:")
        print("\t1 Write HYDRO data layer  ✓")
        
        ## Files needed for HYDROstations
        hydrolayer = QgsVectorLayer('Point?crs = epsg:31254', 'hydrostations', 'memory')
        h_writer = QgsVectorFileWriter.writeAsVectorFormat(hydrolayer,hydro_station_path,'utf-8',driverName='ESRI Shapefile')
        point_layer = QgsVectorLayer(hydro_station_path, dataset_name +  "HYDROstations", "ogr")
        
        ## Set CRS
        point_layer.setCrs(crsSrc)

        ## Check if the layer was loaded successfully
        if not point_layer.isValid():
            print("Error: hydro Layer failed to load!")
        else:
            ## Access the data provider of the layer
            hydroprovider = point_layer.dataProvider()
            
            ## Define the fields to be added
            hydro_fields = [
                QgsField("PRA_ID", QVariant.String),
                QgsField("NAME_HS", QVariant.String),
                QgsField("NAME_WS", QVariant.String),
                QgsField("NAME_WD", QVariant.String),
                QgsField("HEIGHT", QVariant.Double),
                QgsField("HS", QVariant.Double),
                QgsField("HSD24", QVariant.Double),
                QgsField("HSD48", QVariant.Double),
                QgsField("HSD72", QVariant.Double),
                QgsField("WS", QVariant.Double),
                QgsField("WS_G", QVariant.Double),
                QgsField("WD", QVariant.String),
                QgsField("PRA_dist", QVariant.Double)
            ]
            
            ## Add the fields to the layer
            hydroprovider.addAttributes(hydro_fields)
            
            ## Update the fields
            point_layer.updateFields()
        
            ## get field ID from Hydro_LAYER 
            PRA_id_idx              = point_layer.fields().lookupField('PRA_ID')
            station_nameHS_idx      = point_layer.fields().lookupField('NAME_HS')
            station_nameW_idx       = point_layer.fields().lookupField('NAME_WS')
            station_nameWD_idx      = point_layer.fields().lookupField('NAME_WD')
            station_height_idx      = point_layer.fields().lookupField('HEIGHT')
            station_HS_idx          = point_layer.fields().lookupField('HS')
            station_HSD24_idx       = point_layer.fields().lookupField('HSD24')
            station_HSD48_idx       = point_layer.fields().lookupField('HSD48')
            station_HSD72_idx       = point_layer.fields().lookupField('HSD72')
            station_WS_idx          = point_layer.fields().lookupField('WS')
            station_WS_G_idx        = point_layer.fields().lookupField('WS_G')
            station_WD_idx          = point_layer.fields().lookupField('WD')
            station_PRA_dist_idx    = point_layer.fields().lookupField('PRA_dist')
        
        ## GeoJSON URL for HYDRO TIROL data
        geojson_url = "https://wiski.tirol.gv.at/lawine/produkte/ogd.geojson"
        print("\t2 Fetch geojson  ✓")
        
        ## Fetch GeoJSON data from the URL
        HYDROresponse = requests.get(geojson_url)
        geojson_data = HYDROresponse.json()
        
        ## For transforming from WGS84 to EPSG 31254
        transform = QgsCoordinateTransform(QgsCoordinateReferenceSystem(4326), QgsCoordinateReferenceSystem(31254), QgsProject.instance())
        
        ## Get PRA layer
        ftsPoly2 = newlayer.getFeatures()
        newlayer.startEditing()
        
        ## snowdepth idx
        idx_D0_72h = newlayer.fields().indexOf('D72h')
        idx_D0_72h_30 = newlayer.fields().indexOf('D72h_30')
        idx_D0_72h_50 = newlayer.fields().indexOf('D72h_50')
        idx_D0_72h_w = newlayer.fields().indexOf('D72h_rtw')
        
        ## rtw, rp index
        idx_D0_rp_rtw = newlayer.fields().indexOf(f'D{rp}_rtw')
        
        ## wind
        idx_WS = newlayer.fields().indexOf('WS')
        idx_WS_G = newlayer.fields().indexOf('WS_G')
        idx_WD = newlayer.fields().indexOf('WD')
        
        ## volume incl. wind
        idx_vol = newlayer.fields().indexOf('vol[m^3]')
        idx_vol_w = newlayer.fields().indexOf('vol_w[m^3]')
        
        ## select points inside PRA
        for feat in ftsPoly2:
            ## get feat id
            feat_id = feat[0]
            
            ## mean PRA alti
            mean_altitude = feat['alti [hm]']
            PRA_id = feat['ID']
            PRA_expo = feat['exposition']
            PRA_area = feat['area [m^2]']
            PRA_vol = feat['vol[m^3]']
            if wind == "rtw":
                PRA_D0 = feat[f'D{rp}']
                print("PRA_D0 ", PRA_D0 )

            ## Define altitude range
            altitude_range = int(hydro_elevation_range)
            min_altitude = mean_altitude - altitude_range
            max_altitude = mean_altitude + altitude_range

            ## Iterate over GeoJSON features
            min_distance = float('inf')  # Initialize minimum distance to infinity
            closest_feature = None  # Initialize closest feature to None

            ## Initialize variables
            closest_snow_station = None
            closest_wind_speed_station = None
            closest_wind_dir_station = None
            min_snow_distance = float('inf')
            min_wind_speed_distance = float('inf')
            min_wind_dir_distance = float('inf')

            ## Extract altitude and coordinates
            for feature in geojson_data["features"]:
                altitude = feature["geometry"]["coordinates"][2]
                original_point = QgsPointXY(feature["geometry"]["coordinates"][0], feature["geometry"]["coordinates"][1])
                transformed_point = transform.transform(original_point)
                distance = QgsDistanceArea().measureLine(feat.geometry().centroid().asPoint(), transformed_point)
                
                ## Check for snow data
                has_snow_data = "HS" in feature["properties"] and feature["properties"]["HS"] is not None
                if has_snow_data and altitude >= min_altitude and altitude <= max_altitude and distance < min_snow_distance:
                    min_snow_distance = distance
                    closest_snow_station = feature
                    snow_point = QgsPointXY(feature["geometry"]["coordinates"][0], feature["geometry"]["coordinates"][1])
                    transformed_snow_point = transform.transform(snow_point)
                
                ## Check for wind speed data
                has_wind_speed_data = "WG" in feature["properties"] and feature["properties"]["WG"] is not None
                if has_wind_speed_data and min_altitude <= altitude <= max_altitude and distance < min_wind_speed_distance:
                    min_wind_speed_distance = distance
                    closest_wind_speed_station = feature

                ## Check for wind direction data
                has_wind_dir_data = "WR" in feature["properties"] and feature["properties"]["WR"] is not None
                if has_wind_dir_data and min_altitude <= altitude <= max_altitude and distance < min_wind_dir_distance:
                    min_wind_dir_distance = distance
                    closest_wind_dir_station = feature

            ## Extract snow data
            if closest_snow_station:
                snow_name = closest_snow_station["properties"]["name"]
                snow_altitude = closest_snow_station["geometry"]["coordinates"][2]
                HS = closest_snow_station["properties"].get("HS", 0)
                HS_24 = closest_snow_station["properties"].get("HSD24", 0)
                HS_48 = closest_snow_station["properties"].get("HSD48", 0)
                HS_72 = closest_snow_station["properties"].get("HSD72", 0)
                
                ## example data vor evaluation:
                ##HS_72 = 110
            else:
                snow_name = None
                HS = HS_24 = HS_48 = HS_72 = 0
                
            ## Extract wind speed data
            if closest_wind_speed_station:
                wind_name = closest_wind_speed_station["properties"].get("name", "Unknown")
                WS = closest_wind_speed_station["properties"].get("WG", 0)
                WS_G = closest_wind_speed_station["properties"].get("WG_BOE", 0)
            else:
                wind_name = None
                WS = WS_G = 0

            ## Extract wind direction data
            if closest_wind_dir_station:
                wind_dir_name = closest_wind_dir_station["properties"].get("name", "Unknown")
                WD_val = closest_wind_dir_station["properties"].get("WR", 0)
                WD = aspect_to_compass(WD_val)
            else:
                wind_dir_name = None
                WD = None
                
            ## Add closest features to hydro.Pts
            point_layer.startEditing()
            hydrofeat = QgsFeature()
            hydrofeat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(transformed_snow_point.x(), transformed_snow_point.y())))
            hydroprovider.addFeatures([hydrofeat])
            point_layer.commitChanges()

            ## Assign values to the newly added feature
            point_layer.startEditing()
            hydro_featnr = point_layer.featureCount()
            hydro_featlist = list(range(hydro_featnr))
            wanted_hydro_feat = [hydro_featlist[-1]]
            point_layer.select(wanted_hydro_feat)
            hydro_selection = point_layer.selectedFeatures()
            
            ## upadet hydro attributes
            for hydrofeat in hydro_selection:
                point_layer.changeAttributeValue(hydrofeat.id(), PRA_id_idx, PRA_id)
                point_layer.changeAttributeValue(hydrofeat.id(), station_nameHS_idx, snow_name)
                point_layer.changeAttributeValue(hydrofeat.id(), station_nameW_idx, wind_name)
                point_layer.changeAttributeValue(hydrofeat.id(), station_nameWD_idx, wind_dir_name)
                point_layer.changeAttributeValue(hydrofeat.id(), station_height_idx, snow_altitude if closest_snow_station else None)
                point_layer.changeAttributeValue(hydrofeat.id(), station_HS_idx, HS)
                point_layer.changeAttributeValue(hydrofeat.id(), station_HSD24_idx, HS_24)
                point_layer.changeAttributeValue(hydrofeat.id(), station_HSD48_idx, HS_48)
                point_layer.changeAttributeValue(hydrofeat.id(), station_HSD72_idx, HS_72)
                point_layer.changeAttributeValue(hydrofeat.id(), station_WS_idx, WS)
                point_layer.changeAttributeValue(hydrofeat.id(), station_WS_G_idx, WS_G)
                point_layer.changeAttributeValue(hydrofeat.id(), station_WD_idx, WD)
                point_layer.changeAttributeValue(hydrofeat.id(), station_PRA_dist_idx, min(min_snow_distance, min_wind_speed_distance, min_wind_dir_distance))
            point_layer.commitChanges()
            point_layer.removeSelection()
            
            ## hydro is finshed
            ## now the data is used for D0 - wind analysis

            def snowDRIFT(D72h, WS, WD_expo, PRA_expo):
                '''Funktion zur Berechnung von Triebschnee-Transport
                basierend auf den selektierten Messdaten
                '''
                ## maximal bewegbare Schneehöhe basierend auf D72h und WS
                maxD72h = (WS / 100.0) * D72h
                ## Richtungsunterscheid zwischen PRA und Wind
                delta = abs((WD_val - PRA_expo + 180) % 360 - 180)
                ## Erosions-Depositions- Faktor abhängig von Delta
                expo_fac = -math.cos(math.radians(delta))  # luv = erosion, lee = deposition
                ## Triebschneehöhe
                d0_dirft = maxD72h * expo_fac
                return d0_dirft

            ## Update PRA if real time snowdepth gets used
            ## szenario if wind == 0
            if rp == "72h" and wind == "0":
                ## hight difference
                station_PRA_hightdif = mean_altitude - altitude
                ## correction of D0 data
                D72h = (HS_72 + (5*station_PRA_hightdif/100)) *(math.cos(rad_28)) ## 5cm +/- per 100hm, angle change
                ## volume
                vol = round((D72h/100) * PRA_area)
                                
                ## update snowdepth, volume
                newlayer.changeAttributeValue(feat.id(), idx_D0_72h, D72h) ## 72h snowdepth
                newlayer.changeAttributeValue(feat.id(), idx_vol, vol) ## volume 72h snowdepth

            ## szenario if wind == 30
            if rp == "72h" and wind == "30":
                ## hight difference
                station_PRA_hightdif = mean_altitude - altitude
                ## correction of D0 data
                D72h_30 = (HS_72 + (5 * station_PRA_hightdif / 100) + (wind_30 * 100)) * (math.cos(rad_28)) ## 5cm +/- per 100hm, angle change
                ## volume
                vol = round((D72h_30/100) * PRA_area)
                
                ## update snowdepth, volume
                newlayer.changeAttributeValue(feat.id(), idx_D0_72h_30, D72h_30) ## 72h snowdepth
                newlayer.changeAttributeValue(feat.id(), idx_vol, vol) ## volume 72h snowdepth

            ## szenario if wind == 50
            if rp == "72h" and wind == "50":
                ## hight difference
                station_PRA_hightdif = mean_altitude - altitude
                ## correction of D0 data
                D72h_50 = (HS_72 + (5 * station_PRA_hightdif / 100) + (wind_50 * 100)) * (math.cos(rad_28)) ## 5cm +/- per 100hm, angle change
                ## volume
                vol = round((D72h_50/100) * PRA_area)
                
                ## update snowdepth, volume
                newlayer.changeAttributeValue(feat.id(), idx_D0_72h_50, D72h_50) ## 72h snowdepth
                newlayer.changeAttributeValue(feat.id(), idx_vol, vol) ## volume 72h snowdepth
                
            ## Update PRA snowdepth if wind == rtw
            if wind == "rtw":
                ## wind direction = string
                if type(WD) is not str:
                    WD = str(WD)
                    
                ## get wind expp in degree
                WD_expo = WD_val
                
                ## altitude difference PRA closest station
                station_PRA_hightdif = mean_altitude - altitude
                
                ## Params for function:
                ## fetch snowdepth from station and correct 5 cm per 100 meter h difference
                if rp == "72h":
                    D72h = (HS_72 + (5*station_PRA_hightdif/100)) *(math.cos(rad_28)) ## 5cm +/- per 100hm, angle change
                    ## volume
                    vol = round((D72h/100) * PRA_area)
                    
                ## or use calculated d0 for snow errosion
                elif rp != "72h":
                    D72h = PRA_D0
                    vol = PRA_vol
                  
                ## exposition
                for pra_expo in pra_aspect_list:
                    if pra_expo[0] == PRA_id:
                        PRA_expo = pra_expo[1]

                ## run function snowDRIFT
                driftSnow = snowDRIFT(D72h, WS, WD_expo, PRA_expo)
                
                ## Erosion or Depostion of drift snow
                D72_rtw = D72h + driftSnow
                  
                ## New volume
                vol_rtw = D72_rtw * PRA_area

                ## update snowdepth
                if rp == "72h" and wind == "rtw":
                    ## update d0
                    newlayer.changeAttributeValue(feat.id(), idx_D0_72h, D72h) ## 72h snowdepth
                    newlayer.changeAttributeValue(feat.id(), idx_D0_72h_w, D72_rtw) ## 72h snowdepth wind
                    ## update wind
                    newlayer.changeAttributeValue(feat.id(), idx_WS, WS)
                    newlayer.changeAttributeValue(feat.id(), idx_WS_G, WS_G)
                    newlayer.changeAttributeValue(feat.id(), idx_WD, WD)
                    ## update volume
                    newlayer.changeAttributeValue(feat.id(), idx_vol, vol) ## volume 72h sd
                    newlayer.changeAttributeValue(feat.id(), idx_vol_w, vol_rtw) ## volume 72h sd wind)
                
                elif rp != "72h" and wind == "rtw":
                    newlayer.changeAttributeValue(feat.id(), idx_D0_rp_rtw, D72_rtw) ## 72h snowdepth wind
                    ## update wind
                    newlayer.changeAttributeValue(feat.id(), idx_WS, WS)
                    newlayer.changeAttributeValue(feat.id(), idx_WS_G, WS_G)
                    newlayer.changeAttributeValue(feat.id(), idx_WD, WD)
                    ## update volume
                    newlayer.changeAttributeValue(feat.id(), idx_vol, vol) ## volume 72h sd
                    newlayer.changeAttributeValue(feat.id(), idx_vol_w, vol_rtw) ## volume 72h sd wind)

        newlayer.commitChanges()

        print("\t3 Check elevation and aspect  ✓")
        print("\t4 Find closes station  ✓")
        print("\t5 Get station data  ✓")
        print("\t6 Add features, update fields  ✓")
        
        ## Add LHYDROstations layer (EPSG 31254)
        HYDRO_LAYER = iface.addVectorLayer(hydro_station_path, dataset_name +  "_HYDROstations", "ogr")
        HYDRO_LAYER.setCrs(crsSrc)

        if rp == "72h" or rp == "30":
            ## Delet 'H_Gradient' field
            with edit(newlayer): 
                del_field1 = newlayer.fields().indexFromName('g3TNSS_RP')
                del_field2 = newlayer.fields().indexFromName('b3TNSS_RP')
                newlayer.dataProvider().deleteAttributes([del_field1, del_field2])
            newlayer.updateFields() 
 
        ### Write the style content to a temporary file
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".qml")
        temp_file.write(HYDRO_style_file_content)
        temp_file.close()

        ## Apply the style to the layer
        if HYDRO_LAYER is not None:
            success = HYDRO_LAYER.loadNamedStyle(temp_file.name)
            os.unlink(temp_file.name)
            if success:
                HYDRO_LAYER.triggerRepaint()
                root = QgsProject.instance().layerTreeRoot()
                layer_node = root.findLayer(HYDRO_LAYER.id())
                if layer_node:
                    layer_node.layer().triggerRepaint()
                else:
                    print("Failed to find layer in the layer tree.")
            else:
                print("Failed to apply the style.")

        ## Organize PRA data
        ## Get the current project instance
        project = QgsProject.instance()
        
        ## Create a group
        layers_to_move = [HYDRO_LAYER, LAWIS_profiles_EPSG31254, newlayer, dem]
        group = QgsLayerTreeGroup("PRA RESULTS:\n" + group_name)
            
        ## Move loaded layers into a specific group
        root = QgsProject.instance().layerTreeRoot()
        root.insertChildNode(0, group)
        
        for f_layer in layers_to_move:
            layer_node = root.findLayer(f_layer.id())
            if layer_node is not None:
                ## Add layer to the group
                group.addChildNode(layer_node.clone())
                ## Remove layer from its current location
                parent = layer_node.parent()
                if parent is not None:
                    parent.takeChild(layer_node)

                else:
                    print(f"Error: Parent of layer {f_layer.name()} not found.")
            else:
                print(f"Error: Layer {f_layer.name()} not found.")
                
        iface.mapCanvas().refresh()
        
        ########################################################################
        ## clean workspace #####################################################

        ## Remove layers
        if rp == "72h": ## in case it was not needed
            ZONES_3TNSS_150j_HÖLZL_2022 = None
            ZONES_3TNSS_100j_HÖLZL_2022 = None
            csvlayer = None
            ZAMG_list_2019_crs31254 = None
        
        ## in case it was not needed
        if rp != "150":
            ZONES_3TNSS_150j_HÖLZL_2022 = None
        
        ## in case it was not needed
        if rp == "150":
            ZONES_3TNSS_100j_HÖLZL_2022 = None
        
        remove_layer(PRA_poly_layer)
        remove_layer(ZONES_3TNSS_150j_HÖLZL_2022)
        remove_layer(ZONES_3TNSS_100j_HÖLZL_2022)
        remove_layer(csvlayer)
        remove_layer(ZAMG_list_2019_crs31254)
        remove_layer(aspect_points_layer)
        remove_layer(wgs84_pt_layer)
        remove_layer(nlayer)

        print ("\nPRA simulation is finished")
        print("---------------------------------------------------------------")
        
        ## stop PRA timer
        PRA_end_time = time.time()

################################################################################
## PRA - Simulation Part is finished now #######################################
################################################################################

    ## start of GPP_PCM
    elif script_type == "PCM":

#        def trace_step(message):
#            global trace_step_counter
#            trace_step_counter += 1
#            with open("/Users/simonhechenberger/Desktop/Masterarbeit_GIS/Untersuchungsgebiete/Galtür/infinity_check.txt", "a") as f:
#                f.write(f"Step {trace_step_counter}: {message}\n")
#                
#        trace_step_counter = 0
        
        ## PCM timer
        PCM_start_time = time.time()
        print("\n+++ PCM avalanche simulation +++")
        
        ## construct filename, Name of AOI and Nr of run
        split_folder_path = folder_path.split('/')
        folder_name = split_folder_path[-1]
        split_folder_name = folder_name.split('_')
                
        ## names for groups
        dataset_name = '_'.join(split_folder_name[2:])
        group_name = '_'.join(split_folder_name[2:]) 

        ## PCM parameters
        class ParameterSelectionDialog(QDialog):
            def __init__(self, parent=None):
                super(ParameterSelectionDialog, self).__init__(parent)
                self.setWindowTitle("PCM Parameter")
                self.setMinimumWidth(700)  # Set minimum width to prevent squeezing
                self.setMinimumHeight(500)  # Set minimum height

                ## Default values
                self.rho = 200.0                ## snow density
                self.k = 7                      ## smoothing factor
                self.dz_grenz = 30              ## slope treshold
                self.dz_a = 3                   ## divergent flow exponent
                self.dz_p = 1                   ## persistence factor
                self.user_lawis_yn = None       ## snowprofile data
                self.user_fs_yn = None          ## fill sink
                self.user_output_option = None  ## output

                ## Main layout with fixed proportions
                layout = QHBoxLayout()
                layout.setContentsMargins(10, 10, 10, 10)  # Add margins
                layout.setSpacing(15)  # Add spacing between left and right panels
                
                ## Left layout for main widgets
                left_layout = QVBoxLayout()
                left_layout.setSpacing(8)  # Add spacing between widgets

                ## Add a main label at the top with bold text
                main_label = QLabel('<b>Please select PCM Parameters</b>')
                main_label.setStyleSheet("font-size: 14px; margin-bottom: 10px;")
                left_layout.addWidget(main_label)

                ## Function to create form rows with consistent spacing
                def add_form_field(layout, label_text, widget):
                    field_layout = QVBoxLayout()
                    field_layout.setSpacing(4)
                    
                    label = QLabel(label_text)
                    field_layout.addWidget(label)
                    field_layout.addWidget(widget)
                    
                    layout.addLayout(field_layout)
                    layout.addSpacing(4)  # Space between form rows
                    
                    return widget
                
                ## Add line edits for parameters with consistent sizing
                self.rho_value = QLineEdit(str(self.rho))
                self.rho_value.setMinimumWidth(150)
                add_form_field(left_layout, "Snow Density (rho):", self.rho_value)
                    
                self.k_value = QLineEdit(str(self.k))
                add_form_field(left_layout, "Smoothing Factor (k):", self.k_value)
                        
                self.dz_grenz_value = QLineEdit(str(self.dz_grenz))
                add_form_field(left_layout, "Slope Treshold (dz_grenz):", self.dz_grenz_value)
                    
                self.dz_a_value = QLineEdit(str(self.dz_a))
                add_form_field(left_layout, "Divergent Flow Exponent (dz_a):", self.dz_a_value)

                self.dz_p_value = QLineEdit(str(self.dz_p))
                add_form_field(left_layout, "Persistence Factor (dz_p):", self.dz_p_value)

                ## Explanation labels for parameters
                explanations = {
                    "LAWIS data": "Deep propagation (dp)",
                    "Fillsink": "Fillsink (fs)",
                    "Output": "Output options (oo)"
                }

                combo_boxes = {}

                for param, explanation in explanations.items():
                    combo_box = QComboBox()
                    combo_box.setMinimumWidth(150)
                    
                    if param == "LAWIS data":
                        combo_box.addItems(["N", "Y"])
                    elif param == "Fillsink":
                        combo_box.addItems(["N", "Y"])
                    elif param == "Output":
                        combo_box.addItems(["individual PRAs", "combined PRAs"])
                    
                    add_form_field(left_layout, f"{explanation}:", combo_box)
                    combo_boxes[param] = combo_box  # Store the combo box in the dictionary

                ## Add stretch at the end to push everything up
                left_layout.addStretch()
                
                ## Right layout for info label
                right_layout = QVBoxLayout()
                right_layout.setSpacing(10)

                ## Add an info label on the right
                info_label = QTextBrowser()
                info_label.setMinimumWidth(300)  # Ensure info panel has enough width
                info_label.setText(
                    "<b>rho:</b> Default snow density is set to 200.<br><br>"
                    "<b>k:</b> For DTM 5m -> k = 10.  For DTM 10m -> k = 7.<br><br>"
                    "<b>dz_grenz:</b> Slope Treshold (Saga GPP)-> Maximum inclination possible from the lateral spread.<br><br>"
                    "<b>dz_a:</b> Propagation exponent (Saga GPP) -> Slope deviation tolerance for flow..<br><br>"
                    "<b>dz_p:</b> Persistence Factor (Saga GPP) -> Inertia of mass.<br><br>"
                    "<b>dp:</b> Based on the snow profile from LAWIS weak layers can be integrated. Chose Y for yes or N for no.<br><br>"
                    "<b>fs:</b> Fill sink corrects depressions in Digital Terrain Models, ensuring accurate avalanche flow simulation. Chose Y for yes or N for no.<br><br>"
                    "<b>oo:</b> Set to <b>individual PRAs</b> produces a tif for each PRA. Set to <b>combined PRAs</b> produces one tif containg all PRAs<br><br>"
                )
                right_layout.addWidget(info_label)
                
                ## Create a button layout for better organization 
                button_layout = QHBoxLayout()
                button_layout.setSpacing(10)  # Space between buttons
                
                ## Create a spacer to push buttons to the right
                button_layout.addStretch()
                
                ## Cancel button first (on left)
                cancel_button = QPushButton("Cancel")
                cancel_button.setMinimumWidth(100)  # Fixed width for button
                cancel_button.setMinimumHeight(30)  # Fixed height for button
                cancel_button.clicked.connect(self.reject)
                button_layout.addWidget(cancel_button)
                
                ## Run button second (on right) and make it the default button
                run_button = QPushButton("Run")
                run_button.setMinimumWidth(100)  # Fixed width for button
                run_button.setMinimumHeight(30)  # Fixed height for button
                run_button.clicked.connect(self.accept)
                run_button.setDefault(True)  # Make it the default button (responds to Enter key)
                run_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")  # Make it more visible
                button_layout.addWidget(run_button)
                
                ## Add button layout to the right layout
                right_layout.addLayout(button_layout)
                
                ## Set fixed size ratio between left and right panels (40% to 60%)
                layout.addLayout(left_layout, 40)
                layout.addLayout(right_layout, 60)

                self.setLayout(layout)
                self.combo_boxes = combo_boxes

            def accept(self):
                ## Retrieve selected values and store in variables
                self.user_lawis_yn = self.combo_boxes["LAWIS data"].currentText()
                self.user_fs_yn = self.combo_boxes["Fillsink"].currentText()
                self.user_output_option = self.combo_boxes["Output"].currentText()
                self.rho = float(self.rho_value.text())
                self.k = int(self.k_value.text())
                self.dz_grenz = int(self.dz_grenz_value.text())
                self.dz_a = int(self.dz_a_value.text())
                self.dz_p = int(self.dz_p_value.text())

                ## Call the base class accept method to close the dialog
                super(ParameterSelectionDialog, self).accept()
        
        dialog = ParameterSelectionDialog()
        result = dialog.exec_()
        
        ## stop loop
        if result == QDialog.Rejected:
            print("")
            print("PCM stopped by user")
            print("")
            return

        ## Retrieve parameter values from the dialog
        rho = dialog.rho
        k = dialog.k
        dz_grenz = dialog.dz_grenz
        dz_a = dialog.dz_a
        dz_p = dialog.dz_p
        user_lawis_yn = dialog.user_lawis_yn
        user_fs_yn = dialog.user_fs_yn
        user_output_option = dialog.user_output_option

        ## input DEM
        infile_z = f_z
        print("infile_z", infile_z)
        src_ds = osgeo.gdal.Open(infile_z)
        
        ## Get PRA_final group name for PRA simulation run NR
        PRA_group_name = find_group_for_file(infile_z)
        print(f"\nDEM is currently in the group:")
        print("\tPRA RESULTS:\n\t", PRA_group_name)
        
        ## Split
        #PCM_parts = group_name.split('_')
        PCM_parts = folder_path.split('/')[-1].replace("RESULTS_PCM_", "")
        
        ## Define PCM results group name
        pcm_group = QgsLayerTreeGroup("PCM RESULTS:\n"+ PCM_parts)
        
        ## Add group to project
        root = QgsProject.instance().layerTreeRoot()
        root.insertChildNode(0, pcm_group)
        
        ## Name of PRA_final
        outfile_PRA_final_txt = str(PRA_group_name + "_PRA_final.shp")
        aspect_txt = str(PRA_group_name + "_dem_aspect.tif")
        slope_txt = str(PRA_group_name + "_SLOPE.tif")
        
        ## Path to Folder containing DEM
        parent_dir = os.path.dirname(folder_path)
        
        ## Path to PRA_final
        PRA_final_path = str(parent_dir + "/RESULTS_PRA_" + PRA_group_name + "/"+ outfile_PRA_final_txt)
        outfile_dem_aspect = str(parent_dir + "/RESULTS_PRA_" + PRA_group_name + "/"+ aspect_txt)
        outfile_dem_slo = str(parent_dir + "/RESULTS_PRA_" + PRA_group_name + "/"+ slope_txt)

        print("\nPRA input filepath:")
        print(PRA_final_path)
        
        ## Read PRA_final from Group containing the DEM input layer
        gdf = gpd.read_file(PRA_final_path)
        
        if user_lawis_yn == "Y":
            ## Path to LAWIS data
            lawislayer_path = str(parent_dir + "/RESULTS_PRA_" + PRA_group_name + "/"+ PRA_group_name + "_LAWISprofile.shp")
            print("\nLAWISprofile filepath:")
            print(lawislayer_path)
        
            ## Load the lawis_point shapefile 
            point_gdf = gpd.read_file(lawislayer_path)

        ## Replace 'your_raster.tif' with the absolute path to your raster
        aoi_raster_path = infile_z

        ## Open the AOI-raster to get its extent- properties
        with rasterio.open(aoi_raster_path) as src:
            raster_height = src.height
            raster_width = src.width
            raster_transform = src.transform

        def create_flexible_colortable(
            raster_layer,
            num_classes=7,
            method='sqrt',
            layer_type='velocity'
        ):
            """
            Creates a flexible color ramp for a raster layer, with selectable color schemes
            (velocity → reds, pressure → blues, massflow → greens) and no-decimal class breaks.

            Args:
                raster_layer: QgsRasterLayer-Objekt
                num_classes:   Anzahl der Klassen (Default: 5)
                method:        Klassifikationsmethode: 'log' oder 'sqrt' (Default: 'sqrt')
                layer_type:    'velocity' (rote Palette), 'pressure' (blaue Palette),
                               oder 'massflow' (grüne Palette)

            Returns:
                QgsSingleBandPseudoColorRenderer: konfigurierte Pseudo-Farbskala
            """
            ## raster stats
            provider = raster_layer.dataProvider()
            stats = provider.bandStatistics(1, QgsRasterBandStats.All)
            min_value = stats.minimumValue
            max_value = stats.maximumValue

            if min_value <= 0:
                min_value = 0.001

            ## get classes
            raw_breaks = []
            if method == 'log':
                log_min = math.log10(min_value)
                log_max = math.log10(max_value)
                log_interval = (log_max - log_min) / (num_classes - 1)
                for i in range(num_classes):
                    log_val = log_min + i * log_interval
                    raw_breaks.append(10 ** log_val)

            elif method == 'sqrt':
                sqrt_min = math.sqrt(min_value)
                sqrt_max = math.sqrt(max_value)
                sqrt_interval = (sqrt_max - sqrt_min) / (num_classes - 1)
                for i in range(num_classes):
                    sqrt_val = sqrt_min + i * sqrt_interval
                    raw_breaks.append(sqrt_val ** 2)

            else:
                raise ValueError(f"Unbekannte Methode '{method}'. Verwende 'log' oder 'sqrt'.")

            int_breaks = []
            for i, rb in enumerate(raw_breaks):
                if i == num_classes - 1:
                    int_breaks.append(int(math.ceil(max_value)))
                else:
                    int_breaks.append(int(math.floor(rb)))
                    
            for i in range(num_classes - 1):
                if int_breaks[i] >= int_breaks[i + 1]:
                    int_breaks[i + 1] = int_breaks[i] + 1

            ## Velocity colors
            color_1 = [
                QtGui.QColor('#fff5f0'),
                QtGui.QColor('#fee0d2'),
                QtGui.QColor('#fcbba1'),
                QtGui.QColor('#fc9272'),
                QtGui.QColor('#fb6a4a'),
                QtGui.QColor('#de2d26'),
                QtGui.QColor('#a50f15'),
            ]
            ## Pressure colors
            color_2 = [
                QtGui.QColor('#f7fbff'),
                QtGui.QColor('#deebf7'),
                QtGui.QColor('#c6dbef'),
                QtGui.QColor('#9ecae1'),
                QtGui.QColor('#6baed6'),
                QtGui.QColor('#3182bd'),
                QtGui.QColor('#08519c'),
            ]
            ## Massflow colors
            ##color_3 = [
            ##    QtGui.QColor('#f7fcf5'),
            ##    QtGui.QColor('#e5f5e0'),
            ##    QtGui.QColor('#c7e9c0'),
            ##    QtGui.QColor('#a1d99b'),
            ##    QtGui.QColor('#74c476'),
            ##    QtGui.QColor('#31a354'),
            ##    QtGui.QColor('#006d2c'),
            ##]

            if layer_type == 'velocity':
                palette = color_1
            elif layer_type == 'pressure':
                palette = color_2
            ## elif layer_type == 'massflow':
                ##palette = color_3
            else:
                raise ValueError("layer_type muss 'velocity', 'pressure' oder 'massflow' sein.")
        
            ## build ColorRamp-Items
            color_ramp_items = []
            for i in range(num_classes):
                color_index = min(i, len(palette) - 1)
                lower = int_breaks[i]

                if i == 0:
                    label = f'≤ {lower}'
                elif i == num_classes - 1:
                    prev = int_breaks[i - 1]
                    label = f'> {prev}'
                else:
                    prev = int_breaks[i - 1]
                    label = f'{prev} – {lower}'

                item = QgsColorRampShader.ColorRampItem(
                    lower,
                    palette[color_index],
                    label
                )
                color_ramp_items.append(item)

            shader = QgsRasterShader()
            color_ramp_shader = QgsColorRampShader()
            color_ramp_shader.setColorRampType(QgsColorRampShader.Discrete)
            color_ramp_shader.setColorRampItemList(color_ramp_items)
            shader.setRasterShaderFunction(color_ramp_shader)

            renderer = QgsSingleBandPseudoColorRenderer(
                raster_layer.dataProvider(), 1, shader
            )
            return renderer

        ## get return period from PRA
        for feature in gdf:
            d0_rp = gdf.columns[5]
            
            ## in case of real time wind
            windcheck = gdf.columns[7]
            if windcheck == "WS":
                wind = "rtw"
                rp = d0_rp.lstrip("D")
                
            else:
                rp = int(re.search(r"D(\d+)", d0_rp).group(1))
                
                ## Extract the number after '_', default to 0 if '_' is not present
                if '_' in d0_rp:
                    wind = int(d0_rp.split('_')[1])  # Get the part after '_'
                else:
                    wind = 0  # Default value when '_' is not present

                print("\nReturn period from input PRA:", 
                      f"\n\tRP \t\t\t\t\t {rp}",
                      f"\n\twind \t\t\t\t {wind}")
                break

        ## Print parameters
        print("---------------------------------------------------------------")
        print("+++ PCM user parameter +++")
        print("\tRho:\t\t\t\t\t\t", rho)
        print("\tSmoothing Factor:\t\t\t", k)
        print("\tSlope Treshold:\t\t\t\t", dz_grenz)
        print("\tDivergent Flow Exponent\t\t", dz_a)
        print("\tPersistance Factor\t\t\t", dz_p)
        print("\tFillsink:\t\t\t\t\t", user_fs_yn)
        print("\tWeak Layers:\t\t\t\t", user_lawis_yn)
        print("\tOutput option:\t\t\t\t", user_output_option)
        
        ##CONSTANT PARAMTERS
        g = float(9.81)

        ## PCM Parameter
        Xi = 1000 # necessary (!) but only for start
        
        ## Add timestep counter
        timestep = 0
        
        ## initialize lists
        mue_list = []
        xi_list = []
        dz_grenz_list = []
        dz_a_list= []
        dz_p_list = []

        ## Friction for rp = 150 interpolation function
        def log_interpolate(val_100, val_300):
            return math.exp(
                (math.log(val_100) * math.log(300/150) + 
                 math.log(val_300) * math.log(150/100)) 
                / math.log(300/100)
            )

        ## Calculate dynamic friction values for all 4 terrain types (flat to gully)
        mue_list = []
        xi_list = []
        
        ## Iterate through PRA for Friction Paramters μ and ξ based on RAMMS model
        for feature in gdf.iterrows():
            # Get values from the feature
            aval_size = int(feature[1]['vol[m^3]'])  ## Access the PRA_VOL column
            aval_alti = feature[1]['alti [hm]']  ## Access the alti [hm] column
            aval_id = feature[1]['ID']  ## Access the id column
            
            ## Large avalanches (>15.000 m³)
            if aval_size > 15000:
                user_avalsize = 'XL'
                ## Avalanche above 1500m 
                if aval_alti >= 1500:
                    ## RP 300
                    if str(rp).strip() == '300':
                        ## [flat, unchannelled, channeled, gully]
                        y_mu = [0.10,0.115,0.17,0.23]
                        y_xi = [4500, 3500,2500,2000]

                    ## RP  150
                    elif str(rp).strip() == '150':
                        ## Values for RP=300 and RP=100
                        mu_300 = [0.10,0.115,0.17,0.23]
                        mu_100 = [0.11,0.125,0.18,0.24]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [4500, 3500,2500,2000]
                    
                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.11,0.125,0.18,0.24]
                        y_xi = [4500, 3500,2500,2000]
                        
                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu = [0.115,0.13,0.185,0.25]
                        y_xi = [4500, 3500,2500,2000]

                ## Avalanche below 1500m and above 1000m
                elif 1000 < aval_alti <= 1500:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.10,0.115,0.17,0.23]
                        y_xi = [4000, 3000, 2200, 1800]
                        
                    ## RP  150
                    elif str(rp).strip() == '150':
                        ## Values for RP=300 and RP=100
                        mu_300 = [0.10,0.115,0.17,0.23]
                        mu_100 = [0.11,0.125,0.18,0.24]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [4000, 3000, 2200, 1800]
                        
                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.11,0.125,0.18,0.24]
                        y_xi = [4000, 3000, 2200, 1800]
                    
                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu = [0.115,0.13,0.185,0.25]
                        y_xi = [4000, 3000, 2200, 1800]
                        
                    ## Avalanche below 1000m
                elif aval_alti <= 1000:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.08, 0.12, 0.10, 0.13]
                        y_xi = [3500, 2500, 1900, 1600]
                         
                    ## RP  150
                    elif str(rp).strip() == '150':
                        mu_300 = [0.08, 0.12, 0.10, 0.13]
                        mu_100 = [0.14, 0.20, 0.21, 0.27]
                            
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [3500, 2500, 1900, 1600]
                            
                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.14, 0.20, 0.21, 0.27]
                        y_xi = [3500, 2500, 1900, 1600]
                        
                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu = [0.145, 0.21, 0.215, 0.28]
                        y_xi = [3500, 2500, 1900, 1600]

            elif 10000 < aval_size <= 15000:
                user_avalsize = 'L'
                ## Avalanche above 1500m 
                if aval_alti >= 1500:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.14, 0.155, 0.21, 0.27]
                        y_xi = [4000, 3000, 2000, 1500]

                    ## RP  150
                    elif str(rp).strip() == '150':
                        ## Values for RP=300 and RP=100
                        mu_300 = [0.14, 0.155, 0.21, 0.27]
                        mu_100 = [0.15, 0.165, 0.22, 0.28]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [4000, 1500, 2000, 3000]
                    
                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.15, 0.165, 0.22, 0.28]
                        y_xi = [4000, 3000, 2000, 1500]
                        
                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu = [0.155, 0.17, 0.225, 0.29]
                        y_xi = [4000, 3000, 2000, 1500]
               
                ## Avalanche below 1500m and above 1000m
                elif 1000 < aval_alti <= 1500:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.15, 0.17, 0.22, 0.285]
                        y_xi = [3500, 2500, 1750, 1350]
                    
                    ## RP  150
                    elif str(rp).strip() == '150':
                        ## Values for RP=300 and RP=100
                        mu_300 = [0.15, 0.17, 0.22, 0.285]
                        mu_100 = [0.16, 0.18, 0.23, 0.3]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [3500, 2500, 1750, 1350]

                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.16, 0.18, 0.23, 0.3]
                        y_xi = [3500, 2500, 1750, 1350]
                    
                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu = [0.17, 0.19, 0.24, 0.31]
                        y_xi = [3500, 2500, 1750, 1350]
                    
                ## Avalanche below 1000m
                elif aval_alti <= 1000:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.17, 0.19, 0.24, 0.3]
                        y_xi = [3000, 2000, 1500, 1200]
                     
                    ## RP  150
                    elif str(rp).strip() == '150':
                        mu_300 = [0.17, 0.19, 0.24, 0.3]
                        mu_100 = [0.18, 0.2, 0.25, 0.315]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [3000, 2000, 1500, 1200]

                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.18, 0.2, 0.25, 0.315]
                        y_xi = [3000, 2000, 1500, 1200]
                    
                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu = [0.19, 0.21, 0.26, 0.33]
                        y_xi = [3000, 2000, 1500, 1200]
                    
            ## Mediuam avalanche (25 - 60000 m³)
            elif 5000 < aval_size <= 10000:
                user_avalsize = 'M'
                ## Avalanche above 1500m 
                if aval_alti >= 1500:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.17,0.195, 0.25, 0.32]
                        y_xi = [3250, 2500, 1750, 1350]
                    
                    ## RP 150
                    elif str(rp).strip() == '150':
                        mu_300 = [0.17,0.195, 0.25, 0.32]
                        mu_100 = [0.18, 0.205, 0.26, 0.33]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [3250, 2500, 1750, 1350]
                    
                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.18, 0.205, 0.26, 0.33]
                        y_xi = [3250, 2500, 1750, 1350]
                     
                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu = [0.19, 0.215, 0.27, 0.34]
                        y_xi = [3250, 2500, 1750, 1350]

                ## Avalanche below 1500m and above 1000m
                elif 1000 < aval_alti <= 1500:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.19, 0.21, 0.27, 0.33]
                        y_xi = [2900, 2100, 1530, 1200]
                        
                    ## RP 150
                    elif str(rp).strip() == '150':
                        mu_300 = [0.19, 0.21, 0.27, 0.33]
                        mu_100 = [0.2, 0.22, 0.28, 0.34]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [2900, 2100, 1530, 1200]

                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.2, 0.22, 0.28, 0.34]
                        y_xi = [2900, 2100, 1530, 1200]

                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu = [0.21, 0.23, 0.285, 0.355]
                        y_xi = [2900, 2100, 1530, 1200]

                ## Avalanche below 1000m
                elif aval_alti <= 1000:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.21, 0.23, 0.28, 0.36]
                        y_xi = [2500, 1750, 1350, 1100]
                        
                    ## RP 150
                    elif str(rp).strip() == '150':
                        mu_300 = [0.21, 0.23, 0.28, 0.36]
                        mu_100 = [0.22, 0.24, 0.29, 0.37]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [2500, 1750, 1350, 1100]

                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.22, 0.24, 0.29, 0.37]
                        y_xi = [2500, 1750, 1350, 1100]
                    
                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu = [0.23, 0.215, 0.27, 0.38]
                        y_xi = [2500, 1750, 1350, 1100]

            ## Small avalanche (1000 - 5000 m³)
            elif 1000 < aval_size <= 5000:
                user_avalsize = 'S'
                ## Avalanche above 1500m 
                if aval_alti >= 1500:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.215, 0.235, 0.28, 0.37]
                        y_xi = [2500, 2000, 1500, 1200]
                        
                    ## RP 150
                    elif str(rp).strip() == '150':
                        mu_300 = [0.215, 0.235, 0.28, 0.37]
                        mu_100 = [0.225, 0.245, 0.29, 0.38]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [2500, 2000, 1500, 1200]

                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.225, 0.245, 0.29, 0.38]
                        y_xi = [2500, 2000, 1500, 1200]
                     
                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu =  [0.23, 0.25, 0.30, 0.39]
                        y_xi =  [2500, 2000, 1500, 1200]
               
                ## Avalanche below 1500m and above 1000m
                elif 1000 < aval_alti <= 1500:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.23, 0.25, 0.3, 0.38]
                        y_xi = [2250, 1750, 1350, 1100]

                    ## RP 150
                    elif str(rp).strip() == '150':
                        mu_300 = [0.23, 0.25, 0.3, 0.38]
                        mu_100 = [0.24, 0.26, 0.31, 0.39]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [2250, 1750, 1350, 1100]

                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.24, 0.26, 0.31, 0.39]
                        y_xi = [2250, 1750, 1350, 1100]

                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu = [0.245, 0.265, 0.315, 0.4]
                        y_xi = [2250, 1750, 1350, 1100]

                ## Avalanche below 1000m
                elif aval_alti <= 1000:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.245, 0.265, 0.31, 0.4]
                        y_xi = [2000, 1500, 1200, 1000]
                    
                    ## RP 150
                    elif str(rp).strip() == '150':
                        mu_300 = [0.245, 0.265, 0.31, 0.4]
                        mu_100 = [0.255, 0.275, 0.32, 0.41]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [2000, 1500, 1200, 1000]

                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.255, 0.275, 0.32, 0.41]
                        y_xi = [2000, 1500, 1200, 1000]
                    
                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu = [0.26, 0.285, 0.33, 0.42]
                        y_xi = [2000, 1500, 1200, 1000]

            ## Tiny avalanche (< 1000 m³)
            elif aval_size <= 1000:
                user_avalsize = 'XS'
                ## Avalanche above 1500m 
                if aval_alti >= 1500:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.26, 0.275, 0.31, 0.42]
                        y_xi = [1750, 1500, 1250, 1050]

                    ## RP 150
                    elif str(rp).strip() == '150':
                        mu_300 = [0.26, 0.275, 0.31, 0.42]
                        mu_100 = [0.265, 0.28, 0.32, 0.43]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [1750, 1500, 1250, 1050]
                    
                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.265, 0.28, 0.32, 0.43]
                        y_xi = [1750, 1500, 1250, 1050]

                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu =  [0.27,0.285,0.33,0.44]
                        y_xi =  [1750,1500,1250,1050]

                ## Avalanche below 1500m and above 1000m
                elif 1000 < aval_alti <= 1500:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.27, 0.29, 0.33, 0.43]
                        y_xi = [1600, 1400, 1180, 1000]

                    ## RP 150
                    elif str(rp).strip() == '150':
                        mu_300 = [0.275, 0.295, 0.34, 0.44]
                        mu_100 = [0.265, 0.28, 0.32, 0.43]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [1600, 1400, 1180, 1000]
                        
                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.275, 0.295, 0.34, 0.44]
                        y_xi = [1600,1400,1180,1000]

                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu =  [0.28,0.3,0.345,0.45]
                        y_xi =  [1600,1400,1180,1000]

                ## Avalanche below 1000m
                elif aval_alti <= 1000:
                    ## RP 300
                    if str(rp).strip() == '300':
                        y_mu = [0.28, 0.3, 0.34, 0.44]
                        y_xi = [1500, 1250, 1050, 900]
                    
                    ## RP 150
                    elif str(rp).strip() == '150':
                        mu_300 = [0.28, 0.3, 0.34, 0.44]
                        mu_100 = [0.285, 0.31, 0.35, 0.45]
                        
                        ## Calculate interpolated values
                        y_mu = [round(log_interpolate(mu_100[i], mu_300[i]), 3) for i in range(4)]
                        y_xi = [1500, 1250, 1050, 900]
                    
                    ## RP 100
                    elif str(rp).strip() == '100':
                        y_mu = [0.285, 0.31, 0.35, 0.45]
                        y_xi = [1500, 1250, 1050, 900]
                    
                    ## RP 30
                    elif str(rp).strip() == '30':
                        y_mu =  [0.29, 0.32, 0.36, 0.46]
                        y_xi =  [1500, 1250, 1050, 900]

            ## friction for 72h snow dif.
            if str(rp).strip() == '72h':
                ## XL Avalanche (>15.000 m³)
                if aval_size > 15000:
                    if aval_alti >= 1500:
                        y_mu = [0.112, 0.128, 0.175, 0.235]
                        y_xi = [4500, 3500, 2500, 2000]
                    elif 1000 < aval_alti <= 1500:
                        y_mu = [0.112, 0.128, 0.175, 0.235]
                        y_xi = [4000, 3000, 2200, 1800]
                    elif aval_alti <= 1000:
                        y_mu = [0.142, 0.205, 0.215, 0.265]
                        y_xi = [3500, 2500, 1900, 1600]

                ## L Avalanche (10.000–15.000 m³)
                elif 10000 < aval_size <= 15000:
                    if aval_alti >= 1500:
                        y_mu = [0.145, 0.16, 0.215, 0.275]
                        y_xi = [4000, 3000, 2000, 1500]
                    elif 1000 < aval_alti <= 1500:
                        y_mu = [0.155, 0.175, 0.225, 0.292]
                        y_xi = [3500, 2500, 1750, 1350]
                    elif aval_alti <= 1000:
                        y_mu = [0.175, 0.195, 0.235, 0.308]
                        y_xi = [3000, 2000, 1500, 1200]

                ## M Avalanche (5.000–10.000 m³)
                elif 5000 < aval_size <= 10000:
                    if aval_alti >= 1500:
                        y_mu = [0.185, 0.205, 0.26, 0.33]
                        y_xi = [3250, 2500, 1750, 1350]
                    elif 1000 < aval_alti <= 1500:
                        y_mu = [0.2, 0.22, 0.28, 0.34]
                        y_xi = [2900, 2100, 1530, 1200]
                    elif aval_alti <= 1000:
                        y_mu = [0.23, 0.25, 0.29, 0.37]
                        y_xi = [2500, 1750, 1350, 1100]

                ## S Avalanche (1.000–5.000 m³)
                elif 1000 < aval_size <= 5000:
                    if aval_alti >= 1500:
                        y_mu = [0.235, 0.25, 0.3, 0.39]
                        y_xi = [2500, 2000, 1500, 1200]
                    elif 1000 < aval_alti <= 1500:
                        y_mu = [0.245, 0.265, 0.315, 0.4]
                        y_xi = [2250, 1750, 1350, 1100]
                    elif aval_alti <= 1000:
                        y_mu = [0.26, 0.285, 0.33, 0.42]
                        y_xi = [2000, 1500, 1200, 1000]

                ## XS Avalanche (<1.000 m³)
                elif aval_size <= 1000:
                    if aval_alti >= 1500:
                        y_mu = [0.27, 0.285, 0.33, 0.44]
                        y_xi = [1750, 1500, 1250, 1050]
                    elif 1000 < aval_alti <= 1500:
                        y_mu = [0.265, 0.28, 0.32, 0.43]
                        y_xi = [1600, 1400, 1180, 1000]
                    elif aval_alti <= 1000:
                        y_mu = [0.285, 0.31, 0.35, 0.45]
                        y_xi = [1500, 1250, 1050, 900]

            ## Write friction and gpp params to lists
            mue_list.append((aval_id, y_mu))
            xi_list.append((aval_id, y_xi))
            dz_grenz_list.append((aval_id, dz_grenz))
            dz_a_list.append((aval_id, dz_a))
            dz_p_list.append((aval_id, dz_p))
                
        ## Fillsink
        ## processing.algorithmHelp("saga:fillsinks")
        if user_fs_yn == 'Y':
            ## saga fill sink outpath
            dem_fs_sdat = os.path.join(folder_path, f"DEM_fillsink.sdat")

            ## Convert SDAT to TIF
            processing.run("saga:fillsinks", {
                'DEM': infile_z,
                'MINSLOPE': 0.01,
                'RESULT': dem_fs_sdat
            })
            
            ## fill sink tif outpath
            dem_fs = os.path.join(folder_path, f"DEM_fillsink.tif")

            ## Convert SDAT to TIF
            processing.run("gdal:translate", {
                'INPUT': dem_fs_sdat,
                'OUTPUT': dem_fs,
                'FORMAT': 'GTiff'
            })

            DEM_fs = iface.addRasterLayer(dem_fs, "DEM_fs")

            ## verify file exists and is readable
            if not os.path.exists(dem_fs_sdat):
                print("SDAT file not created")
            if not os.path.exists(dem_fs):
                print("TIF file not created")
            
            print("---------------------------------------------------------------")
            print("+++ Algorithm saga:fillsinks complete +++")
            print("\nGenerated DEM: ", "\n",dem_fs)

        if user_fs_yn == 'Y':
            infile_z = dem_fs
            src_ds = osgeo.gdal.Open(infile_z)
            print(f"Fill Sink DEM used: {infile_z}")

        ## Get raster dimensions and properties from source
        zncol, znrow = src_ds.RasterXSize, src_ds.RasterYSize
        nc = zncol * znrow  ## Total number of cells
        xdisp, ydisp = zncol//2, znrow//2  ## Center points

        ## Initialize all arrays with same source dimensions
        src_ar = src_ds.ReadAsArray()
        z = src_ds.ReadAsArray()
        dst_ar = src_ds.ReadAsArray()
        dst_comb = src_ds.ReadAsArray()
        dst_PRA = src_ds.ReadAsArray()
        dst_mu = src_ds.ReadAsArray()
        dst_xi = src_ds.ReadAsArray()
        
        ## Get cell sizes
        cellSizeX = src_ds.GetGeoTransform()[1]
        cellSizeY = src_ds.GetGeoTransform()[5]
        
        ## Get no data
        no = src_ds.GetRasterBand(1).GetNoDataValue()
        
        ## Inidial Values
        max_val_2 = 0
        min_val_2 = 9000
        zaehler = 0
        curv = 0
        
        ## Extend
        ext = dem.extent()
        xmin = ext.xMinimum()
        xmax = ext.xMaximum()
        ymin = ext.yMinimum()
        ymax = ext.yMaximum()
        
        ## Geographic boundaries
        coord = [xmin,ymin,xmax,ymax]
        
        print("---------------------------------------------------------------")
        print("+++ PCM avalanche runout calculation starts +++")
        print("\nPRA specific friction paramter:")
        
        if user_lawis_yn == "Y":
            print("\n\tLAWIS snow profile data:")
        
        ## print lists
        m2d_l = []
        PRA_d0 = []
        D0_print = []
        PCM_V_individual = []
        PCM_P_individual = []
        PCM_V_combined = []
        PCM_P_combined = []
        
        ## acces PRA file
        for idx, feature in gdf.iterrows():
            geom = feature['geometry']## get feature geometry
            PRA_id = int(feature[0])  ## ID is at index 0
            mue_pra_id = int(feature['ID'])  ## Access the id colum
            d0 = int(feature[5])  ## Field name for 3TNSS is at index 4
            PRA_d0.append(d0) ## append PRA 3TNSS for print
                        
            ## deep propagation with LAWIS data
            if user_lawis_yn == "Y":
                ## find matching LAWIS profile
                for idx, lpt in point_gdf.iterrows():
                    LAWIS_PRA_ID = lpt['PRA_ID']
                    if int(PRA_id) == int(LAWIS_PRA_ID):
                        ## Get SD and ECT values
                        sd_val = lpt['SD']
                        ect_val = lpt['ECT']
                        weak_add = 0
                        if ect_val is not None and ect_val > 0:
                            weak_add = sd_val - ect_val
                            d0 = d0 + weak_add
                        else:
                            ## manual LAWIS input dialog
                            class ManualEntryDialog(QDialog):
                                def __init__(self, pdf_url):
                                    super().__init__()
                                    self.setWindowTitle("Manual Snowdepth Entry")
                                    self.weak_add = 0
                                    self.valid = False
                                    layout = QVBoxLayout()
                                    
                                    ## Create visible, clickable link with actual URL
                                    link_label = QLabel(
                                        f"Open snow profile: <a href='{pdf_url}'>{pdf_url}</a>"
                                    )
                                    link_label.setOpenExternalLinks(True)
                                    link_label.setTextInteractionFlags(link_label.textInteractionFlags() | Qt.TextBrowserInteraction)
                                    link_label.setTextFormat(Qt.RichText)

                                    layout.addWidget(link_label)

                                    ## Instructions and input
                                    layout.addWidget(QLabel(
                                        "Automatic processing failed.\n"
                                        "Please enter the additional snow depth manually:"
                                    ))

                                    self.input_field = QLineEdit()
                                    self.input_field.setPlaceholderText("e.g., 25.0")
                                    layout.addWidget(self.input_field)

                                    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
                                    button_box.accepted.connect(self.confirm)
                                    button_box.rejected.connect(self.reject)
                                    layout.addWidget(button_box)

                                    self.setLayout(layout)

                                def confirm(self):
                                    try:
                                        self.weak_add = float(self.input_field.text())
                                        self.valid = True
                                        self.accept()
                                    except ValueError:
                                        self.input_field.setPlaceholderText("Please enter a valid number.")

                            ## Get the PDF link
                            pdf_url = lpt.get('PDF', None)
                            if pdf_url:
                                app = QApplication.instance()
                                close_app = False
                                if app is None:
                                    app = QApplication(sys.argv)
                                    close_app = True

                                dialog = ManualEntryDialog(pdf_url)
                                result = dialog.exec_()

                                if dialog.valid:
                                    weak_add = dialog.weak_add
                                    d0 = d0 + weak_add
                                else:
                                    weak_add = 0

                                if close_app:
                                    app.quit()
                            else:
                                print("No PDF link found; skipping manual entry.")
                                weak_add = 0

                        ## Print or process the values
                        print(f"\t\tPRA ID: {PRA_id}, SD: {sd_val}, ECT: {ect_val}, weak_add: {weak_add}")
            
            D0_print.append((PRA_id, d0))

                        
            ## PRA raster mask
            r_mask_path = str(folder_path + '/' + f"_PRA{PRA_id}_mask.tif")
            
            ## Check friction values for each PRA
            y_mu = next((value for id, value in mue_list if id == mue_pra_id), None)
            y_xi = next((value for id, value in xi_list if id == mue_pra_id), None)
            dz_grenz = next((value for id, value in dz_grenz_list if id == mue_pra_id), None)
            dz_a = next((value for id, value in dz_a_list if id == mue_pra_id), None)
            dz_p = next((value for id, value in dz_p_list if id == mue_pra_id), None)
            
            ## print friction
            print(f"\tPRA {PRA_id} friction parameter:\n\t\tμ \t\t\t{y_mu}\n\t\tξ \t\t\t{y_xi}\n\t\tdz_grenz \t{dz_grenz}\n\t\tdz_a \t\t{dz_a}\n\t\tdz_p \t\t{dz_p} ")
            
            ## Calculation Curvature & Mue & Xi for DEM
            for i in range(znrow):
                for j in range(zncol):
                    ## Fortschrittsanzeige
                    if (src_ar[i,j] < min_val_2 and src_ar[i,j] > max_val_2 and i > k and j > k and i < (znrow-k) and j < (zncol-k)):
                        z5 = src_ar[i,j]
                        z2 = src_ar[i-k,j]
                        z4 = src_ar[i,j-k]
                        z6 = src_ar[i,j+k]
                        z8 = src_ar[i+k,j]
                        
                        ## Radius
                        hd1 = (z4+z6)/2-z5;
                        he1 = (z2+z8)/2-z5;
                        ## Vermeidung von Division durch 0
                        if (hd1 == 0 or he1 == 0):
                            dst_ar[i,j] = 0
                        else:
                            s2 = math.pow((2*k*cellSizeX),2);
                            d1 = (s2/(8*hd1) + hd1/2) * -1;
                            e1 = (s2/(8*he1) + he1/2) * -1;
                            
                            curv = (d1+e1)/2;
                            dst_ar[i,j] = curv;
                            
                    ## Curvature classes
                    ## flat:             less -5000
                    ## unchannelled:     -5000 to -1000
                    ## channelled:       -1000 to -250
                    ## gully:            -250  to  0

                    if(curv < -5000 or curv >= 0):
                        dst_mu[i,j] = y_mu[0]
                        dst_xi[i,j] = y_xi[0]
                    if(curv >= -5000 and curv < 1000 ):
                        dst_mu[i,j] = y_mu[1]
                        dst_xi[i,j] = y_xi[1]
                    if(curv >= -1000 and curv < 250 ):
                        dst_mu[i,j] = y_mu[2]
                        dst_xi[i,j] = y_xi[2]
                    if(curv >= -250 and curv < 0 ):
                        dst_mu[i,j] = y_mu[3]
                        dst_xi[i,j] = y_xi[3]

            ## tangent values
            dz_grenz_txt = dz_grenz
            dz_grenz_org = dz_grenz
            dz_grenz= math.tan(dz_grenz*math.pi/180)
            dz_grenz_auf = 5
            dz_a_org = dz_a
            dz_a_auf = -0.3
            dz_p_org = dz_p
            dz_p_auf = 0.5
            
            ## prepare d0 for PCM cacl
            m2d = (d0*10)/g

            ## Create a raster mask for the feature
            crs_rasterio = crsSrc.toWkt()
            with rasterio.open(r_mask_path, 'w',
                               driver='GTiff',
                               height=raster_height,
                               width=raster_width,
                               count=1,
                               dtype='uint8',
                               crs=crs_rasterio,
                               transform=raster_transform) as dst:

                mask = geometry_mask([geom], out_shape=(raster_height, raster_width),
                                     transform=raster_transform, invert=True)
                dst.write(mask.astype('uint8'), 1)

            ## Open the raster created at r_mask_path after writing
            with rasterio.open(r_mask_path) as src_r:
                cellSizeX2 = src_r.transform[0]
                cellSizeY2 = src_r.transform[4]
                zncol2 = src_r.width
                znrow2 = src_r.height
                r = src_r.read()

            if zncol != zncol2 or znrow != znrow2 or cellSizeX != cellSizeX2 or cellSizeY != cellSizeY2:
                print ("\n\t>>> Remark: Row or Column numbers of DTM and PRA do not match! <<<\n")
                
                ## Resample PRA
                ## processing.algorithmHelp("saga:resampling")
                exp = {'INPUT': r_mask_path,
                    'TARGET_USER_FITS':1,
                    'TARGET_USER_SIZE':cellSizeX,
                    'TARGET_USER_XMIN TARGET_USER_XMAX TARGET_USER_YMIN TARGET_USER_YMAX': PRA_final_path,
                    'OUTPUT': outfile_PRA_rs
                }
                result = processing.run("saga:resampling",exp )
                
                fileInfo = QFileInfo(outfile_PRA_rs)
                rLabel = fileInfo.baseName()
                
                ## add PRA raster file
                PRA_PCM = iface.addRasterLayer(outfile_PRA_rs,rLabel,'gdal')
                PRA_PCM.setCrs(crsSrc)
                
                print('\tExtent changed to : ',PRA.extent())
                
                ## PRA raster meta data
                infile_PRA = outfile_PRA_rs
                src_r = osgeo.gdal.Open(infile_PRA)
                r = src_r.read()
                cellSizeX2 = src_r.GetGeoTransform()[1]
                cellSizeY2 = src_r.GetGeoTransform()[5]
                zncol2 = src_r.RasterXSize
                znrow2 = src_r.RasterYSize
            
            xdisp = int(zncol / 2)
            ydisp = int(znrow / 2)
            
            ## Initialize velocity array 
            pcm_V = src_ds.ReadAsArray()
            
            ## Initialize pressure array 
            pcm_P = src_ds.ReadAsArray()
            
            ## Initialize starting mass array 
            ##pcm_SM = src_ds.ReadAsArray()
            
            ## Initialize rwr array 
            rwr = src_ds.ReadAsArray()
        
            no=src_ds.GetRasterBand(1).GetNoDataValue()
            
            def WriteRaster (dst_filename, raster):
                ## writes Raster for simulaiton Output
                format = "MEM"
                driver = gdal.GetDriverByName( format )
                dst_ds = driver.Create( dst_filename, len(raster[0]), len(raster),1,gdal.GDT_Float32)
                dst_ds.SetGeoTransform( src_ds.GetGeoTransform() )
                dst_ds.GetRasterBand(1).SetNoDataValue(0)
                dst_ds.GetRasterBand(1).WriteArray( raster )
                
                format = 'GTiff'
                driver = gdal.GetDriverByName(format)
                dst_ds_new = driver.CreateCopy(dst_filename, dst_ds)
                dst_ds = None
                
            def smooth_isolated_cells(pcm_V, pcm_P, min_neighbors=3):
                '''Smooths isolated cells within the avalanche flow by
                assigning them the mean value of their neighbors.
                Create copies to avoid modifying arrays during iteration'''
                
                pcm_V_smoothed = pcm_V.copy()
                pcm_P_smoothed = pcm_P.copy()
                rows, cols = pcm_V.shape
                cells_smoothed = 0
                
                ## Iterate through all cells
                for i in range(1, rows-1):
                    for j in range(1, cols-1):
                        ## Skip cells that already have velocity values
                        if pcm_V[i, j] <= 0:
                            ## Check neighbors (8-way connectivity)
                            neighbor_velocities = []
                            neighbor_pressures = []
                            neighbor_depostion = []
                            
                            for ni in range(i-1, i+2):
                                for nj in range(j-1, j+2):
                                    ## Skip the cell itself
                                    if ni == i and nj == j:
                                        continue
                                    
                                    ## Check if neighbor has a velocity value
                                    if 0 < ni < rows-1 and 0 < nj < cols-1 and pcm_V[ni, nj] > 0:
                                        neighbor_velocities.append(pcm_V[ni, nj])
                                        neighbor_pressures.append(pcm_P[ni, nj])
                            
                            ## If we have enough neighbors with values, fill in this cell
                            if len(neighbor_velocities) >= min_neighbors:
                                pcm_V_smoothed[i, j] = sum(neighbor_velocities) / len(neighbor_velocities)
                                pcm_P_smoothed[i, j] = sum(neighbor_pressures) / len(neighbor_pressures)
                                cells_smoothed += 1
                
                ##print(f"Smoothed {cells_smoothed} isolated cells surrounded by flow.")
                return pcm_V_smoothed, pcm_P_smoothed
            
            Lg = float(cellSizeX)
            Lu = float(math.sqrt(2*math.pow((cellSizeX),2)))
            
            Llist = [Lg,Lu,Lg,Lu,Lg,Lu,Lg,Lu]
            
            d8rev = [4,5,6,7,0,1,2,3]

            ####################################################################
            ## PREWORK PMC #####################################################

            ## fill dst_PRA grid with zeros(e.g. NODATA values -9999 or -99999)
            for i in range(znrow):
                for j in range(zncol):
                    pcm_V[i,j] = 0
                    pcm_P[i,j] = 0

            ## fill rwr grid with zeros (e.g. NODATA values -9999 or -99999)  
            for i in range(znrow):
                for j in range(zncol):
                    rwr[i,j] = 9999

            ## PCM calc for START Cells 
            i = 0
            j = 0
            ic = 0
            
            rowlist0 = []
            collist0 = []
            crowlist = []
            ccollist = []
            release_cells = []
            dzlist = [0,0,0,0,0,0,0,0]

            ## Aggregation factors
            aggfact				= 444   ## to use if original cellsize should be used
            aggfact				= 10    ## cellsize (reduce/aggregate cellsize by factor)
            step				= 10    ## for output (comand line)
            vmin 				= 0.001 ## minimu Velocity
            r 					= r[0]  ##
            mue 				= 0.155 ## only for start

            ## START INITIAL VELOCITY CALC
            for row in range(znrow):
                for col in range(zncol):
                    ## Check if this is a release cell
                    if (r[row,col] > 0):
                        ## Count and mark
                        ic = ic + 1
                        rwr[row, col] = 8888

                        ## Detect neighboring cells
                        rowlist0 = [row, row+1, row+1, row+1, row, row-1, row-1, row-1]
                        crowlist.extend(rowlist0)
                        collist0 = [col+1, col+1, col, col-1, col-1, col-1, col, col+1]
                        ccollist.extend(collist0)
                        
                        ## Get elevation values
                        zval0 = z[row, col]
                        zlist0 = [z[row, col+1], z[row+1, col+1], z[row+1, col], z[row+1, 
                                col-1], z[row, col-1], z[row-1, col-1],
                                  z[row-1, col], z[row-1, col+1]]
                        
                        ## Get elevation difference
                        k = 0
                        for k in range(len(zlist0)):
                            dzlist[k] = zval0 - zlist0[k]
                        
                        ## Potentially draining neighbors (cells with lower elevation)
                        zm_v = np.min(dzlist)  # Lowest z
                        zm_i = dzlist.index(np.min(dzlist))  # Index of the lowest z cell
                        zlow0 = [item for item in range(len(dzlist)) if dzlist[item] > 0]
                        
                        for k in range(len(zlow0)):
                            ## Get target cell coordinates
                            target_row = rowlist0[zlow0[k]]
                            target_col = collist0[zlow0[k]]
                            
                            ## Calculate velocity using your existing code
                            L = Llist[zlow0[k]]
                            dh = dzlist[zlow0[k]]
                            theta0 = math.atan(dh / L)
                            
                            ## Calculate velocity
                            if theta0 > mue:
                                ## Above critical angle - calculate velocity
                                a0 = g * (math.sin(theta0) - mue * math.cos(theta0))
                                b0 = -2 * L / m2d
                                Va0 = 0
                                Vb1 = math.sqrt(a0*m2d*(1-math.exp(b0))+Va0**2*math.exp(b0))
                            else:
                                ## Below critical angle - check neighbor velocities
                                Vb1list = [pcm_V[row, col+1], pcm_V[row+1, col+1], pcm_V[row+1, col], 
                                          pcm_V[row+1, col-1], pcm_V[row, col-1],
                                          pcm_V[row-1, col-1], pcm_V[row-1, col], pcm_V[row-1, col+1]]
                                Vb1 = np.max(Vb1list)
                                                            
                            ## Write velocity and pressure
                            pcm_V[target_row, target_col] = Vb1
                            kPa = (rho * Vb1**2 / 2) / 1000
                            pcm_P[target_row, target_col] = round(kPa, 2)
                            
                            ## Mark cell as processed
                            rwr[target_row, target_col] = 7777
            
            ####################################################################
            ## END PCM STARING VELOCITY ########################################

            zaehler = 0
            abbruch = 0
            cellsum = 0
            breaknr0 = -1
            breaknr = 0
            
            ## inidial velocities to 0
            Vb0 = 0
            Vb1 = 0
            
            ## inidial m2d0 list
            m2dlsit = []

            ## open PRA_final shp as gdf
            gdf = gpd.read_file(PRA_final_path)

            def ensure_within_range(value, max_value):
                return max(0, min(value, max_value - 1))

            def ensure_row_within_range(row, max_row):
                return max(0, min(row, max_row - 1))
            
            ## Initialize velocity memory grid once at the start of your program
            if 'velocity_memory' not in globals():
                velocity_memory = np.zeros_like(z)
            
            ## add iteration max - for terrain traps 
            iteration_count = 0
            iteration_max = 1000

            ####################################################################
            ## Start PCM Flowpath, max. Velocity, max. Pressure ################
            ## main loop
            while len(crowlist) != 0:
                ## break endless loops
                iteration_count += 1
                if iteration_count > iteration_max:
                    print("Warning: Maximum iteration count reached. Exiting loop early.")
                    break
                
                dz_grenz = dz_grenz_org
                dz_grenz= math.tan(dz_grenz*math.pi/180)
                dz_a = dz_a_org
                dz_p = dz_p_org
            
                breaknr0  = breaknr
                abbruch = abbruch + 1
                zaehler = zaehler + 1
                cellsum = cellsum + len(crowlist)
                
                i = 0
                crowlist0 = []
                ccollist0 = []
                cntVb1 = 0
                
                MAX_I = 10000       ## max iterations for outer loop
                MAX_J = 500         ## max iterations for middle loop
                MAX_O = 500         ## max iterations for inner loop

                ##for i in range(len(crowlist)):
                for i in range(min(len(crowlist), MAX_I)):
                    source_row = crowlist[i]
                    source_col = ccollist[i]
                    
                    if len(crowlist) != len(ccollist):
                        print ("Error: Length of crowlist and ccollist differ!")
                        break
                    
                    ## z value of process cell
                    zval = z[source_row,source_col]
                    
                    ## Check and add the values of the neighboring cell to zlist
                    ## D8 z values
                    zlist = []
                    if 0 <= source_row < znrow and 0 <= source_col+1 < zncol:
                        zlist.append(z[source_row, source_col+1])
                    if 0 <= source_row+1 < znrow and 0 <= source_col+1 < zncol:
                        zlist.append(z[source_row+1, source_col+1])
                    if 0 <= source_row+1 < znrow and 0 <= source_col < zncol:
                        zlist.append(z[source_row+1, source_col])
                    if 0 <= source_row+1 < znrow and 0 <= source_col-1 < zncol:
                        zlist.append(z[source_row+1, source_col-1])
                    if 0 <= source_row < znrow and 0 <= source_col-1 < zncol:
                        zlist.append(z[source_row, source_col-1])
                    if 0 <= source_row-1 < znrow and 0 <= source_col-1 < zncol:
                        zlist.append(z[source_row-1, source_col-1])
                    if 0 <= source_row-1 < znrow and 0 <= source_col < zncol:
                        zlist.append(z[source_row-1, source_col])
                    if 0 <= source_row-1 < znrow and 0 <= source_col+1 < zncol:
                        zlist.append(z[source_row-1, source_col+1])
                    
                    ## Generate rowlist with boundary checks
                    rowlist = [ensure_row_within_range(source_row, znrow),
                               ensure_row_within_range(source_row+1, znrow),
                               ensure_row_within_range(source_row+1, znrow),
                               ensure_row_within_range(source_row+1, znrow),
                               ensure_row_within_range(source_row, znrow),
                               ensure_row_within_range(source_row-1, znrow),
                               ensure_row_within_range(source_row-1, znrow),
                               ensure_row_within_range(source_row-1, znrow)]

                    ## Generate collist with boundary checks
                    collist = [ensure_within_range(source_col+1, dst_xi.shape[1]),
                               ensure_within_range(source_col+1, dst_xi.shape[1]),
                               ensure_within_range(source_col, dst_xi.shape[1]),
                               ensure_within_range(source_col-1, dst_xi.shape[1]),
                               ensure_within_range(source_col-1, dst_xi.shape[1]),
                               ensure_within_range(source_col-1, dst_xi.shape[1]),
                               ensure_within_range(source_col, dst_xi.shape[1]),
                               ensure_within_range(source_col+1, dst_xi.shape[1])]

                    ## Add D8 PCM velocities values to pcmlist
                    pcmlist = []

                    if 0 <= source_row < znrow and 0 <= source_col+1 < zncol:
                        pcmlist.append(pcm_V[source_row, source_col+1])
                    if 0 <= source_row+1 < znrow and 0 <= source_col+1 < zncol:
                        pcmlist.append(pcm_V[source_row+1, source_col+1])
                    if 0 <= source_row+1 < znrow and 0 <= source_col < zncol:
                        pcmlist.append(pcm_V[source_row+1, source_col])
                    if 0 <= source_row+1 < znrow and 0 <= source_col-1 < zncol:
                        pcmlist.append(pcm_V[source_row+1, source_col-1])
                    if 0 <= source_row < znrow and 0 <= source_col-1 < zncol:
                        pcmlist.append(pcm_V[source_row, source_col-1])
                    if 0 <= source_row-1 < znrow and 0 <= source_col-1 < zncol:
                        pcmlist.append(pcm_V[source_row-1, source_col-1])
                    if 0 <= source_row-1 < znrow and 0 <= source_col < zncol:
                        pcmlist.append(pcm_V[source_row-1, source_col])
                    if 0 <= source_row-1 < znrow and 0 <= source_col+1 < zncol:
                        pcmlist.append(pcm_V[source_row-1, source_col+1])
            
                    ## Add D8 rwr value list to rwrlist 
                    rwrlist = []
                    if 0 <= source_row < znrow and 0 <= source_col+1 < zncol:
                        rwrlist.append(rwr[source_row, source_col+1])
                    if 0 <= source_row+1 < znrow and 0 <= source_col+1 < zncol:
                        rwrlist.append(rwr[source_row+1, source_col+1])
                    if 0 <= source_row+1 < znrow and 0 <= source_col < zncol:
                        rwrlist.append(rwr[source_row+1, source_col])
                    if 0 <= source_row+1 < znrow and 0 <= source_col-1 < zncol:
                        rwrlist.append(rwr[source_row+1, source_col-1])
                    if 0 <= source_row < znrow and 0 <= source_col-1 < zncol:
                        rwrlist.append(rwr[source_row, source_col-1])
                    if 0 <= source_row-1 < znrow and 0 <= source_col-1 < zncol:
                        rwrlist.append(rwr[source_row-1, source_col-1])
                    if 0 <= source_row-1 < znrow and 0 <= source_col < zncol:
                        rwrlist.append(rwr[source_row-1, source_col])
                    if 0 <= source_row-1 < znrow and 0 <= source_col+1 < zncol:
                        rwrlist.append(rwr[source_row-1, source_col+1])
                    
                    ## calc. propagation if cell is lower than processing cell
                    if np.min(rwrlist) >= 5555 and zval > 0:
                        k=0
                        
                        for k in range(len(zlist)):
                            dzlist[k] = zval - zlist[k]
                        
                        ## indices are stored in zlow vector
                        zalow = [item for item in range(len(zlist)) if zlist[item] <= zval]

                        cntVb1 = 0
                        zlow = []
            
                        ## Adjust GPP parameter
                        if Vb0 < 10 or Vb1 < 10:
                            dz_grenz = dz_grenz_org - dz_grenz_auf
                            dz_grenz= math.tan(dz_grenz*math.pi/180)
                            dz_a = dz_a_org
                            dz_p = dz_p_org

                        if Vb0 > 10 or Vb1 > 10:
                            dz_grenz = dz_grenz_org + dz_grenz_auf
                            dz_grenz= math.tan(dz_grenz*math.pi/180)
                            dz_a = dz_a_org + dz_a_auf * 1
                            dz_p = dz_p_org + dz_p_auf * 1

                        if Vb0 > 15 or Vb1 > 15:
                            dz_grenz = dz_grenz_org + dz_grenz_auf * 1.5
                            dz_grenz= math.tan(dz_grenz*math.pi/180)
                            dz_a = dz_a_org + dz_a_auf * 2
                            dz_p = dz_p_org + dz_p_auf * 2
                            
                        if Vb0 > 20 or Vb1 > 20:
                            dz_grenz = dz_grenz_org + dz_grenz_auf * 2
                            dz_grenz= math.tan(dz_grenz*math.pi/180)
                            dz_a = dz_a_org + dz_a_auf * 3
                            dz_p = dz_p_org + dz_p_auf * 3
                            
                        if Vb0 > 25 or Vb1 > 25:
                            dz_grenz = dz_grenz_org + dz_grenz_auf * 2.5
                            dz_grenz= math.tan(dz_grenz*math.pi/180)
                            dz_a = dz_a_org + dz_a_auf * 4
                            dz_p = dz_p_org + dz_p_auf * 4
                            
                        if Vb0 > 30 or Vb1 > 30:
                            dz_grenz = dz_grenz_org + dz_grenz_auf * 3
                            dz_grenz= math.tan(dz_grenz*math.pi/180)
                            dz_a = dz_a_org + dz_a_auf * 5
                            dz_p = dz_p_org + dz_p_auf * 5
                                    
                        ##for j in range(len(zalow)):
                        for j in range(min(len(zalow), MAX_J)):
                            
                            row = rowlist[zalow[j]]
                            col = collist[zalow[j]]
                            
                            ## get Mu and Xi from calculation with curvature (see above), Mue and Xi are variable for each cell
                            Xi = dst_xi[row,col]
                            mue = dst_mu[row,col]
                            
                            dzmin = np.min(dzlist)                          ## reverse order of D8, needed to find the impulse direction
                            dzminindx = dzlist.index(np.min(dzlist))        ## find minimum in D8, gives the impulse to the process cell
                            dzrevindx = d8rev[dzminindx]                    ## find the index from which the impulse is coming
                            
                            ## Step 1: dip slope (inclination)
                            dipbeta = [0 for zncol in range(len(dzlist))]   ## create empty list
                            for m in range(len(dzlist)):
                                dipbeta[m] = dzlist[m]/Llist[m]             ## calc dip angle
                            dipbetadz = dipbeta
                            
                            ## Step 2: calc relative dip slope
                            diprlv = [0 for zncol in range(len(dzlist))]    ## create empty list
                            for m in range(len(dzlist)):
                                diprlv[m] = dipbeta[m]/dz_grenz             ## calc of realative dip angle
                            
                            ## Step 3: exclude cells with relative inclination less then max dip angle
                            diprlvmax = np.max(diprlv)                      ## find max of relative dip angle
                            
                            if diprlvmax <= dz_grenz and diprlvmax <= 1:    ## calc max^propagation exponent if dip anlge is smaller max dip angle and smaller 1
                                                                            ## else only use the cell with the highest slope angle
                                diprlvmax = pow(np.max(diprlv),dz_a)        ## propagation exponent only used when inclination less 1 (=45deg) #original
                                
                                ## Step 4: calc propability intervall with impulse cell from above
                                dipbeta[dzrevindx] = dipbeta[dzrevindx]*dz_p ## multiplied by persitence factor
                                
                                ## Step 4.1: select only cells with specific dz (combination of dz_grenz and threshold (percentage of dz maximum) 
                                for i in range(len(dzlist)):
                                    zlow = [item for item in range(len(dzlist)) if diprlv[item] >= diprlvmax]
                                
                            else:   ## if slope larger than threshold slope (dz_grenz) only this cell is used
                                zlow = [item for item in range(len(dzlist)) if diprlv[item] == diprlvmax]

                            ## Step 5: calc probability intervall
                            dipcumsum = 0
                            dipintv = [0 for zncol in range(len(dzlist))]
                            dipcnt = [0 for zncol in range(len(dzlist))]
                            l = 0

                            ####################################################
                            ## PCM Calculation #################################
                            for o in range(min(len(zlow), MAX_O)):
                                
                                dzmin = abs(dzlist[dzminindx])  ## dz minimum (i.e. the dz to the highest D8 cell)
                                Lmin = Llist[dzminindx]         ## length to this cell (streight or diagonal)
                                theta0 = math.atan(dzmin/Lmin)
                                
                                ## calculate slope to lower cells (index: z.low)
                                dh = dzlist[zlow[o]]            ## heigth difference
                                L = Llist[zlow[o]]              ## length (straight or diagonal)
                                theta1 = math.atan(dh / L)      ## slope angle to this cell
                                
                                ## Vb0 -> velocity of the processing cell to hand this velocity over to this (lower) cell in process
                                Vb0 = pcm_V[row,col]

                                ## if Vb0 is NA >> handle cell as start cell and calc Vb0 new
                                if Vb0 == 0:
                                    a0 = g * (math.sin(theta0) - mue * math.cos(theta0))
                                    b0 = -2 * L / m2d
                                    Va0 = 0
                                    if theta0 > mue:
                                        Vb0 = math.sqrt(a0*m2d*(1-math.exp(b0))+Va0**2*math.exp(b0))
                                    else:
                                        Vb0 = 0
                                        
                                ## if upstream segment steper or equal processing segment (cf. Perla et al. 1980, p. 201 between eq. 14 and 15)
                                Va = Vb0*math.cos(theta0-theta1)
                            
                                ## if upstream segment less step then processing segment (cf. Perla et al. 1980, p. 201 between eq. 15 and 16)
                                if theta0 <= theta1:
                                    Va = Vb0
                                else:
                                    Va = Vb0*math.cos(theta0-theta1)
 
                                ## prepare for Vb calc, introduce Vb1_term to find end of runout
                                a1 = g * (math.sin(theta1) - mue * math.cos(theta1))
                                b1 = -2 * L / (m2d)
                                
                                if theta1 > mue:
                                    Vb1 = math.sqrt(a1*m2d*(1-math.exp(b1))+Va**2*math.exp(b1))  ## calc Vb (Perla et al. 1980, eq. 13)
                                else:
                                    Vb1 = 0

                                ## if propagation cell but no Vb1 can be calculated
                                if not Vb1 or Vb1 <= 0 or Vb1 == float('nan'):
                                    Vb1 = 0
                                
                                ## Velocity and Pressure
                                if Vb1 > vmin:
                                    pcm_V[row,col] = round(Vb1, 2)          ##write suv. velocity to array
                                    kPa_b0 = (rho * Vb1**2 / 2) / 1000      ## calculate kPa from velocity
                                    pcm_P[row,col] = round(kPa_b0, 2)       ## write pressure to array   
                                else:
                                    pcm_V[row,col] = round(Vb0, 2)          ## write insuv. velocity to array
                                    kPa_b0 = (rho * Vb0**2 / 2) / 1000      ## calculate kPa from velocity
                                    pcm_P[row,col] = round(kPa_b0, 2)       ## write pressure to array
                                            
                                if rwr[rowlist[zlow[o]],collist[zlow[o]]] == 9999 and Vb1 > vmin:
                                        crowlist0.extend([rowlist[zlow[o]]])
                                        ccollist0.extend([collist[zlow[o]]])
                                        rwr[row,col] = 5555
                                    
                crowlist = crowlist0
                ccollist = ccollist0

            ####################################################################
            ## GPP_PCM flowpath simulatiion is finished ########################
            
            ## Apply smoothing to fill in isolated cells
            pcm_V, pcm_P = smooth_isolated_cells(pcm_V, pcm_P, min_neighbors=3)
            

            ####################################################################
            ## Output ##########################################################

            ## Name + parameters for VELOCITY
            individual_outfile_aval = ("_V_" + d0_rp)
            
            ## Name + parameters for Pressure
            individual_outfile_aval_P = ("_P_" + d0_rp)
            
            ## individual  outfiles
            if user_output_option == 'individual PRAs':
                ## Add debugging here
                non_zero_v = np.count_nonzero(pcm_V)
                non_zero_p = np.count_nonzero(pcm_P)
                
                ## Define the subgroup name for the specific PRA
                subgroup_name = f"PRA {PRA_id}"
                subgroup = QgsLayerTreeGroup(subgroup_name)
                
                ## Add the subgroup inside the PCM results group
                pcm_group.addChildNode(subgroup)
                
                ## VELOCITY
                ## Generate a unique filename for each iteration
                iteration_filename_V = os.path.join(folder_path, f"PRA{int(round(feature['ID']))}{individual_outfile_aval}.tif")
                PCM_V_individual.append(iteration_filename_V)
                WriteRaster(iteration_filename_V, pcm_V)
                
                ## info and label
                fileInfo_V = QFileInfo(iteration_filename_V)
                rLabel_V = fileInfo_V.baseName()
                aval_V = QgsRasterLayer(iteration_filename_V, rLabel_V, 'gdal')
                QgsProject.instance().addMapLayer(aval_V, False)
                subgroup.addLayer(aval_V)
                aval_V.setCrs(crsSrc)

                ## Apply flexible color table
                renderer_V = create_flexible_colortable(aval_V, num_classes=7, method='sqrt', layer_type='velocity')                
                aval_V.setRenderer(renderer_V)
                aval_V.setOpacity(0.75)
                aval_V.triggerRepaint()

                ## PRESSURE
                ## Generate a unique filename for each iteration
                iteration_filename_P = os.path.join(folder_path, f"PRA{int(round(feature['ID']))}{individual_outfile_aval_P}.tif")
                PCM_P_individual.append(iteration_filename_P)
                WriteRaster(iteration_filename_P, pcm_P)

                ## add pcm_V Velocities
                fileInfo_P = QFileInfo(iteration_filename_P)
                rLabel_P = fileInfo_P.baseName()
                aval_P = QgsRasterLayer(iteration_filename_P, rLabel_P, 'gdal')
                QgsProject.instance().addMapLayer(aval_P, False)
                subgroup.addLayer(aval_P)
                aval_P.setCrs(crsSrc)

                ## Apply flexible color table
                renderer_P = create_flexible_colortable(aval_P, num_classes=7, method='sqrt', layer_type='pressure')                
                aval_P.setRenderer(renderer_P)
                aval_P.setOpacity(0.75)
                aval_P.triggerRepaint()

            ####################################################################
            ## combined VELOCITY outfiles
            elif user_output_option == 'combined PRAs':
                
                ## Path to combined VELOCITY
                outfile_aval_V = os.path.join(folder_path, f"c{individual_outfile_aval}.tif")

                if not os.path.exists(outfile_aval_V):
                    ## Create a new raster file if it doesn't exist
                    WriteRaster(outfile_aval_V, pcm_V)
                else:
                    ## Read existing data first
                    with rasterio.open(outfile_aval_V, 'r') as aval_V_src:
                        existing_shape = aval_V_src.shape
                        profile = aval_V_src.profile
                        
                        ## Verify shapes match
                        if pcm_V.shape != existing_shape:
                            raise ValueError(f"Input data shape {pcm_V.shape} does not match existing raster shape {existing_shape}")
                        
                        ## Read the existing data
                        existing_data = aval_V_src.read(1)  # Assuming single band

                    ## Combine existing data with new data (pcm_P)
                    combined_data = np.maximum(existing_data, pcm_V)

                    ## Write the combined result back to the raster
                    with rasterio.open(outfile_aval_V, 'r+') as aval_V_dst:
                        aval_V_dst.write(combined_data, indexes=1)

                ####################################################################
                ## combined PRESSURE outfiles
                outfile_aval_P = os.path.join(folder_path, f"c{individual_outfile_aval_P}.tif")
                
                if not os.path.exists(outfile_aval_P):
                    ## Create a new raster file if it doesn't exist
                    WriteRaster(outfile_aval_P, pcm_P)
                else:
                    ## Read existing data first
                    with rasterio.open(outfile_aval_P, 'r') as aval_P_src:
                        existing_shape = aval_P_src.shape
                        profile = aval_P_src.profile
                        
                        ## Verify shapes match
                        if pcm_P.shape != existing_shape:
                            raise ValueError(f"Input data shape {pcm_P.shape} does not match existing raster shape {existing_shape}")
                        
                        ## Read the existing data
                        existing_data = aval_P_src.read(1)  # Assuming single band

                    ## Combine existing data with new data (pcm_P)
                    combined_data = np.maximum(existing_data, pcm_P)

                    ## Write the combined result back to the raster
                    with rasterio.open(outfile_aval_P, 'r+') as aval_P_dst:
                        aval_P_dst.write(combined_data, indexes=1)

            else:
                print("\tInvalid output format specified.")

        ########################################################################
        ## Add  combined VELOCITY results
        if user_output_option == 'combined PRAs':
            ## Get file info for labels
            fileInfo = QFileInfo(outfile_aval_V)
            rLabel = fileInfo.baseName()
            
            ## Add and style velocity raster
            aval_v = QgsRasterLayer(outfile_aval_V, rLabel, 'gdal')
            
            ## Add and style pressure raster
            aval_v = QgsRasterLayer(outfile_aval_V, rLabel, 'gdal')
            
            ## Get maximum value for styling
            provider = aval_v.dataProvider()
            stats = provider.bandStatistics(1, QgsRasterBandStats.All)
            avalV_max = stats.maximumValue
            
            ## Define raster shader
            shader = QgsRasterShader()
            color_ramp_shader = QgsColorRampShader()
            color_ramp_shader.setColorRampType(QgsColorRampShader.Discrete)
            
            ## Define color ramp items
            color_ramp_items = [
                    QgsColorRampShader.ColorRampItem(5, QtGui.QColor('#2b83ba'), '<= 5 m/s'),
                    QgsColorRampShader.ColorRampItem(10, QtGui.QColor('#abdda4'), '5–10 m/s'),
                    QgsColorRampShader.ColorRampItem(20, QtGui.QColor('#ffffbf'), '10–20 m/s'),
                    QgsColorRampShader.ColorRampItem(40, QtGui.QColor('#fdae61'), '20–40 m/s'),
                    QgsColorRampShader.ColorRampItem(avalV_max, QtGui.QColor('#d7191c'), '> 40 m/s')
            ]
            
            ## Apply styling
            color_ramp_shader.setColorRampItemList(color_ramp_items)
            shader.setRasterShaderFunction(color_ramp_shader)
            renderer = QgsSingleBandPseudoColorRenderer(aval_v.dataProvider(), 1, shader)
            aval_v.setRenderer(renderer)
            
            ## Add layer to QGIS
            QgsProject.instance().addMapLayer(aval_v, False)
            pcm_group.addLayer(aval_v)
            aval_v.setCrs(crsSrc)
            aval_v.renderer().setOpacity(0.52)
            aval_v.triggerRepaint()

            ########################################################################
            ## Add  combined PRESSURE results
            ## Get file info for labels
            fileInfo = QFileInfo(outfile_aval_P)
            rLabel = fileInfo.baseName()

            ## Add and style pressure raster
            aval_p = QgsRasterLayer(outfile_aval_P, rLabel, 'gdal')
            
            ## Get maximum value for styling
            provider = aval_v.dataProvider()
            stats = provider.bandStatistics(1, QgsRasterBandStats.All)
            avalP_max = stats.maximumValue
            
            ## Define raster shader
            shader = QgsRasterShader()
            color_ramp_shader = QgsColorRampShader()
            color_ramp_shader.setColorRampType(QgsColorRampShader.Discrete)
            
            ## Define color ramp items
            color_ramp_items = [
                    QgsColorRampShader.ColorRampItem(1, QtGui.QColor('#2b83ba'), '<= 1 kPa'),
                    QgsColorRampShader.ColorRampItem(10, QtGui.QColor('#abdda4'), '1–10 kPa'),
                    QgsColorRampShader.ColorRampItem(30, QtGui.QColor('#ffffbf'), '10–30 kPa'),
                    QgsColorRampShader.ColorRampItem(50, QtGui.QColor('#fdae61'), '30–50 kPa'),
                    QgsColorRampShader.ColorRampItem(avalP_max, QtGui.QColor('#d7191c'), '> 50 kPa')
            ]
            
            ## Apply styling
            color_ramp_shader.setColorRampItemList(color_ramp_items)
            shader.setRasterShaderFunction(color_ramp_shader)
            renderer = QgsSingleBandPseudoColorRenderer(aval_p.dataProvider(), 1, shader)
            aval_p.setRenderer(renderer)
            
            ## Add layer to QGIS
            QgsProject.instance().addMapLayer(aval_p, False)
            pcm_group.addLayer(aval_p)
            aval_p.setCrs(crsSrc)
            aval_p.renderer().setOpacity(0.52)
            aval_p.triggerRepaint()
        
        print("---------------------------------------------------------------")
        
        ## print results
        if user_lawis_yn != "Y":
            print("\n\tSnowdepth has been selected from PRA:")
            for pra_nr, d0_val in D0_print:
                print(f"\t\tPRA {pra_nr}\t\t\t{d0_val} cm")
        else:
            print("\n\tPRA snow depth with added snowpack from deep propagation:")
            for (pra_nr, d0_val), pra_d0 in zip(D0_print, PRA_d0):
                #print(f"\t\tPRA {pra_nr}\t\t\t{d0_val}cm\ttotal d0: {pra_d0}cm")
                print(f"\t\tPRA {pra_nr}\t{pra_d0}cm\t\t\ttotal d0: {d0_val}cm")

        print("---------------------------------------------------------------")
        if user_output_option != "combined PRAs":
            print("\n\tIndividual pressure simulation results:")
            for file_path in PCM_P_individual:
                filename_P = os.path.basename(file_path)  # Extract only the filename
                print(f"\t\t{filename_P}")
                
            print("\n\tIndividual velocity simulation results:")
            for file_path in PCM_P_individual:
                filename_V = os.path.basename(file_path) ## Extract only the filename
                print(f"\t\t{filename_V}")
        else:
            print("\n\tCombined pressure simulation results:")
            print("\t", os.path.basename(outfile_aval_P))
            
            print("\n\tCombined velocity simulation results:")
            print("\t", os.path.basename(outfile_aval_V))
            


        print("\nAvalanche Velocity an Pressure calculation is finished")
        print("---------------------------------------------------------------")
        
        ##set extent
        canvas = qgis.utils.iface.mapCanvas()
        canvas.setExtent(dem.extent())
        iface.mainWindow().blockSignals(False)
        
        ## Stop the timer
        PCM_end_time = time.time()

################################################################################
################################################################################
################################################################################

## preperation time
Prepare_elepsed_time = Prep_end_time - Prep_start_time

## Convert seconds to minutes and seconds
def format_time(seconds):
    if seconds > 60:
        minutes, seconds = divmod(seconds, 60)
        return f"{int(minutes)} min {seconds:.1f} sec"
    return f"{seconds:.1f} sec"

## Logic for saving PRA and PCM results
if saving_option == 1:
    ## run both parts of the script
    if selected_parts == 1:
        PRA_folder = create_new_folder("RESULTS_PRA")
        pcm_folder = create_new_folder("RESULTS_PCM")
        PRA_folder = PRA_folder.rstrip("/")
        pcm_folder = pcm_folder.rstrip("/")
        PRA_start_time = time.time()
        run_script("PRA", PRA_folder)
        PRA_end_time = time.time()
        PCM_start_time = time.time()
        run_script("PCM", pcm_folder)
        PCM_end_time = time.time()
        
        ## Calculate the elapsed time
        PRA_elapsed_time = PRA_end_time - PRA_start_time
        PCM_elapsed_time = PCM_end_time - PCM_start_time
        Total_elapsed_time = Prepare_elepsed_time + PRA_elapsed_time + PCM_elapsed_time
        
        ## print time
        print("+++ Time evaluation +++")
        print(f"\tPreparation processing time:\t{format_time(Prepare_elepsed_time)}")
        print(f"\tPRA processing time:\t\t\t{format_time(PRA_elapsed_time)}")
        print(f"\tPCM processing time:\t\t\t{format_time(PCM_elapsed_time)}")
        print(f"\tTotal processing time:\t\t\t{format_time(Total_elapsed_time)}")

    ## only run PRA
    elif selected_parts == 2:
        PRA_folder = create_new_folder("RESULTS_PRA")
        PRA_folder = PRA_folder.rstrip("/")
        PRA_start_time = time.time()
        run_script("PRA", PRA_folder)
        PRA_end_time = time.time()
        
        ## Calculate the elapsed time
        PRA_elapsed_time = PRA_end_time - PRA_start_time
        Total_elapsed_time = Prepare_elepsed_time + PRA_elapsed_time
        
        ## print time
        print("+++ Time evaluation +++")
        print(f"\tPreparation processing time:\t{format_time(Prepare_elepsed_time)}")
        print(f"\tPRA processing time:\t\t\t{format_time(PRA_elapsed_time)}")
        print(f"\tTotal processing time:\t\t\t{format_time(Total_elapsed_time)}")

    ## only run PCM
    elif selected_parts == 3:
        pcm_folder = create_new_folder("RESULTS_PCM")
        pcm_folder = pcm_folder.rstrip("/")
        PCM_start_time = time.time()
        run_script("PCM", pcm_folder)
        PCM_end_time = time.time()
        
        ## Calculate the elapsed time
        PCM_elapsed_time = PCM_end_time - PCM_start_time
        Total_elapsed_time = Prepare_elepsed_time + PCM_elapsed_time
        
        ## print time
        print("+++ Time evaluation +++")
        print(f"\tPreparation processing time:\t{format_time(Prepare_elepsed_time)}")
        print(f"\tPCM processing time:\t\t\t{format_time(PCM_elapsed_time)}")
        print(f"\tTotal processing time:\t\t\t{format_time(Total_elapsed_time)}")

################################################################################
elif saving_option == 2:
    if selected_parts == 1:
        PRA_folder = overwrite_existing_folder("RESULTS_PRA")
        pcm_folder = overwrite_existing_folder("RESULTS_PCM")
        PRA_start_time = time.time()
        run_script("PRA", PRA_folder)
        PRA_end_time = time.time()
        PRA_elapsed_time = PRA_end_time - PRA_start_time
        PCM_start_time = time.time()
        run_script("PCM", pcm_folder)
        PCM_end_time = time.time()
        
        ## Calculate the elapsed time
        PCM_elapsed_time = PCM_end_time - PCM_start_time
        Total_elapsed_time = Prepare_elepsed_time + PRA_elapsed_time + PCM_elapsed_time
        
        ## print time
        print("+++ Time evaluation +++")
        print(f"\tPreparation processing time:\t{format_time(Prepare_elepsed_time)}")
        print(f"\tPRA processing time:\t\t\t{format_time(PRA_elapsed_time)}")
        print(f"\tPCM processing time:\t\t\t{format_time(PCM_elapsed_time)}")
        print(f"\tTotal processing time:\t\t\t{format_time(Total_elapsed_time)}")


        
    elif selected_parts == 2:
        PRA_folder = overwrite_existing_folder("RESULTS_PRA")
        PRA_start_time = time.time()
        run_script("PRA", PRA_folder)
        PRA_end_time = time.time()
        
        ## Calculate the elapsed time
        PRA_elapsed_time = PRA_end_time - PRA_start_time
        Total_elapsed_time = Prepare_elepsed_time + PRA_elapsed_time
        
        ## print time
        print("+++ Time evaluation +++")
        print(f"\tPreparation processing time:\t{format_time(Prepare_elepsed_time)}")
        print(f"\tPRA processing time:\t\t\t{format_time(PRA_elapsed_time)}")
        print(f"\tTotal processing time:\t\t\t{format_time(Total_elapsed_time)}")

        
    elif selected_parts == 3:
        pcm_folder = overwrite_existing_folder("RESULTS_PCM")
        PCM_start_time = time.time()
        run_script("PCM", pcm_folder)
        PCM_end_time = time.time()

        ## Calculate the elapsed time
        PCM_elapsed_time = PCM_end_time - PCM_start_time
        Total_elapsed_time = Prepare_elepsed_time + PCM_elapsed_time
        
        ## print time
        print("+++ Time evaluation +++")
        print(f"\tPreparation processing time:\t{format_time(Prepare_elepsed_time)}")
        print(f"\tPCM processing time:\t\t\t{format_time(PCM_elapsed_time)}")
        print(f"\tTotal processing time:\t\t\t{format_time(Total_elapsed_time)}")
        
################################################################################
################################################################################




