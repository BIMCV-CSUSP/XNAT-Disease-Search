from pyxnat import Interface
import pydicom
import pandas as pd
import os
import tempfile
import shutil
from datetime import datetime
import re
import sys

## IN ENGLISH:
# This script connects to an XNAT server, retrieves subjects from a specified project, and attempts 
# to extract T2-weighted (T2W) MRI data by accessing the numbered resources associated with each subject's 
# sessions and scans. It downloads files from these resources, checks if they are DICOM files, and extracts
# relevant metadata such as patient age, study description, and series descriptions.
# The script also constructs URLs for viewing and downloading the images directly from XNAT.
# Finally, it compiles the extracted information into a DataFrame and saves it as a CSV file.

# --- VALIDACIÓN DE ARGUMENTOS ---
if len(sys.argv) < 2:
    print("❌ Error: Falta el ID del proyecto.")
    sys.exit(1)

project = sys.argv[1] # <--- RECIBE EL PROYECTO
# ------------------------------

print(f"🔌 Conectando a XNAT para proyecto: {project}")

# Connect to XNAT
central = Interface(server="https://xnat",
                    user='your_user',
                    password="your_password") # <--- REPLACE IT WITH YOUR PASSWORD 

# #print projects
# projects = central.select.projects().get()
# print(f"Available projects: {projects}")

#FUNCIONA---------------------------------------------------------------------------------------------
# project = 'p0012025'

# Modified approach to access numbered resources with image links
def extract_t2w_data_from_resources(max_subjects=3):
    """
    Extract T2W data by accessing the numbered resources we found, including image links
    """
    
    print("=== ACCESSING NUMBERED RESOURCES WITH LINKS ===")
    
    subjects_list = central.select.project(project).subjects().get()
    print(len(subjects_list))
    if max_subjects:
        subjects_list = subjects_list[:max_subjects]
    
    results = []
    temp_dir = "temp_numbered_resources"
    
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    for i, subject_id in enumerate(subjects_list):
        print(f"\\nProcessing subject {i+1}/{len(subjects_list)}: {subject_id}")
        
        patient_record = {
            'subject_id': subject_id,
            'patient_age': None,
            'study_description': None,
            'series_descriptions': [],
            't2w_series': [],
            't2w_count': 0,
            'dicom_files_found': 0,
            'dicom_files_analyzed': 0
        }
        
        try:
            subject = central.select.project(project).subject(subject_id)
            print(subject)
            subject_label = subject.label()
            sessions = subject.experiments().get()
            
            for session_id in sessions:  # Just first session
                print(f"  Session: {session_id}")
                
                session = subject.experiment(session_id)
                patient_record['session_label'] = session.label()
                patient_record['viwer_url'] = construct_viewer_url(subject_id, session_id, experiment_label=subject_label)
                # Try session resources
                if hasattr(session, 'resources'):
                    resources = session.resources().get()
                    print(f"    Session resources: {resources}")
                    
                    for resource_id in resources:  # Try first resource
                        print(f"      Trying resource: {resource_id}")
                        try:
                            resource = session.resource(resource_id)
                            files = resource.files().get()
                            patient_record['dicom_files_found'] += len(files)
                            print(f"        Files found: {len(files)}")
                            
                            if files:
                                print(f"        Sample files: {files[:3]}")
                                
                                # Try to download and analyze first file
                                first_file = files[0]
                                safe_filename = f"{subject_id}_{resource_id}_{0}.tmp"
                                local_path = os.path.join(temp_dir, safe_filename)
                                
                                try:
                                    resource.file(first_file).get(local_path)
                                    file_size = os.path.getsize(local_path)
                                    print(f"        Downloaded {first_file}: {file_size} bytes")
                                    
                                    if file_size > 0:
                                        # Try to read as DICOM
                                        try:
                                            ds = pydicom.dcmread(local_path)
                                            patient_record['dicom_files_analyzed'] += 1
                                            
                                            print(f"        ✓ Successfully read as DICOM!")
                                            
                                            # Extract metadata
                                            patient_age = getattr(ds, 'PatientAge', None)
                                            study_desc = getattr(ds, 'StudyDescription', None)
                                            series_desc = getattr(ds, 'SeriesDescription', None)
                                            modality = getattr(ds, 'Modality', None)
                                            
                                            if patient_age and not patient_record['patient_age']:
                                                patient_record['patient_age'] = str(patient_age)
                                                print(f"        ✓ Patient Age: {patient_age}")
                                            
                                            if study_desc and not patient_record['study_description']:
                                                patient_record['study_description'] = str(study_desc)
                                                print(f"        ✓ Study Description: {study_desc}")
                                            
                                            if series_desc:
                                                series_str = str(series_desc)
                                                if series_str not in patient_record['series_descriptions']:
                                                    patient_record['series_descriptions'].append(series_str)
                                                    print(f"        ✓ Series Description: {series_desc}")
                                                
                                                # Check if T2W
                                                is_t2w = detect_t2w_sequence(series_desc, '', '', '')
                                                if is_t2w:
                                                    patient_record['t2w_series'].append(series_str)
                                                    patient_record['t2w_count'] += 1
                                                    print(f"        ✓ T2W sequence detected!")
                                                    
                                                    # Add image links for T2W sequences
                                                    patient_record['session_image_url'] = construct_session_url(subject_id, session_id)
                                                    patient_record['session_download_url'] = construct_session_download_url(subject_id, session_id, resource_id)
                                                    
                                            
                                            print(f"        Modality: {modality}")
                                            
                                        except Exception as dicom_error:
                                            print(f"        ✗ Not a valid DICOM: {dicom_error}")
                                            
                                            # Check file header
                                            with open(local_path, 'rb') as f:
                                                header = f.read(20)
                                                print(f"        File header: {header}")
                                    
                                    # Clean up
                                    os.remove(local_path)
                                    
                                except Exception as download_error:
                                    print(f"        ✗ Download error: {download_error}")
                        
                        except Exception as resource_error:
                            print(f"      ✗ Resource access error: {resource_error}")
                
                # Also try scan resources
                scans = session.scans().get()
                for scan_id in scans:  # Try first 2 scans
                    scan = session.scan(scan_id)
                    
                    if hasattr(scan, 'resources'):
                        scan_resources = scan.resources().get()
                        print(f"      Scan {scan_id} resources: {scan_resources}")
                        
                        for resource_id in scan_resources[:1]:  # Try first resource
                            try:
                                resource = scan.resource(resource_id)
                                files = resource.files().get()
                                print(f"        Scan resource {resource_id}: {len(files)} files")
                                
                                if files and patient_record['dicom_files_analyzed'] == 0:  # Only if we haven't found DICOM yet
                                    first_file = files[0]
                                    safe_filename = f"{subject_id}_{scan_id}_{resource_id}.tmp"
                                    local_path = os.path.join(temp_dir, safe_filename)
                                    
                                    try:
                                        resource.file(first_file).get(local_path)
                                        
                                        if os.path.getsize(local_path) > 0:
                                            try:
                                                ds = pydicom.dcmread(local_path)
                                                patient_record['dicom_files_analyzed'] += 1
                                                print(f"        ✓ Scan DICOM found!")
                                                
                                                # Extract same metadata as above
                                                if not patient_record['patient_age']:
                                                    age = getattr(ds, 'PatientAge', None)
                                                    if age:
                                                        patient_record['patient_age'] = str(age)
                                                        print(f"        ✓ Age from scan: {age}")
                                                
                                                series_desc = getattr(ds, 'SeriesDescription', None)
                                                if series_desc:
                                                    series_str = str(series_desc)
                                                    if series_str not in patient_record['series_descriptions']:
                                                        patient_record['series_descriptions'].append(series_str)
                                                    
                                                    if detect_t2w_sequence(series_desc, '', '', ''):
                                                        patient_record['t2w_series'].append(series_str)
                                                        patient_record['t2w_count'] += 1
                                                        print(f"        ✓ T2W from scan: {series_desc}")
                                                        
                                                        # Add image links for T2W sequences
                                                        patient_record['scan_image_url'] = construct_scan_url(subject_id, session_id, scan_id)
                                                        patient_record['scan_download_url'] = construct_scan_download_url(subject_id, session_id, scan_id, resource_id)
                                                        patient_record['viwer_url'] = construct_viewer_url(subject_id, session_id, experiment_label=subject_label)
                                            except:
                                                pass  # Not a DICOM file
                                        
                                        os.remove(local_path)
                                        
                                    except Exception as e:
                                        print(f"        Error with scan resource: {e}")
                                        
                            except Exception as e:
                                print(f"        Error accessing scan resource: {e}")
            
            results.append(patient_record)
            
            # Summary for this patient
            print(f"  Summary: Age={patient_record['patient_age']}, "
                  f"DICOM_analyzed={patient_record['dicom_files_analyzed']}, "
                  f"T2W_count={patient_record['t2w_count']}")
            
        except Exception as e:
            print(f"  ✗ Error processing subject: {e}")
            results.append(patient_record)
    
    # Clean up
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except:
        pass
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    print(f"\\n=== FINAL RESULTS ===")
    if not df.empty:
        print(f"Subjects processed: {len(df)}")
        
        success_count = (df['dicom_files_analyzed'] > 0).sum()
        age_count = df['patient_age'].notna().sum()
        t2w_count = df['t2w_count'].sum()
        
        print(f"DICOM files successfully analyzed: {df['dicom_files_analyzed'].sum()}")
        print(f"Subjects with patient age: {age_count}")
        print(f"Subjects with T2W sequences: {(df['t2w_count'] > 0).sum()}")
        print(f"Total T2W sequences found: {t2w_count}")
        
        if success_count > 0:
            successful_df = df[df['dicom_files_analyzed'] > 0]
            print(f"\\n=== SUCCESSFUL DATA EXTRACTION ===")
            display_cols = ['subject_id', 'patient_age', 'study_description', 't2w_count']
            available_cols = [col for col in display_cols if col in successful_df.columns]
            print(successful_df[available_cols].to_string())
            
            # Show T2W series found with links
            for _, row in successful_df.iterrows():
                if row['t2w_count'] > 0:
                    print(f"\\nT2W sequences for {row['subject_id']}:")
                    for seq in row['t2w_series']:
                        print(f"  - {seq}")
                    
                    # Show image links if available
                    if 'scan_image_url' in row and pd.notna(row['scan_image_url']):
                        print(f"  🔗 Scan URL: {row['scan_image_url']}")
                        print(f"  📥 Download URL: {row['scan_download_url']}")
                    elif 'session_image_url' in row and pd.notna(row['session_image_url']):
                        print(f"  🔗 Session URL: {row['session_image_url']}")
                        print(f"  📥 Download URL: {row['session_download_url']}")
    
    return df

def detect_t2w_sequence(series_desc, protocol_name, sequence_name, modality):
    """
    Lógica para detectar si es T2W basándose en texto.
    Devuelve True si parece ser T2.
    """
    desc = str(series_desc).upper() if series_desc else ""
    prot = str(protocol_name).upper() if protocol_name else ""
    
    # Palabras clave positivas
    t2_keywords = ['T2', 'T2W', 'FRFSE', 'FSE']
    # Palabras clave negativas (para evitar falsos positivos)
    exclude_keywords = ['T1', 'DWI', 'DIFFUSION', 'LOCALIZER', 'SCOUT', 'ADC']
    
    is_t2 = any(k in desc or k in prot for k in t2_keywords)
    is_excluded = any(k in desc or k in prot for k in exclude_keywords)
    
    return is_t2 and not is_excluded

def construct_viewer_url(subject_id, session_id, experiment_label=None):
    """
    Construct XNAT viewer URL for viewing images
    """
    base_url = "https://xnat"
    if experiment_label:
        return f"{base_url}/VIEWER/?subjectId={subject_id}&projectId={project}&experimentId={session_id}&experimentLabel={experiment_label}"
    else:
        return f"{base_url}/VIEWER/?subjectId={subject_id}&projectId={project}&experimentId={session_id}"

def construct_session_url(subject_id, session_id):
    """
    Construct XNAT web interface URL for the session
    """
    base_url = "https://xnat"
    return f"{base_url}/data/projects/{project}/subjects/{subject_id}/experiments/{session_id}"

def construct_session_download_url(subject_id, session_id, resource_id):
    """
    Construct direct download URL for session resource
    """
    base_url = "https://xnat"
    return f"{base_url}/data/projects/{project}/subjects/{subject_id}/experiments/{session_id}/resources/{resource_id}/files?format=zip"

def construct_scan_url(subject_id, session_id, scan_id):
    """
    Construct XNAT web interface URL for the scan
    """
    base_url = "https://xnat"
    return f"{base_url}/data/projects/{project}/subjects/{subject_id}/experiments/{session_id}/scans/{scan_id}"

def construct_scan_download_url(subject_id, session_id, scan_id, resource_id):
    """
    Construct direct download URL for scan resource
    """
    base_url = "https://xnat2"
    return f"{base_url}/data/projects/{project}/subjects/{subject_id}/experiments/{session_id}/scans/{scan_id}/resources/{resource_id}/files?format=zip"

def analyze_dicom_file(resource, file_name, patient_record, temp_dir, subject_id, session_id, file_idx):
    """
    Download and analyze a single DICOM file
    
    Returns:
        bool: True if file was successfully analyzed
    """
    
    try:
        # Create safe filename
        safe_filename = f"{subject_id}_{session_id}_{file_idx}.dcm"
        local_path = os.path.join(temp_dir, safe_filename)
        
        # Download file
        resource.file(file_name).get(local_path)
        
        if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
            # Read DICOM
            ds = pydicom.dcmread(local_path)
            
            # Extract patient age (only once per patient)
            if not patient_record['patient_age']:
                if hasattr(ds, 'PatientAge') and ds.PatientAge:
                    patient_record['patient_age'] = str(ds.PatientAge)
            
            # Extract study description (only once per patient)
            if not patient_record['study_description']:
                if hasattr(ds, 'StudyDescription') and ds.StudyDescription:
                    patient_record['study_description'] = str(ds.StudyDescription)
            
            # Extract series description
            series_desc = getattr(ds, 'SeriesDescription', '')
            protocol_name = getattr(ds, 'ProtocolName', '')
            sequence_name = getattr(ds, 'SequenceName', '')
            
            if series_desc and series_desc not in patient_record['series_descriptions']:
                patient_record['series_descriptions'].append(str(series_desc))
            
            # Check if T2W
            is_t2w = detect_t2w_sequence(series_desc, protocol_name, sequence_name, '')
            
            if is_t2w:
                t2w_description = str(series_desc) if series_desc else f"T2W_scan_{session_id}"
                if t2w_description not in patient_record['t2w_series']:
                    patient_record['t2w_series'].append(t2w_description)
                    patient_record['t2w_count'] += 1
            
            # Clean up
            os.remove(local_path)
            return True
            
    except Exception as e:
        print(f"        Error analyzing DICOM {file_name}: {e}")
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
        except:
            pass
        return False
    
    return False

# Run the resource-based extraction with image links
numbered_resources_df = extract_t2w_data_from_resources(max_subjects=len(central.select.project(project).subjects().get()))
numbered_resources_df.to_csv(f'/mnt/datalake/openmind/MedP-Midas/sgonzalez/radiomics-midas-new/code/find/project_{project}.csv', index=False)
print("saved")

# # Save results

# if not numbered_resources_df.empty:
#     numbered_resources_df.to_csv('t2w_data_with_links.csv', index=False)
#     print(f"\\nResults with image links saved to 't2w_data_with_links.csv'")
    
#     # Display sample results with links
#     print(f"\\n=== SAMPLE RESULTS WITH LINKS ===")
#     t2w_samples = numbered_resources_df[numbered_resources_df['t2w_count'] > 0]
#     if not t2w_samples.empty:
#         for _, row in t2w_samples.head().iterrows():
#             print(f"\\nSubject: {row['subject_id']}")
#             print(f"  Age: {row['patient_age']}")
#             print(f"  T2W sequences: {row['t2w_count']}")
            
#             # Show available links
#             link_cols = ['scan_image_url', 'scan_download_url', 'session_image_url', 'session_download_url']
#             for col in link_cols:
#                 if col in row and pd.notna(row[col]):
#                     print(f"  {col}: {row[col]}")