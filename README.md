# XNAT-Disease-Search
A modular Python-based pipeline designed to interact with the XNAT platform to identify, retrieve, and process patient data related to the diagnosis of espondilolistesis.
 
- This repository provides a modular, automated pipeline to process medical imaging and clinical data stored in XNAT. The pipeline identifies patients diagnosed with espondilolistesis by scanning clinical text reports, extracting T2-weighted MRI metadata, and generating a final filtered report of relevant patient cases.
 
## Pipeline Architecture
The project is built on an orchestrator script that manages three specialized modules:
 
automatization.py (Orchestrator): The master script that queries XNAT for all available projects, filters out completed ones (via PROYECTOS_YA_HECHOS), and triggers the processing sequence (Find -> Extract -> Join) for each active project.
 
find_espondilolistesis.py (Search Module): Scans local XNAT archive directories for clinical .txt reports. It performs case-insensitive matching for the keyword "espondilolistesis" and logs findings into a project-specific CSV.
 
extract_XNAT.py (Extraction Module): Connects to the XNAT API to retrieve subjects, analyzes DICOM files (checking for T2W sequences), extracts patient metadata (age, series descriptions), and constructs direct viewer/download URLs.
 
join.py (Merge Module): Performs an inner join between the "found" patients (from the search module) and the metadata extracted from XNAT. It generates a final CSV containing only the confirmed patients with their metadata and direct access links.
 
## Libraries
 
pyxnat, pydicom, pandas, subprocess, glob, csv, logging.
 
## How to Run
Configure Credentials: Update the XNAT_USER and XNAT_PASS in automatization.py and extract_XNAT.py.
 
- Security Note: It is highly recommended to use environment variables instead of hardcoding passwords.
 
- Execution: Run the master script to trigger the full pipeline:
 
## Execution
```
python automatization.py
```
 
Output: The pipeline generates a pipeline_global.log and a final filtered CSV for each project (e.g., pacientes_con_espondilolistesis_{project}.csv) located in the /find directory.
