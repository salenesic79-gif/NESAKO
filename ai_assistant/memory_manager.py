try:
    import sqlite3  # Not available on Railway base image
    HAS_SQLITE = True
except Exception:
    sqlite3 = None
    HAS_SQLITE = False
import json
import os
from datetime import datetime, timedelta
import threading
from typing import Dict, List, Any, Optional

class PersistentMemoryManager:
    """Fizička memorija koja čuva sve konverzacije i učenje na disku ili u DB (ORM)"""
    
    def __init__(self, db_path: str = None):
        # If sqlite3 is available use it for local dev; on Railway use ORM
        self.use_sqlite = HAS_SQLITE and not os.getenv('RAILWAY_ENVIRONMENT') and not os.getenv('RAILWAY_PROJECT_ID')
        if db_path is None:
            # Kreiranje baze u NESAKO direktorijumu
            base_dir = os.path.dirname(os.path.dirname(__file__))
            self.db_path = os.path.join(base_dir, 'nesako_memory.db')
        else:
            self.db_path = db_path
        
        self.lock = threading.Lock()
        if self.use_sqlite:
            self._init_database()
            print(f"Memory Manager (sqlite) initialized: {self.db_path}")
        else:
            print("Memory Manager using Django ORM (PostgreSQL on Railway)")
    
    def _init_database(self):
        """Kreiranje tabela za memoriju (samo za lokalni sqlite)"""
        if not self.use_sqlite:
            return
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
            
            conn.commit()
            print("Database tables (sqlite) initialized successfully")
    
    def save_conversation(self, session_id: str, user_message: str, ai_response: str, 
                         chat_id: str = None, tools_used: List[str] = None, 
                         context_data: Dict = None) -> int:
        """Čuva konverzaciju u bazu (sqlite) ili preko ORM (Postgres)"""
        if not self.use_sqlite:
            # ORM path
            try:
                # Lazy import to avoid circular imports during Django setup
                from django.apps import apps
                Conversation = apps.get_model('ai_assistant', 'Conversation')
                obj = Conversation.objects.create(
                    user_input=user_message,
                    assistant_response=ai_response,
                )
                return obj.id or 1
            except Exception as e:
                print(f"ORM: Error saving conversation: {e}")
                return -1
        # sqlite local path
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
        if not self.use_sqlite:
            try:
                from django.apps import apps
                Conversation = apps.get_model('ai_assistant', 'Conversation')
                qs = Conversation.objects.order_by('-created_at')[:limit]
                rows = list(qs)
                history = []
                for row in rows:
                    history.append({
                        'user_message': getattr(row, 'user_input', ''),
                        'ai_response': getattr(row, 'assistant_response', ''),
                        'timestamp': row.created_at.isoformat() if getattr(row, 'created_at', None) else '',
                        'tools_used': [],
                        'context_data': {}
                    })
                return list(reversed(history))
            except Exception as e:
                print(f"ORM: Error retrieving conversation history: {e}")
                return []
        # sqlite path
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
    
    def save_learning_data(self, session_id: str, category: str, data: Any, confidence: float = 0.5):
        """Čuva naučene podatke o korisniku. Na ORM koristi MemoryEntry key-value."""
        if not self.use_sqlite:
            try:
                from django.apps import apps
                MemoryEntry = apps.get_model('ai_assistant', 'MemoryEntry')
                key = f"learning:{session_id}:{category}"
                value = json.dumps({'data': data, 'confidence': confidence, 'updated': datetime.utcnow().isoformat()})
                obj, created = MemoryEntry.objects.update_or_create(
                    key=key,
                    defaults={'value': value}
                )
                return
            except Exception as e:
                print(f"ORM: Error saving learning data: {e}")
                return
        # sqlite path
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
        """Vraća kompletan profil učenja korisnika."""
        if not self.use_sqlite:
            try:
                from django.apps import apps
                MemoryEntry = apps.get_model('ai_assistant', 'MemoryEntry')
                prefix = f"learning:{session_id}:"
                entries = MemoryEntry.objects.filter(key__startswith=prefix)
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
                for entry in entries:
                    try:
                        payload = json.loads(entry.value)
                        category = entry.key[len(prefix):]
                        data = payload.get('data')
                        conf = payload.get('confidence', 0.5)
                        profile[category] = data
                        profile['confidence_scores'][category] = conf
                    except Exception:
                        continue
                return profile
            except Exception as e:
                print(f"ORM: Error retrieving learning profile: {e}")
                return {}
        # sqlite path
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
        """Skladišti modul u DB (ORM) kroz MemoryEntry, ili no-op za sqlite fallback."""
        if not self.use_sqlite:
            try:
                from django.apps import apps
                MemoryEntry = apps.get_model('ai_assistant', 'MemoryEntry')
                key = f"module:{module_name}"
                value = json.dumps({'code': module_code, 'config': config or {}, 'is_active': True, 'updated': datetime.utcnow().isoformat()})
                MemoryEntry.objects.update_or_create(key=key, defaults={'value': value})
                return True
            except Exception as e:
                print(f"ORM: Error adding AI module: {e}")
                return False
        # sqlite path (not used often now)
        return True
    
    def get_active_modules(self) -> List[Dict]:
        """Vraća sve aktivne module iz DB (ORM)"""
        if not self.use_sqlite:
            try:
                from django.apps import apps
                MemoryEntry = apps.get_model('ai_assistant', 'MemoryEntry')
                entries = MemoryEntry.objects.filter(key__startswith='module:')
                modules = []
                for e in entries:
                    try:
                        payload = json.loads(e.value)
                        if payload.get('is_active'):
                            modules.append({
                                'name': e.key.split(':', 1)[1],
                                'code': payload.get('code', ''),
                                'config': payload.get('config', {}),
                                'last_used': None
                            })
                    except Exception:
                        continue
                return modules
            except Exception as e:
                print(f"ORM: Error retrieving active modules: {e}")
                return []
        return []
    
    def set_modules_active(self, active: bool = True) -> bool:
        """Aktivira/deaktivira sve module (ORM preko MemoryEntry sa key 'module:*').
        Na sqlite (dev) metoda je no-op i vraća True.
        """
        if not self.use_sqlite:
            try:
                from django.apps import apps
                MemoryEntry = apps.get_model('ai_assistant', 'MemoryEntry')
                entries = MemoryEntry.objects.filter(key__startswith='module:')
                for e in entries:
                    try:
                        payload = json.loads(e.value or '{}')
                        payload['is_active'] = bool(active)
                        e.value = json.dumps(payload)
                        e.save(update_fields=['value'])
                    except Exception:
                        continue
                return True
            except Exception as e:
                print(f"ORM: Error toggling modules active state: {e}")
                return False
        return True
    
    # Sledeće metode nisu kritične za rad sistema na Railway i ostaju no-op u ORM modu
    def save_task(self, task_id: str, description: str, status: str = 'pending') -> bool:
        if not self.use_sqlite:
            return True
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
        if not self.use_sqlite:
            return True
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
        if not self.use_sqlite:
            return True
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
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
        if not self.use_sqlite:
            return
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM conversations 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                cursor.execute('''
                    DELETE FROM file_operations 
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                task_cutoff = datetime.now() - timedelta(days=7)
                cursor.execute('''
                    DELETE FROM task_history 
                    WHERE completed_at < ? AND task_status = 'completed'
                ''', (task_cutoff,))
                cursor.execute('VACUUM')
                conn.commit()
                print(f"Cleaned up data older than {days_to_keep} days")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def get_memory_stats(self) -> Dict:
        if not self.use_sqlite:
            try:
                from django.apps import apps
                Conversation = apps.get_model('ai_assistant', 'Conversation')
                MemoryEntry = apps.get_model('ai_assistant', 'MemoryEntry')
                return {
                    'total_conversations': Conversation.objects.count(),
                    'active_modules': MemoryEntry.objects.filter(key__startswith='module:').count(),
                    'total_tasks': 0,
                    'db_size_mb': 0.0
                }
            except Exception as e:
                print(f"ORM: Error getting memory stats: {e}")
                return {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                stats = {}
                cursor.execute('SELECT COUNT(*) FROM conversations')
                stats['total_conversations'] = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='ai_modules'")
                stats['active_modules'] = 0
                cursor.execute('SELECT COUNT(*) FROM task_history')
                stats['total_tasks'] = cursor.fetchone()[0] if cursor.fetchone() else 0
                stats['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
                return stats
        except Exception as e:
            print(f"Error getting memory stats: {e}")
            return {}

    # --- New: Module snapshot helpers used by upgrade flow ---
    def save_module_snapshot(self, snapshot_key: str = 'auto', payload: Optional[Dict] = None) -> bool:
        """Sačuvaj snapshot stanja modula. U ORM modu koristi MemoryEntry, u sqlite snimi kao learning kategoriju.
        payload može sadržati dodatne informacije; ako nije zadan, upišemo samo timestamp.
        """
        try:
            data = payload or {'saved_at': datetime.utcnow().isoformat()}
            key_name = f"module_snapshot:{snapshot_key}"
            if not self.use_sqlite:
                from django.apps import apps
                MemoryEntry = apps.get_model('ai_assistant', 'MemoryEntry')
                value = json.dumps(data)
                MemoryEntry.objects.update_or_create(key=key_name, defaults={'value': value})
                return True
            # sqlite fallback: snimi kao user_learning sa fiksnim session_id 'global'
            self.save_learning_data('global', key_name, data, confidence=1.0)
            return True
        except Exception as e:
            print(f"Error saving module snapshot: {e}")
            return False

    def restore_module_snapshot(self, snapshot_key: str = 'auto') -> bool:
        """Vrati snapshot ako postoji (indikativno). U ORM modu čita MemoryEntry; u sqlite iz user_learning.
        Napomena: Ovde ne vraćamo kod modula već samo signal da snapshot postoji.
        """
        try:
            key_name = f"module_snapshot:{snapshot_key}"
            if not self.use_sqlite:
                from django.apps import apps
                MemoryEntry = apps.get_model('ai_assistant', 'MemoryEntry')
                obj = MemoryEntry.objects.filter(key=key_name).first()
                return bool(obj)
            # sqlite fallback: pročitaj profil i proveri da li postoji zapis
            profile = self.get_learning_profile('global')
            return key_name in profile
        except Exception as e:
            print(f"Error restoring module snapshot: {e}")
            return False

    # --- New: Simple conversation-driven learning ---
    def learn_from_conversation(self, session_id: str, user_message: str, ai_response: str = "") -> bool:
        """Lightweight samoučenje iz teksta: detekcija preferenci i tema.
        - Ako korisnik pominje 'sofascore', postavi preferencu prefer_sofascore=True
        - Sačuvaj poslednje teme (naivna ekstrakcija ključnih reči)
        """
        try:
            if not session_id:
                session_id = 'default'
            text = (user_message or '').lower()
            # Preferenca izvora za sport
            if 'sofascore' in text:
                self.save_learning_data(session_id, 'sports_source', {'prefer_sofascore': True}, confidence=0.85)
            # Naivna ekstrakcija tema (kljucne reci duže od 3)
            import re
            tokens = re.findall(r"[a-zA-ZčćšđžČĆŠĐŽ0-9]+", (user_message or ''))
            topics = [t for t in tokens if len(t) > 3][:10]
            if topics:
                self.save_learning_data(session_id, 'last_topics', topics, confidence=0.6)
            return True
        except Exception as e:
            print(f"Learning error: {e}")
            return False
