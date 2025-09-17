import asyncio
import threading
import json
import time
import traceback
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
import queue
import logging

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"

class TaskPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class HeavyTaskProcessor:
    """Napredni sistem za procesiranje heavy task-ova sa error handling i recovery"""
    
    def __init__(self, max_workers: int = 3, max_retries: int = 3):
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.tasks = {}
        self.task_queue = queue.PriorityQueue()
        self.workers = []
        self.running = False
        self.recovery_strategies = {}
        self.task_history = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Start worker threads
        self.start_workers()
    
    def start_workers(self):
        """Pokreće worker thread-ove"""
        self.running = True
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, args=(i,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
            self.logger.info(f"Started worker {i}")
    
    def stop_workers(self):
        """Zaustavlja worker thread-ove"""
        self.running = False
        for worker in self.workers:
            worker.join(timeout=5)
        self.logger.info("All workers stopped")
    
    def _worker_loop(self, worker_id: int):
        """Glavna petlja worker thread-a"""
        while self.running:
            try:
                # Uzmi task iz queue-a (timeout 1 sekunda)
                priority, task_id = self.task_queue.get(timeout=1)
                
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    self._execute_task(worker_id, task)
                
                self.task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {e}")
                continue
    
    def create_task(self, 
                   task_id: str,
                   task_type: str,
                   function: Callable,
                   args: tuple = (),
                   kwargs: dict = None,
                   priority: TaskPriority = TaskPriority.MEDIUM,
                   timeout: int = 300,
                   retry_strategy: str = "exponential_backoff",
                   recovery_function: Callable = None) -> Dict:
        """Kreira novi heavy task"""
        
        if kwargs is None:
            kwargs = {}
        
        task = {
            'id': task_id,
            'type': task_type,
            'function': function,
            'args': args,
            'kwargs': kwargs,
            'priority': priority,
            'status': TaskStatus.PENDING,
            'created_at': datetime.now(),
            'started_at': None,
            'completed_at': None,
            'timeout': timeout,
            'retry_count': 0,
            'max_retries': self.max_retries,
            'retry_strategy': retry_strategy,
            'recovery_function': recovery_function,
            'result': None,
            'error': None,
            'progress': 0,
            'logs': [],
            'worker_id': None
        }
        
        self.tasks[task_id] = task
        
        # Dodaj u queue sa prioritetom
        self.task_queue.put((priority.value * -1, task_id))  # Negativan za reverse order
        
        self.logger.info(f"Created task {task_id} ({task_type}) with priority {priority.name}")
        
        return {
            'task_id': task_id,
            'status': 'created',
            'message': f'Task {task_id} kreiran i dodat u queue'
        }
    
    def _execute_task(self, worker_id: int, task: Dict):
        """Izvršava task sa error handling"""
        task_id = task['id']
        
        try:
            # Ažuriraj status
            task['status'] = TaskStatus.RUNNING
            task['started_at'] = datetime.now()
            task['worker_id'] = worker_id
            task['progress'] = 0
            
            self.logger.info(f"Worker {worker_id} executing task {task_id}")
            
            # Pokreni task sa timeout
            result = self._run_with_timeout(
                task['function'],
                task['args'],
                task['kwargs'],
                task['timeout']
            )
            
            # Task uspešno završen
            task['status'] = TaskStatus.COMPLETED
            task['completed_at'] = datetime.now()
            task['result'] = result
            task['progress'] = 100
            
            self.logger.info(f"Task {task_id} completed successfully")
            
            # Dodaj u istoriju
            self._add_to_history(task)
            
        except TimeoutError:
            self._handle_task_error(task, "Task timeout exceeded")
        except Exception as e:
            self._handle_task_error(task, str(e))
    
    def _run_with_timeout(self, func: Callable, args: tuple, kwargs: dict, timeout: int):
        """Pokreće funkciju sa timeout"""
        result = [None]
        exception = [None]
        
        def target():
            try:
                result[0] = func(*args, **kwargs)
            except Exception as e:
                exception[0] = e
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            # Timeout - pokušaj da prekineš thread (ograničeno u Python)
            raise TimeoutError(f"Task exceeded timeout of {timeout} seconds")
        
        if exception[0]:
            raise exception[0]
        
        return result[0]
    
    def _handle_task_error(self, task: Dict, error_message: str):
        """Rukuje greškama u task-u"""
        task_id = task['id']
        task['error'] = error_message
        task['retry_count'] += 1
        
        self.logger.error(f"Task {task_id} failed: {error_message}")
        
        # Pokušaj recovery ako je definisan
        if task['recovery_function']:
            try:
                recovery_result = task['recovery_function'](task, error_message)
                if recovery_result.get('recovered', False):
                    self.logger.info(f"Task {task_id} recovered successfully")
                    task['status'] = TaskStatus.RUNNING
                    return
            except Exception as e:
                self.logger.error(f"Recovery failed for task {task_id}: {e}")
        
        # Proveri da li treba retry
        if task['retry_count'] < task['max_retries']:
            self._schedule_retry(task)
        else:
            # Task konačno neuspešan
            task['status'] = TaskStatus.FAILED
            task['completed_at'] = datetime.now()
            self.logger.error(f"Task {task_id} failed permanently after {task['retry_count']} retries")
            self._add_to_history(task)
    
    def _schedule_retry(self, task: Dict):
        """Zakazuje retry task-a"""
        task_id = task['id']
        retry_delay = self._calculate_retry_delay(task)
        
        task['status'] = TaskStatus.RETRYING
        
        self.logger.info(f"Scheduling retry for task {task_id} in {retry_delay} seconds")
        
        # Zakaži retry nakon delay-a
        def retry_task():
            time.sleep(retry_delay)
            if task_id in self.tasks:
                task['status'] = TaskStatus.PENDING
                self.task_queue.put((task['priority'].value * -1, task_id))
        
        retry_thread = threading.Thread(target=retry_task)
        retry_thread.daemon = True
        retry_thread.start()
    
    def _calculate_retry_delay(self, task: Dict) -> int:
        """Računa delay za retry na osnovu strategije"""
        strategy = task['retry_strategy']
        retry_count = task['retry_count']
        
        if strategy == "exponential_backoff":
            return min(2 ** retry_count, 300)  # Max 5 minuta
        elif strategy == "linear":
            return retry_count * 30  # 30, 60, 90 sekundi
        elif strategy == "fixed":
            return 60  # Fiksno 1 minut
        else:
            return 30  # Default
    
    def _add_to_history(self, task: Dict):
        """Dodaje task u istoriju"""
        history_entry = {
            'task_id': task['id'],
            'type': task['type'],
            'status': task['status'].value,
            'created_at': task['created_at'].isoformat(),
            'completed_at': task['completed_at'].isoformat() if task['completed_at'] else None,
            'duration': (task['completed_at'] - task['created_at']).total_seconds() if task['completed_at'] else None,
            'retry_count': task['retry_count'],
            'error': task['error']
        }
        
        self.task_history.append(history_entry)
        
        # Čuvaj samo poslednih 1000 task-ova
        if len(self.task_history) > 1000:
            self.task_history = self.task_history[-1000:]
    
    def get_task_status(self, task_id: str) -> Dict:
        """Vraća status task-a"""
        if task_id not in self.tasks:
            return {
                'status': 'not_found',
                'message': f'Task {task_id} ne postoji'
            }
        
        task = self.tasks[task_id]
        
        return {
            'task_id': task_id,
            'status': task['status'].value,
            'progress': task['progress'],
            'created_at': task['created_at'].isoformat(),
            'started_at': task['started_at'].isoformat() if task['started_at'] else None,
            'completed_at': task['completed_at'].isoformat() if task['completed_at'] else None,
            'retry_count': task['retry_count'],
            'error': task['error'],
            'result': task['result'] if task['status'] == TaskStatus.COMPLETED else None,
            'worker_id': task['worker_id']
        }
    
    def cancel_task(self, task_id: str) -> Dict:
        """Otkazuje task"""
        if task_id not in self.tasks:
            return {
                'success': False,
                'message': f'Task {task_id} ne postoji'
            }
        
        task = self.tasks[task_id]
        
        if task['status'] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return {
                'success': False,
                'message': f'Task {task_id} je već završen'
            }
        
        task['status'] = TaskStatus.CANCELLED
        task['completed_at'] = datetime.now()
        
        self.logger.info(f"Task {task_id} cancelled")
        
        return {
            'success': True,
            'message': f'Task {task_id} otkazan'
        }
    
    def get_queue_status(self) -> Dict:
        """Vraća status queue-a"""
        pending_tasks = [t for t in self.tasks.values() if t['status'] == TaskStatus.PENDING]
        running_tasks = [t for t in self.tasks.values() if t['status'] == TaskStatus.RUNNING]
        
        return {
            'queue_size': self.task_queue.qsize(),
            'pending_tasks': len(pending_tasks),
            'running_tasks': len(running_tasks),
            'total_tasks': len(self.tasks),
            'workers': self.max_workers,
            'active_workers': len([t for t in self.tasks.values() if t['status'] == TaskStatus.RUNNING])
        }
    
    def get_task_history(self, limit: int = 50) -> List[Dict]:
        """Vraća istoriju task-ova"""
        return self.task_history[-limit:]
    
    def cleanup_completed_tasks(self, older_than_hours: int = 24):
        """Čisti završene task-ove starije od X sati"""
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            if (task['status'] in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                task['completed_at'] and task['completed_at'] < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
        
        self.logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
        
        return {
            'cleaned_tasks': len(tasks_to_remove),
            'remaining_tasks': len(self.tasks)
        }

# Globalna instanca
task_processor = HeavyTaskProcessor()

# Helper funkcije za česte task tipove
def create_code_analysis_task(task_id: str, code: str, language: str) -> Dict:
    """Kreira task za analizu koda"""
    
    def analyze_code(code: str, language: str):
        # Simulacija analize koda
        time.sleep(5)  # Simulacija heavy processing
        
        analysis = {
            'language': language,
            'lines_of_code': len(code.split('\n')),
            'complexity_score': len(code) / 100,
            'suggestions': [
                'Dodaj error handling',
                'Optimizuj performanse',
                'Dodaj dokumentaciju'
            ],
            'security_issues': [],
            'performance_issues': []
        }
        
        return analysis
    
    return task_processor.create_task(
        task_id=task_id,
        task_type='code_analysis',
        function=analyze_code,
        args=(code, language),
        priority=TaskPriority.HIGH,
        timeout=120
    )

def create_file_processing_task(task_id: str, file_path: str, operation: str) -> Dict:
    """Kreira task za procesiranje fajlova"""
    
    def process_file(file_path: str, operation: str):
        # Simulacija file processing
        time.sleep(3)
        
        result = {
            'file_path': file_path,
            'operation': operation,
            'processed_at': datetime.now().isoformat(),
            'status': 'success'
        }
        
        return result
    
    return task_processor.create_task(
        task_id=task_id,
        task_type='file_processing',
        function=process_file,
        args=(file_path, operation),
        priority=TaskPriority.MEDIUM,
        timeout=180
    )

def create_ai_training_task(task_id: str, data: Dict, model_type: str) -> Dict:
    """Kreira task za AI training"""
    
    def train_model(data: Dict, model_type: str):
        # Simulacija AI training
        for i in range(10):
            time.sleep(1)  # Simulacija training steps
            # Ovde bi trebalo ažurirati progress
        
        model = {
            'model_type': model_type,
            'training_data_size': len(str(data)),
            'accuracy': 0.95,
            'trained_at': datetime.now().isoformat()
        }
        
        return model
    
    return task_processor.create_task(
        task_id=task_id,
        task_type='ai_training',
        function=train_model,
        args=(data, model_type),
        priority=TaskPriority.CRITICAL,
        timeout=600
    )
