"""
History management module for Gemini Desktop Tool.
Provides functionality to save and load recent instructions.
"""
import json
import os
from datetime import datetime

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.json")

class HistoryManager:
    def __init__(self, max_items=10):
        self.max_items = max_items
        self.history = []
        self.load()
    
    def load(self):
        """Load history from file."""
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get('history', [])
        except Exception as e:
            print(f"Failed to load history: {e}")
            self.history = []
    
    def save(self):
        """Save history to file."""
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump({'history': self.history}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save history: {e}")
    
    def add(self, instruction, content=""):
        """Add a new entry to history."""
        if not instruction.strip():
            return
        
        entry = {
            'instruction': instruction.strip(),
            'content_preview': content[:100] if content else "",
            'timestamp': datetime.now().isoformat()
        }
        
        # Remove duplicate if exists
        self.history = [h for h in self.history if h['instruction'] != entry['instruction']]
        
        # Add to front
        self.history.insert(0, entry)
        
        # Trim to max
        self.history = self.history[:self.max_items]
        
        self.save()
    
    def get_recent(self, count=5):
        """Get recent history entries."""
        return self.history[:count]
    
    def clear(self):
        """Clear all history."""
        self.history = []
        self.save()
