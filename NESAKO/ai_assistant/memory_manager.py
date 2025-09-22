import sqlite3
import json
import os
from datetime import datetime, timedelta
import threading
from typing import Dict, List, Any, Optional

class PersistentMemoryManager:
    """Fizička memorija koja čuva sve konverzacije i učenje na disku"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Kreiranje baze u NESAKO direktorijumu
            base_dir = os.path.dirname(os.path.dirname(__file__))
            self.db_path = os.path.join(base_dir, 'nesako_memory.db')
        else:
            self.db_path = db_path
            
        self.lock = threading.Lock()
        self._init_database()
        print(f"Memory Manager initialized with database: {self.db_path}")
    
    def _init_database(self):
        """Kreiranje tabela za memoriju"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela za konverzacije
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    chat_id TEXT,
                    user_message TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    tools_used TEXT,
                    context_data TEXT,
                    message_type TEXT DEFAULT 'chat'
                )
            ''')
            
            # Tabela za učenje i preferencije
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_learning (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    learning_category TEXT NOT NULL,
                    learning_data TEXT NOT NULL,
                    confidence_score REAL DEFAULT 0.5,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, learning_category)
                )
            ''')
            
            # Tabela za AI module i proširenja
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_modules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module_name TEXT UNIQUE NOT NULL,
                    module_code TEXT NOT NULL,
                    module_config TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_used DATETIME
                )
            ''')
            
            # Tabela za task history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    task_description TEXT NOT NULL,
                    task_status TEXT DEFAULT 'pending',
                    task_result TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_at DATETIME,
                    execution_time REAL
                )
            ''')
            
            # Tabela za file operations
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    operation_data TEXT,
                    success BOOLEAN DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            print("Database tables initialized successfully")
    
    def save_conversation(self, session_id: str, user_message: str, ai_response: str, 
                         chat_id: str = None, tools_used: List[str] = None, 
                         context_data: Dict = None) -> int:
        """Čuva konverzaciju u bazu"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO conversations 
                        (session_id, chat_id, user_message, ai_response, tools_used, context_data)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        session_id,
                        chat_id,
                        user_message,
                        ai_response,
                        json.dumps(tools_used) if tools_used else None,
                        json.dumps(context_data) if context_data else None
                    ))
                    
                    conversation_id = cursor.lastrowid
                    conn.commit()
                    
                    print(f"Conversation saved with ID: {conversation_id}")
                    return conversation_id
                    
            except Exception as e:
                print(f"Error saving conversation: {e}")
                return -1
    
    def get_conversation_history(self, session_id: str, limit: int = 20) -> List[Dict]:
        """Vraća istoriju konverzacije"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT user_message, ai_response, timestamp, tools_used, context_data
                    FROM conversations 
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (session_id, limit))
                
                rows = cursor.fetchall()
                
                history = []
                for row in rows:
                    user_msg, ai_resp, timestamp, tools_used, context_data = row
                    
                    history.append({
                        'user_message': user_msg,
                        'ai_response': ai_resp,
                        'timestamp': timestamp,
                        'tools_used': json.loads(tools_used) if tools_used else [],
                        'context_data': json.loads(context_data) if context_data else {}
                    })
                
                return list(reversed(history))  # Vraćamo u hronološkom redosledu
                
        except Exception as e:
            print(f"Error retrieving conversation history: {e}")
            return []
    
    def save_learning_data(self, session_id: str, category: str, data: Dict, confidence: float = 0.5):
        """Čuva naučene podatke o korisniku"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_learning 
                        (session_id, learning_category, learning_data, confidence_score, last_updated)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (session_id, category, json.dumps(data), confidence))
                    
                    conn.commit()
                    print(f"Learning data saved: {category}")
                    
            except Exception as e:
                print(f"Error saving learning data: {e}")
    
    def get_learning_profile(self, session_id: str) -> Dict:
        """Vraća kompletan profil učenja korisnika"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT learning_category, learning_data, confidence_score, last_updated
                    FROM user_learning 
                    WHERE session_id = ?
                    ORDER BY confidence_score DESC
                ''', (session_id,))
                
                rows = cursor.fetchall()
                
                profile = {
                    'programming_languages': [],
                    'frameworks': [],
                    'project_types': [],
                    'coding_style': 'standard',
                    'complexity_preference': 'intermediate',
                    'communication_style': 'direct',
                    'learning_speed': 'normal',
                    'last_topics': [],
                    'confidence_scores': {}
                }
                
                for row in rows:
                    category, data_json, confidence, last_updated = row
                    try:
                        data = json.loads(data_json)
                        profile[category] = data
                        profile['confidence_scores'][category] = confidence
                    except:
                        continue
                
                return profile
                
        except Exception as e:
            print(f"Error retrieving learning profile: {e}")
            return {}
    
    def add_ai_module(self, module_name: str, module_code: str, config: Dict = None) -> bool:
        """Dodaje novi AI modul u sistem"""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO ai_modules 
                        (module_name, module_code, module_config, is_active, created_at)
                        VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ''', (module_name, module_code, json.dumps(config) if config else None))
                    
                    conn.commit()
                    print(f"AI module added: {module_name}")
                    return True
                    
            except Exception as e:
                print(f"Error adding AI module: {e}")
                return False
    
    def get_active_modules(self) -> List[Dict]:
        """Vraća sve aktivne AI module"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT module_name, module_code, module_config, last_used
                    FROM ai_modules 
                    WHERE is_active = 1
                    ORDER BY last_used DESC
                ''')
                
                rows = cursor.fetchall()
                
                modules = []
                for row in rows:
                    name, code, config_json, last_used = row
                    modules.append({
                        'name': name,
                        'code': code,
                        'config': json.loads(config_json) if config_json else {},
                        'last_used': last_used
                    })
                
                return modules
                
        except Exception as e:
            print(f"Error retrieving active modules: {e}")
            return []
    
    def save_task(self, task_id: str, description: str, status: str = 'pending') -> bool:
        """Čuva task u bazu"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO task_history 
                    (task_id, task_description, task_status, created_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (task_id, description, status))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error saving task: {e}")
            return False
    
    def update_task_status(self, task_id: str, status: str, result: str = None) -> bool:
        """Ažurira status task-a"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if status == 'completed':
                    cursor.execute('''
                        UPDATE task_history 
                        SET task_status = ?, task_result = ?, completed_at = CURRENT_TIMESTAMP
                        WHERE task_id = ?
                    ''', (status, result, task_id))
                else:
                    cursor.execute('''
                        UPDATE task_history 
                        SET task_status = ?, task_result = ?
                        WHERE task_id = ?
                    ''', (status, result, task_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error updating task status: {e}")
            return False
    
    def log_file_operation(self, operation_type: str, file_path: str, 
                          operation_data: Dict = None, success: bool = False) -> bool:
        """Loguje file operacije"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO file_operations 
                    (operation_type, file_path, operation_data, success, timestamp)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (operation_type, file_path, 
                     json.dumps(operation_data) if operation_data else None, success))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error logging file operation: {e}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Briše stare podatke starije od N dana"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Briši stare konverzacije
                cursor.execute('''
                    DELETE FROM conversations 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                
                # Briši stare file operacije
                cursor.execute('''
                    DELETE FROM file_operations 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                
                # Briši završene taskove starije od 7 dana
                task_cutoff = datetime.now() - timedelta(days=7)
                cursor.execute('''
                    DELETE FROM task_history 
                    WHERE completed_at < ? AND task_status = 'completed'
                ''', (task_cutoff,))
                
                # Briši stare podatke učenja
                cursor.execute('''
                    DELETE FROM user_learning 
                    WHERE last_updated < ?
                ''', (cutoff_date,))
                
                # Optimizacija baze nakon brisanja
                cursor.execute('VACUUM')
                
                conn.commit()
                print(f"Cleaned up data older than {days_to_keep} days")
                
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def get_memory_stats(self) -> Dict:
        """Vraća statistike memorije"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Broj konverzacija
                cursor.execute('SELECT COUNT(*) FROM conversations')
                stats['total_conversations'] = cursor.fetchone()[0]
                
                # Broj aktivnih modula
                cursor.execute('SELECT COUNT(*) FROM ai_modules WHERE is_active = 1')
                stats['active_modules'] = cursor.fetchone()[0]
                
                # Broj taskova
                cursor.execute('SELECT COUNT(*) FROM task_history')
                stats['total_tasks'] = cursor.fetchone()[0]
                
                # Veličina baze
                stats['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
                
                return stats
                
        except Exception as e:
            print(f"Error getting memory stats: {e}")
            return {}
