import io
import pandas as pd

def validate_csv_content(content: bytes):
    """
    Validates that the file has text/CSV magic bytes and parses the first 50 rows 
    successfully using Pandas to ensure proper CSV structure.
    """
    if not content:
        raise ValueError("File content is empty")
        
    # Check magic bytes for common binary signatures
    magic = content[:4]
    binary_signatures = {
        b"\x89PNG": "PNG Image",
        b"GIF8": "GIF Image",
        b"PK\x03\x04": "ZIP/Archive/Jar",
        b"\x7fELF": "ELF Executable",
        b"%PDF": "PDF Document",
        b"\xff\xd8\xff": "JPEG Image"
    }
    
    for sig, name in binary_signatures.items():
        if content.startswith(sig):
            raise ValueError(f"Invalid file format: Detected {name} binary signature instead of CSV text")

    # Verify first 50 rows can be parsed as a valid CSV
    try:
        pd.read_csv(io.BytesIO(content), nrows=50)
    except Exception as e:
        raise ValueError(f"File content could not be parsed as CSV: {e}")

def scan_file_for_virus(content: bytes) -> bool:
    """
    Simulates an antivirus scanning pipeline.
    Checks for the standard EICAR anti-virus test file signature.
    Returns True if clean, False if infected.
    """
    # EICAR Standard Antivirus Test File signature
    eicar_sig = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"
    if eicar_sig in content:
        return False
        
    # Simulated scanning delay
    import time
    time.sleep(0.3)
    return True
