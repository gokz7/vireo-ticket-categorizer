"""
run_all.py - Execute the full data pipeline sequentially.
Run from the project root: python src/run_all.py
"""
import subprocess
import sys
from pathlib import Path

def main():
    src_dir = Path(__file__).resolve().parent
    scripts = [
        "01_audit.py",
        "02_clean.py",
        "03_categorise.py",
        "04_validate.py",
        "05_charts.py",
        "06_business_number.py"
    ]

    print("Initiating Pipeline Execution...\n" + "-"*40)
    for script in scripts:
        script_path = src_dir / script
        if not script_path.exists():
            print(f"Skipping {script} - file not found.")
            continue
        
        print(f"Running {script}...")
        result = subprocess.run([sys.executable, str(script_path)])
        
        if result.returncode != 0:
            print(f"Error encountered in {script}. Halting pipeline.")
            sys.exit(result.returncode)
            
    print("-"*40 + "\nPipeline completed successfully.")

if __name__ == "__main__":
    main()