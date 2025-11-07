import pandas as pd
from openpyxl import Workbook
from datetime import datetime
import os

async def generate_excel_report(data: list, department: str) -> str:
    """
    Generate Excel report for placement data
    """
    df = pd.DataFrame(data)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"placement_report_{department}_{timestamp}.xlsx"
    filepath = f"/tmp/{filename}"
    
    # Create Excel writer
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Placements', index=False)
    
    return filepath
