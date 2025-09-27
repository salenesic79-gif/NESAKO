import json
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
