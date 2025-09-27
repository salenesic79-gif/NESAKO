import pandas as pd
import openpyxl
from datetime import datetime

class ExcelExpert:
    """Excel automatizacija i analiza"""
    
    def __init__(self):
        self.name = "Excel Expert"
        self.version = "1.0"
        self.capabilities = [
            "data_analysis", "chart_creation",
            "formula_generation", "automation"
        ]
    
    def analyze_data(self, file_path: str) -> dict:
        """Analizira Excel fajl"""
        try:
            df = pd.read_excel(file_path)
            return {
                "rows": len(df),
                "columns": len(df.columns),
                "summary": df.describe().to_dict(),
                "analysis_date": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def generate_formula(self, description: str) -> str:
        """Generiše Excel formulu"""
        formulas = {
            "sum": "=SUM(A1:A10)",
            "average": "=AVERAGE(A1:A10)",
            "vlookup": "=VLOOKUP(A1,B:C,2,FALSE)"
        }
        
        for key, formula in formulas.items():
            if key in description.lower():
                return formula
        
        return "=SUM(A1:A10)"  # Default
    
    def get_capabilities(self) -> list:
        return self.capabilities
