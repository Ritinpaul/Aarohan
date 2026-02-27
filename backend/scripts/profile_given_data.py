import os
import json
import fitz  # PyMuPDF
import pdfplumber
import concurrent.futures
from pathlib import Path
from tqdm import tqdm

TARGET_DIR = Path(r"d:\webDev\more-projects\hackathons\NCHX\given_data")
OUTPUT_DB = Path(r"d:\webDev\more-projects\hackathons\NCHX\backend\data\fingerprints.json")

def process_pdf(filepath: Path) -> dict:
    meta = {
        "filename": filepath.name,
        "type": filepath.parent.name,
        "size_bytes": filepath.stat().st_size,
        "pages": 0,
        "is_scanned": False,
        "text_length": 0,
        "error": None
    }
    
    try:
        # Check text length via PyMuPDF to classify as scanned vs digital
        with fitz.open(filepath) as doc:
            meta["pages"] = len(doc)
            text = ""
            for page in doc:
                text += page.get_text()
            meta["text_length"] = len(text)
            
            # Heuristic: If there is less than 50 chars of text per page, it's highly likely a scan
            if meta["text_length"] / max(1, meta["pages"]) < 50:
                meta["is_scanned"] = True
    except Exception as e:
        meta["error"] = str(e)
        
    return meta

def run_profiling():
    pdf_files = list(TARGET_DIR.rglob("*.pdf"))
    print(f"Starting profiling for {len(pdf_files)} PDFs in given_data...")
    
    results = []
    
    # Process concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = {executor.submit(process_pdf, f): f for f in pdf_files}
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(pdf_files)):
            results.append(future.result())
            
    # Aggregate stats
    stats = {
        "total_files": len(pdf_files),
        "total_pages": sum(r["pages"] for r in results if not r["error"]),
        "digital_pdfs": sum(1 for r in results if not r["is_scanned"] and not r["error"]),
        "scanned_pdfs": sum(1 for r in results if r["is_scanned"] and not r["error"]),
        "types": {}
    }
    
    for r in results:
        t = r["type"]
        if t not in stats["types"]:
            stats["types"][t] = 0
        stats["types"][t] += 1
        
    print("\nExtraction Summary:")
    print(json.dumps(stats, indent=2))
    
    OUTPUT_DB.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DB, "w") as f:
        json.dump({"stats": stats, "files": results}, f, indent=2)
        
    print(f"\nSaved fingerprints to {OUTPUT_DB}")

if __name__ == "__main__":
    run_profiling()
