import os
import json
import importlib
import inspect
from typing import Dict, List, Any, Optional
from datetime import datetime

class ModuleManager:
    """Self-modifying sistem za dodavanje novih AI modula"""
    
    def __init__(self):
        self.modules_dir = os.path.join(os.path.dirname(__file__), 'modules')
        self.ensure_modules_directory()
        self.active_modules = {}
        self.module_registry = {}
        self.load_existing_modules()
    
    def ensure_modules_directory(self):
        """Kreira modules direktorijum ako ne postoji"""
        if not os.path.exists(self.modules_dir):
            os.makedirs(self.modules_dir)
            
        # Kreira __init__.py za modules paket
        init_file = os.path.join(self.modules_dir, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('# NESAKO AI Modules Package\n')
    
    def create_financial_analyzer_module(self):
        """Kreira finansijski analizator modul"""
        module_code = '''import requests
import json
from datetime import datetime, timedelta

class FinancialAnalyzer:
    """Napredni finansijski analizator"""
    
    def __init__(self):
        self.name = "Financial Analyzer"
        self.version = "1.0"
        self.capabilities = [
            "stock_analysis", "crypto_tracking", 
            "portfolio_management", "market_trends"
        ]
    
    def analyze_stock(self, symbol: str) -> dict:
        """Analizira akciju"""
        try:
            # Simulacija analize (u realnosti bi koristio API)
            return {
                "symbol": symbol,
                "analysis": f"Analiza za {symbol}",
                "recommendation": "HOLD",
                "confidence": 0.75,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def track_crypto(self, coin: str) -> dict:
        """Prati kripto valutu"""
        return {
            "coin": coin,
            "price_trend": "BULLISH",
            "volatility": "HIGH",
            "recommendation": "WATCH"
        }
    
    def get_capabilities(self) -> list:
        return self.capabilities
'''
        
        module_path = os.path.join(self.modules_dir, 'financial_analyzer.py')
        with open(module_path, 'w', encoding='utf-8') as f:
            f.write(module_code)
        
        return module_path
    
    def create_excel_expert_module(self):
        """Kreira Excel expert modul"""
        module_code = '''import pandas as pd
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
'''
        
        module_path = os.path.join(self.modules_dir, 'excel_expert.py')
        with open(module_path, 'w', encoding='utf-8') as f:
            f.write(module_code)
        
        return module_path
    
    def create_stock_tracker_module(self):
        """Kreira stock tracker modul"""
        module_code = '''import json
from datetime import datetime

class StockTracker:
    """Praćenje akcija i tržišnih trendova"""
    
    def __init__(self):
        self.name = "Stock Tracker"
        self.version = "1.0"
        self.capabilities = [
            "real_time_tracking", "alerts",
            "portfolio_monitoring", "trend_analysis"
        ]
        self.watchlist = []
    
    def add_to_watchlist(self, symbol: str) -> dict:
        """Dodaje akciju u watchlist"""
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)
            return {
                "status": "added",
                "symbol": symbol,
                "watchlist_size": len(self.watchlist)
            }
        return {"status": "already_exists", "symbol": symbol}
    
    def get_market_summary(self) -> dict:
        """Vraća pregled tržišta"""
        return {
            "market_status": "OPEN",
            "major_indices": {
                "S&P500": "+0.5%",
                "NASDAQ": "+0.8%",
                "DOW": "+0.3%"
            },
            "trending_stocks": ["AAPL", "TSLA", "MSFT"],
            "timestamp": datetime.now().isoformat()
        }
    
    def get_capabilities(self) -> list:
        return self.capabilities
'''
        
        module_path = os.path.join(self.modules_dir, 'stock_tracker.py')
        with open(module_path, 'w', encoding='utf-8') as f:
            f.write(module_code)
        
        return module_path
    
    def load_module(self, module_name: str) -> bool:
        """Učitava modul dinamički"""
        try:
            module_path = f'ai_assistant.modules.{module_name}'
            module = importlib.import_module(module_path)
            
            # Pronađi glavnu klasu u modulu
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and hasattr(obj, 'capabilities'):
                    instance = obj()
                    self.active_modules[module_name] = instance
                    self.module_registry[module_name] = {
                        'name': getattr(instance, 'name', module_name),
                        'version': getattr(instance, 'version', '1.0'),
                        'capabilities': instance.get_capabilities(),
                        'loaded_at': datetime.now().isoformat()
                    }
                    return True
            
            return False
            
        except Exception as e:
            print(f"Error loading module {module_name}: {e}")
            return False
    
    def create_and_load_default_modules(self):
        """Kreira i učitava default module"""
        modules_created = []
        
        # Kreira module
        financial_path = self.create_financial_analyzer_module()
        excel_path = self.create_excel_expert_module()
        stock_path = self.create_stock_tracker_module()
        
        modules_created.extend([
            'financial_analyzer',
            'excel_expert', 
            'stock_tracker'
        ])
        
        # Učitava module
        loaded_modules = []
        for module_name in modules_created:
            if self.load_module(module_name):
                loaded_modules.append(module_name)
        
        return {
            'created': modules_created,
            'loaded': loaded_modules,
            'total_active': len(self.active_modules)
        }
    
    def load_existing_modules(self):
        """Učitava postojeće module pri pokretanju"""
        if not os.path.exists(self.modules_dir):
            return
        
        for file in os.listdir(self.modules_dir):
            if file.endswith('.py') and file != '__init__.py':
                module_name = file[:-3]  # Ukloni .py
                self.load_module(module_name)
    
    def execute_module_function(self, module_name: str, function_name: str, *args, **kwargs):
        """Izvršava funkciju iz modula"""
        if module_name not in self.active_modules:
            return {"error": f"Module {module_name} not loaded"}
        
        module_instance = self.active_modules[module_name]
        
        if not hasattr(module_instance, function_name):
            return {"error": f"Function {function_name} not found in {module_name}"}
        
        try:
            result = getattr(module_instance, function_name)(*args, **kwargs)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}
    
    def get_module_status(self) -> dict:
        """Vraća status svih modula"""
        return {
            'active_modules': list(self.active_modules.keys()),
            'module_registry': self.module_registry,
            'total_modules': len(self.active_modules),
            'modules_directory': self.modules_dir
        }
    
    def detect_module_request(self, user_input: str) -> dict:
        """Detektuje zahtev za modul"""
        input_lower = user_input.lower()
        
        # Financial requests
        financial_keywords = [
            'akcije', 'stock', 'berza', 'investicije', 'portfolio',
            'kripto', 'bitcoin', 'ethereum', 'finansije', 'analiza tržišta'
        ]
        
        # Excel requests  
        excel_keywords = [
            'excel', 'spreadsheet', 'tabela', 'formula', 'grafik',
            'pivot', 'vlookup', 'suma', 'prosek', 'chart'
        ]
        
        # Stock tracking requests
        tracking_keywords = [
            'prati akcije', 'watchlist', 'alerti', 'praćenje',
            'trendovi', 'market summary', 'pregled tržišta'
        ]
        
        detected = []
        
        if any(keyword in input_lower for keyword in financial_keywords):
            detected.append({
                'module': 'financial_analyzer',
                'confidence': 0.8,
                'suggested_functions': ['analyze_stock', 'track_crypto']
            })
        
        if any(keyword in input_lower for keyword in excel_keywords):
            detected.append({
                'module': 'excel_expert', 
                'confidence': 0.8,
                'suggested_functions': ['analyze_data', 'generate_formula']
            })
        
        if any(keyword in input_lower for keyword in tracking_keywords):
            detected.append({
                'module': 'stock_tracker',
                'confidence': 0.7,
                'suggested_functions': ['add_to_watchlist', 'get_market_summary']
            })
        
        return {
            'detected_modules': detected,
            'has_module_request': len(detected) > 0
        }
