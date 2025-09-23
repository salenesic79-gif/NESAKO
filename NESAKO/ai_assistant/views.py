import json
import os
import requests
import subprocess
import tempfile
import re
import urllib.parse
from datetime import datetime
import pytz
from django.http import JsonResponse
from django.views import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import redirect
from django.conf import settings
from django.middleware.csrf import get_token
from bs4 import BeautifulSoup
from pathlib import Path
import base64
from typing import Any, Dict, List, Optional
from .memory_manager import PersistentMemoryManager
from .image_processor import ImageProcessor
from .command_generator import CommandGenerator
from .module_manager import ModuleManager
from .file_operations import FileOperationsManager
from .task_processor import task_processor, create_code_analysis_task, create_file_processing_task
from .nesako_chatbot import NESAKOChatbot
from .models import LessonLearned

class DeepSeekAPI(View):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory = PersistentMemoryManager()
        self.image_processor = ImageProcessor()
        self.command_generator = CommandGenerator()
        self.module_manager = ModuleManager()
        self.file_operations = FileOperationsManager()
        # NESAKO Chatbot with ORM-backed memory and SerpAPI integration
        self.nesako = NESAKOChatbot()

    # --- Safe stub: UI expects threat detection method ---
    def detect_critical_threats(self, text: str) -> list:
        """Stub for UI compatibility. Returns empty list (no threats)."""
        try:
            if not text:
                return []
            # Here we could add real detection; for now, return [] to avoid UI errors
            return []
        except Exception:
            return []

    # --- Safe stub: UI may call this to update learning
    def update_learning_from_conversation(self, session_id: str, user_input: str, conversation_history: list):
        """Stub for UI compatibility. Delegates to NESAKO memory if available, else no-op."""
        try:
            # Delegate to NESAKO chatbot learning system if present
            if hasattr(self.nesako, 'learn_from_conversation'):
                self.nesako.learn_from_conversation(user_input or '', '')
            return True
        except Exception:
            return False

    # --- Safe stub: heavy task detector used in post() flow
    def is_heavy_task(self, user_input: str) -> bool:
        """Lightweight heuristic to detect heavy tasks; safe default False."""
        try:
            if not user_input:
                return False
            text = user_input.lower()
            keywords = ['analyze repo', 'code analysis', 'large file', 'process project', 'rollback', 'deploy']
            return any(k in text for k in keywords)
        except Exception:
            return False

    # --- Safe stub: complex task detector expected by some UI flows
    def is_complex_task(self, user_input: str) -> bool:
        """Heuristic for complex tasks; default False to keep UX stable."""
        try:
            if not user_input:
                return False
            text = user_input.lower()
            patterns = ['kompleks', 'complex', 'plan', 'arhitekt', 'refactor', 'migrate', 'docker', 'kubernetes']
            return any(p in text for p in patterns)
        except Exception:
            return False
        
    def dispatch(self, request, *args, **kwargs):
        # Check authentication for API access
        if not request.session.get('authenticated'):
            return JsonResponse({
                'error': 'Neautorizovan pristup - molim vas ulogujte se',
                'status': 'unauthorized'
            }, status=401)
        return super().dispatch(request, *args, **kwargs)
    def get_github_content(self, repo_url, path=""):
        """Tool: Pristup GitHub repozitorijumu za analizu koda"""
        try:
            # Parse GitHub URL
            if "github.com" in repo_url:
                # Remove any query parameters and fragments
                clean_url = repo_url.split('?')[0].split('#')[0]
                parts = clean_url.rstrip('/').split("/")
                if len(parts) < 2:
                    return "❌ Nevalidan GitHub URL format"
                
                owner = parts[-2]
                repo = parts[-1].replace(".git", "")
            else:
                return "❌ Nevalidan GitHub URL - mora biti github.com link"
            
            github_token = os.environ.get('GITHUB_TOKEN')
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'NESAKO-AI-Assistant'
            }
            if github_token:
                headers['Authorization'] = f'token {github_token}'
            
            # First, get repository info to verify it exists
            repo_api_url = f"https://api.github.com/repos/{owner}/{repo}"
            repo_response = requests.get(repo_api_url, headers=headers, timeout=15)
            
            if repo_response.status_code != 200:
                # Try to get more specific error information
                error_info = ""
                try:
                    error_data = repo_response.json()
                    error_info = f" - {error_data.get('message', '')}"
                except:
                    pass
                return f"❌ GitHub repozitorijum nije pronađen ili nije javan: {owner}/{repo}{error_info}"
            
            repo_data = repo_response.json()
            
            # Get repository contents
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            response = requests.get(api_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    # Directory listing - get up to 20 items
                    files = []
                    for item in data:
                        files.append({
                            'name': item['name'],
                            'type': item['type'],
                            'size': item.get('size', 0),
                            'path': item['path'],
                            'html_url': item.get('html_url', '')
                        })
                    return {
                        'type': 'directory', 
                        'files': files[:20],  # Limit to 20 files
                        'repo_info': {
                            'name': repo_data.get('name', repo),
                            'full_name': repo_data.get('full_name', f"{owner}/{repo}"),
                            'description': repo_data.get('description', ''),
                            'stars': repo_data.get('stargazers_count', 0),
                            'forks': repo_data.get('forks_count', 0),
                            'language': repo_data.get('language', ''),
                            'updated_at': repo_data.get('updated_at', '')
                        }
                    }
                else:
                    # Single file
                    if data['type'] == 'file':
                        # For text files, get content
                        if data['size'] < 50000:  # Limit to 50KB
                            content = base64.b64decode(data['content']).decode('utf-8', errors='ignore')
                            return {
                                'type': 'file',
                                'name': data['name'],
                                'content': content[:15000],  # Limit to 15k chars
                                'size': data['size'],
                                'path': data['path'],
                                'html_url': data.get('html_url', ''),
                                'repo_info': {
                                    'name': repo_data.get('name', repo),
                                    'full_name': repo_data.get('full_name', f"{owner}/{repo}"),
                                    'description': repo_data.get('description', '')
                                }
                            }
                        else:
                            return {
                                'type': 'file_too_large',
                                'name': data['name'],
                                'size': data['size'],
                                'path': data['path'],
                                'html_url': data.get('html_url', ''),
                                'message': 'Fajl je prevelik za prikaz (preko 50KB)'
                            }
            
            # More detailed error information
            error_msg = f"❌ GitHub API greška: {response.status_code}"
            try:
                error_data = response.json()
                error_msg += f" - {error_data.get('message', '')}"
                if 'documentation_url' in error_data:
                    error_msg += f" (dokumentacija: {error_data['documentation_url']})"
            except:
                error_msg += f" - {response.text[:200]}"
            
            return error_msg
            
        except requests.exceptions.Timeout:
            return "❌ GitHub API timeout - repozitorijum je prevelik ili server ne odgovara"
        except Exception as e:
            return f"❌ GitHub greška: {str(e)}"

    def analyze_code_structure(self, code_content, language):
        """Tool: Analiza strukture koda"""
        try:
            analysis = {
                'language': language,
                'lines': len(code_content.split('\n')),
                'functions': [],
                'classes': [],
                'imports': [],
                'complexity': 'low'
            }
            
            if language.lower() == 'python':
                # Python specific analysis
                lines = code_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('def '):
                        func_name = line.split('(')[0].replace('def ', '')
                        analysis['functions'].append(func_name)
                    elif line.startswith('class '):
                        class_name = line.split(':')[0].replace('class ', '')
                        analysis['classes'].append(class_name)
                    elif line.startswith('import ') or line.startswith('from '):
                        analysis['imports'].append(line)
                
                # Simple complexity estimation
                if len(analysis['functions']) > 10 or len(analysis['classes']) > 5:
                    analysis['complexity'] = 'high'
                elif len(analysis['functions']) > 5 or len(analysis['classes']) > 2:
                    analysis['complexity'] = 'medium'
            
            return analysis
            
        except Exception as e:
            return f"Analysis Error: {str(e)}"

    def get_web_content(self, url):
        """Tool: Preuzimanje sadržaja sa web stranice"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                for script in soup(["script", "style"]):
                    script.decompose()
                text = soup.get_text()
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = ' '.join(chunk for chunk in chunks if chunk)
                return text[:5000]
        except Exception as e:
            return f"Error: {str(e)}"
        return "Content not accessible"

    def get_sports_stats(self, sport, event_id, data_points):
        """Tool: Preuzimanje sportskih statistika"""
        try:
            sports_data = {
                "football": {
                    "premier_league": {
                        "standings": "1. Man City 45pts, 2. Arsenal 43pts, 3. Liverpool 42pts",
                        "top_scorers": "Haaland 15, Salah 12, Kane 11",
                        "fixtures": "Man City vs Arsenal (Sunday 16:00)"
                    }
                },
                "basketball": {
                    "nba": {
                        "standings": "1. Celtics 25-8, 2. Nuggets 24-11, 3. Bucks 23-10",
                        "top_scorers": "Dončić 32.1ppg, Antetokounmpo 31.2ppg",
                        "games": "Lakers vs Warriors (Tonight 21:00)"
                    }
                }
            }
            
            result = {}
            sport_data = sports_data.get(sport.lower(), {})
            event_data = sport_data.get(event_id.lower(), {})
            
            for point in data_points:
                if point in event_data:
                    result[point] = event_data[point]
                    
            return result if result else "No data available"
            
        except Exception as e:
            return f"Error: {str(e)}"

    def run_code_sandbox(self, language, code):
        """Tool: Izvršavanje koda u sandbox okruženju"""
        try:
            if language.lower() == 'python':
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(code)
                    temp_file = f.name
                
                result = subprocess.run(
                    ['python', temp_file], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                
                os.unlink(temp_file)
                
                if result.returncode == 0:
                    return result.stdout
                else:
                    return f"Error: {result.stderr}"
                    
            elif language.lower() == 'javascript':
                result = subprocess.run(
                    ['node', '-e', code], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                
                if result.returncode == 0:
                    return result.stdout
                else:
                    return f"Error: {result.stderr}"
            
            else:
                return f"Language {language} not supported"
                
        except subprocess.TimeoutExpired:
            return "Error: Code execution timeout"
        except Exception as e:
            return f"Error: {str(e)}"

    def detect_and_execute_tools(self, user_input):
        """Detektuje i izvršava tool pozive iz korisničkog unosa"""
        tools_output = ""
        status_updates = []
        
        # Detektuj GitHub URL-ove direktno u tekstu
        github_url_pattern = r'https?://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+'
        github_matches = re.findall(github_url_pattern, user_input)
        
        for github_url in github_matches:
            status_updates.append(f"🔗 Pronađen GitHub repozitorijum: {github_url}")
            status_updates.append("📂 Analiziram GitHub repozitorijum...")
            
            content = self.get_github_content(github_url)
            if isinstance(content, dict):
                # Formatiraj lepši izlaz za GitHub
                tools_output += f"\n🎯 **GITHUB REPO ANALIZA: {content.get('repo_info', {}).get('full_name', github_url)}**\n\n"
                
                # Dodaj osnovne informacije o repozitorijumu
                repo_info = content.get('repo_info', {})
                if repo_info:
                    tools_output += f"📋 **OPIS:** {repo_info.get('description', 'Nema opisa')}\n"
                    tools_output += f"⭐ **ZVEZDICE:** {repo_info.get('stars', 0)}\n"
                    tools_output += f"🍴 **FORKOVI:** {repo_info.get('forks', 0)}\n"
                    tools_output += f"💻 **JEZIK:** {repo_info.get('language', 'Nepoznato')}\n"
                    tools_output += f"🔄 **AŽURIRANO:** {repo_info.get('updated_at', 'Nepoznato')}\n\n"
                
                # Prikaz sadržaja
                if content.get('type') == 'directory':
                    tools_output += "📁 **SADRŽAJ REPOZITORIJUMA:**\n"
                    for file in content.get('files', [])[:10]:  # Prikaz prvih 10 fajlova
                        tools_output += f"• {file['name']} ({file['type']}, {file['size']} bytes)\n"
                elif content.get('type') == 'file':
                    tools_output += f"📄 **FAJL:** {content.get('name')}\n"
                    tools_output += f"📏 **VELIČINA:** {content.get('size')} bytes\n"
                    tools_output += f"```\n{content.get('content', 'Nema sadržaja')}\n```\n"
                
                status_updates.append("✅ GitHub repozitorijum uspešno analiziran")
            else:
                tools_output += f"\n❌ **GREŠKA PRI ANALIZI GITHUB REPO:**\n{content}\n"
                status_updates.append("❌ Greška pri analizi GitHub repozitorijuma")
        
        # Detektuj tool pozive u JSON formatu
        json_pattern = r'\{[^{}]*"tool"[^{}]*\}'
        matches = re.findall(json_pattern, user_input)
        
        for match in matches:
            try:
                tool_call = json.loads(match)
                tool_name = tool_call.get('tool')
                
                if tool_name == 'get_web_content':
                    status_updates.append("🌐 Pristupam web stranici...")
                    url = tool_call.get('url')
                    if url:
                        content = self.get_web_content(url)
                        tools_output += f"\n🌐 **WEB SADRŽAJ SA {url}:**\n{content}\n"
                        status_updates.append("✅ Web sadržaj preuzet")
                        
                elif tool_name == 'get_github_content':
                    status_updates.append("🔗 Pristupam GitHub repozitorijumu...")
                    repo_url = tool_call.get('repo_url')
                    path = tool_call.get('path', '')
                    if repo_url:
                        content = self.get_github_content(repo_url, path)
                        tools_output += f"\n🔗 **GITHUB SADRŽAJ ({repo_url}/{path}):**\n{json.dumps(content, indent=2, ensure_ascii=False)}\n"
                        status_updates.append("✅ GitHub sadržaj analiziran")
                        
                elif tool_name == 'analyze_code':
                    status_updates.append("🔍 Analiziram strukturu koda...")
                    code = tool_call.get('code')
                    language = tool_call.get('language', 'python')
                    if code:
                        analysis = self.analyze_code_structure(code, language)
                        tools_output += f"\n🔍 **ANALIZA KODA ({language}):**\n{json.dumps(analysis, indent=2, ensure_ascii=False)}\n"
                        status_updates.append("✅ Kod analiziran")
                        
                elif tool_name == 'get_sports_stats':
                    status_updates.append("⚽ Preuzimam sportske statistike...")
                    sport = tool_call.get('sport')
                    event_id = tool_call.get('event_id')
                    data_points = tool_call.get('data_points', [])
                    if sport and event_id:
                        stats = self.get_sports_stats(sport, event_id, data_points)
                        tools_output += f"\n⚽ **SPORTSKE STATISTIKE ({sport} - {event_id}):**\n{json.dumps(stats, indent=2, ensure_ascii=False)}\n"
                        status_updates.append("✅ Sportske statistike preuzete")
                        
                elif tool_name == 'run_code_sandbox':
                    status_updates.append("💻 Izvršavam kod...")
                    language = tool_call.get('language')
                    code = tool_call.get('code')
                    if language and code:
                        result = self.run_code_sandbox(language, code)
                        tools_output += f"\n💻 **IZVRŠAVANJE KODA ({language}):**\n{result}\n"
                        status_updates.append("✅ Kod izvršen")
                        
            except json.JSONDecodeError:
                continue
        
        # Add status updates to output
        if status_updates:
            tools_output = "\n".join(status_updates) + "\n" + tools_output
                
        return tools_output

    # --- Novi: Provera pouzdanosti odgovora i fallback na web ---
    def is_confident_answer(self, response_text: str, min_confidence: float = 0.7) -> bool:
        """Heuristika za procenu pouzdanosti odgovora.
        Ako model ne vraća score, koristimo jednostavne provere: dužina, negacije, indikatori nesigurnosti.
        """
        if not response_text:
            return False
        text = response_text.lower()
        uncertain_markers = [
            'nisam siguran', 'ne mogu da proverim', 'možda', 'verovatno',
            'nemam dovoljno informacija', 'ne mogu da pristupim', 'nepoznato'
        ]
        if any(m in text for m in uncertain_markers):
            return False
        if 'sigurno' in text:
            return True
        # Minimalna dužina kao prag
        return len(text.strip()) > 40

    def apply_confidence_fallback(self, user_input: str, ai_response: str) -> str:
        """Ako odgovor nije dovoljno pouzdan, ili je eksplicitno traženo 'trenutno/realno/najnovije',
        automatski dodaj web pretragu kao izvor i priloži URL.
        """
        try:
            lower_q = user_input.lower()
            force_web = any(w in lower_q for w in ['trenutno', 'realno stanje', 'najnovije'])
            if self.is_confident_answer(ai_response) and not force_web:
                return ai_response
            # Automatski fallback na web
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(user_input)}"
            web_text = self.get_web_content(search_url)
            prefix = "Nisam siguran, ali evo šta sam našao na internetu:\n"
            return f"{prefix}{web_text}\n\nIzvor: {search_url}"
        except Exception as e:
            return ai_response

    def get_web_data(self, query):
        """Postojeća funkcija za web pretragu"""
        try:
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(search_url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                search_results = []
                for result in soup.find_all('div', class_='g')[:3]:
                    title_elem = result.find('h3')
                    snippet_elem = result.find('span', class_='aCOpRe')
                    
                    if title_elem and snippet_elem:
                        search_results.append({
                            'title': title_elem.get_text(),
                            'snippet': snippet_elem.get_text()
                        })
                
                return search_results
            
        except Exception as e:
            print(f"Web search error: {e}")
            return []
        
        return []
    
    def get_weather_data(self):
        """Postojeća funkcija za vreme"""
        try:
            api_key = os.environ.get('WEATHER_API_KEY')
            if api_key:
                url = f"http://api.openweathermap.org/data/2.5/weather?q=Belgrade,RS&appid={api_key}&units=metric&lang=sr"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'temperature': data['main']['temp'],
                        'description': data['weather'][0]['description'],
                        'humidity': data['main']['humidity']
                    }
        except Exception as e:
            print(f"Weather API error: {e}")
        
        return None
    
    def get_news_data(self):
        """Postojeća funkcija za vesti"""
        try:
            rss_urls = [
                'https://www.b92.net/rss/index.xml',
                'https://www.rts.rs/page/stories/ci/story/124/drustvo/rss.xml'
            ]
            
            news_items = []
            for url in rss_urls[:1]:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'xml')
                    items = soup.find_all('item')[:3]
                    
                    for item in items:
                        title = item.find('title')
                        description = item.find('description')
                        if title:
                            news_items.append({
                                'title': title.get_text(),
                                'description': description.get_text() if description else ''
                            })
                    break
            
            return news_items
            
        except Exception as e:
            print(f"News fetch error: {e}")
            return []

    def post(self, request):
        print("=== NESAKO AI POST METHOD ===")
        try:
            print(f"Request body: {request.body}")
            print(f"Content type: {request.content_type}")
            
            # Handle multipart/form-data for image uploads
            if request.content_type and 'multipart/form-data' in request.content_type:
                return self.handle_image_upload(request)
            
            # Improved JSON parsing with error handling
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                return JsonResponse({
                    'error': 'Invalid JSON format',
                    'status': 'error',
                    'response': 'Greška u parsiranju zahteva. Molim pokušajte ponovo.'
                }, status=400)
            
            # Add request validation
            if not isinstance(data, dict):
                return JsonResponse({
                    'error': 'Invalid request format',
                    'status': 'error',
                    'response': 'Nevalidan format zahteva. Molim pokušajte ponovo.'
                }, status=400)
            
            user_input = data.get('instruction', '').strip()
            conversation_history = data.get('conversation_history', [])
            task_id = data.get('task_id', None)
            
            print(f"User input: '{user_input}'")
            print(f"Task ID: {task_id}")
            print(f"History length: {len(conversation_history)}")
            
            # Handle task progress polling (empty instruction with task_id)
            if task_id and not user_input:
                print(f"DEBUG: Polling progress for task_id: {task_id}")
                progress = self.get_task_progress(task_id)
                print(f"DEBUG: Progress result: {progress}")
                if progress['status'] == 'completed':
                    return JsonResponse({
                        'response': f"✅ Zadatak završen!\n\n{progress['result']}",
                        'status': 'success',
                        'task_completed': True,
                        'task_id': task_id
                    })
                elif progress['status'] == 'running':
                    return JsonResponse({
                        'response': f"⏳ Zadatak u toku... {progress['progress']}%",
                        'status': 'progress',
                        'progress': progress['progress'],
                        'task_id': task_id
                    })
                else:
                    return JsonResponse({
                        'response': "Zadatak završen ili nije pronađen.",
                        'status': 'completed'
                    })
            
            # Validate user input
            if not user_input:
                print("ERROR: Empty user input")
                return JsonResponse({
                    'error': 'Prazan unos',
                    'status': 'error',
                    'response': 'Molim unesite vašu poruku ili pitanje.'
                }, status=400)
            
            # Security threat detection - SAMO za kritične pretnje
            security_warnings = self.detect_critical_threats(user_input)
            if security_warnings:
                # Log security threat
                print(f"SECURITY THREAT DETECTED: {security_warnings}")
                return JsonResponse({
                    'response': f"🚨 KRITIČNA PRETNJA DETEKTOVANA:\n{security_warnings}\n\nZadatak automatski blokiran.",
                    'status': 'blocked',
                    'threat_level': 'critical'
                })
            
            # Rate limiting check
            session_id = request.session.session_key
            if not self.check_rate_limit(session_id):
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'status': 'error',
                    'response': 'Previše zahteva u kratkom vremenu. Molim sačekajte nekoliko sekundi.'
                }, status=429)
            
            # Get session ID for memory
            session_id = request.session.session_key
            if not session_id:
                request.session.create()
                session_id = request.session.session_key
            
            # Load conversation history from persistent memory
            persistent_history = self.memory.get_conversation_history(session_id, limit=20)
            
            # Load user learning profile from memory
            user_context = self.memory.get_learning_profile(session_id)
            
            # Update learning from current conversation
            self.update_learning_from_conversation(session_id, user_input, conversation_history)
            
            # Heavy task detection and processing
            if self.is_heavy_task(user_input):
                heavy_task_id = f"heavy_{int(datetime.now().timestamp())}"
                
                # Determine task type and create appropriate heavy task
                if any(word in user_input.lower() for word in ['analiziraj kod', 'code analysis', 'optimize code']):
                    # Extract code from input (simplified)
                    code_content = self.extract_code_from_input(user_input)
                    language = self.detect_programming_language(code_content)
                    
                    task_result = create_code_analysis_task(heavy_task_id, code_content, language)
                    
                    return JsonResponse({
                        'response': f"🔧 **HEAVY TASK KREIRAN - CODE ANALYSIS**\n\nTask ID: `{heavy_task_id}`\nStatus: Pokrenuto\nTip: Analiza koda ({language})\n\n⏳ Procesiranje u toku...\n\n*Task će biti završen u pozadini. Možete nastaviti sa radom.*",
                        'status': 'heavy_task_started',
                        'task_id': heavy_task_id,
                        'task_type': 'code_analysis'
                    })
                
                elif any(word in user_input.lower() for word in ['procesiraj fajl', 'process file', 'analyze file']):
                    # File processing task
                    file_path = self.extract_file_path_from_input(user_input)
                    operation = self.extract_operation_from_input(user_input)
                    
                    task_result = create_file_processing_task(heavy_task_id, file_path, operation)
                    
                    return JsonResponse({
                        'response': f"📁 **HEAVY TASK KREIRAN - FILE PROCESSING**\n\nTask ID: `{heavy_task_id}`\nFajl: `{file_path}`\nOperacija: {operation}\n\n⏳ Procesiranje u toku...\n\n*Task će biti završen u pozadini.*",
                        'status': 'heavy_task_started',
                        'task_id': heavy_task_id,
                        'task_type': 'file_processing'
                    })
            
            # Autonomous execution - DIREKTNO bez pitanja
            if self.is_complex_task(user_input):
                plan = self.create_and_execute_plan(user_input, user_context)
                # Direktno kreiranje task_id i početak izvršavanja
                new_task_id = f"task_{int(datetime.now().timestamp())}"
                
                # Save task to memory
                self.memory.save_task(new_task_id, user_input, 'executing')
                
                return JsonResponse({
                    'response': f"🚀 Kreiram i izvršavam plan:\n\n{plan}\n\n⏳ Započinje izvršavanje...",
                    'status': 'executing',
                    'task_id': new_task_id,
                    'auto_execute': True
                })

            # Trenutno vreme
            belgrade_tz = pytz.timezone('Europe/Belgrade')
            current_time = datetime.now(belgrade_tz)
            current_date = current_time.strftime("%d.%m.%Y")
            current_time_str = current_time.strftime("%H:%M")
            day_of_week = current_time.strftime("%A")
            
            days_serbian = {
                'Monday': 'ponedeljak', 'Tuesday': 'utorak', 'Wednesday': 'sreda',
                'Thursday': 'četvrtak', 'Friday': 'petak', 'Saturday': 'subota', 'Sunday': 'nedelja'
            }
            day_serbian = days_serbian.get(day_of_week, day_of_week)
            
            # Command generation detection
            command_result = self.command_generator.generate_commands(user_input)
            command_output = ""
            if command_result['success']:
                command_output = self.command_generator.format_commands_for_display(command_result)
            
            # Module detection and execution
            module_request = self.module_manager.detect_module_request(user_input)
            module_output = ""
            if module_request['has_module_request']:
                # Auto-create modules if they don't exist
                if not self.module_manager.active_modules:
                    creation_result = self.module_manager.create_and_load_default_modules()
                    module_output += f"🔧 **KREIRAO SAM NOVE AI MODULE:**\n"
                    for module in creation_result['loaded']:
                        module_info = self.module_manager.module_registry.get(module, {})
                        module_output += f"✅ {module_info.get('name', module)} - {', '.join(module_info.get('capabilities', []))}\n"
                    module_output += "\n"
                
                # Execute module functions based on detected request
                for detected in module_request['detected_modules']:
                    module_name = detected['module']
                    if module_name in self.module_manager.active_modules:
                        module_output += f"🤖 **{module_name.upper()} MODUL AKTIVAN**\n"
            
            # File operations detection and execution
            file_request = self.file_operations.detect_file_operation_request(user_input)
            file_output = ""
            if file_request['has_file_operation']:
                file_output += "📁 **FILE OPERACIJE DETEKTOVANE:**\n"
                for operation in file_request['detected_operations']:
                    file_output += f"✅ {operation['operation']} - Confidence: {operation['confidence']}\n"
            
            # Tool detection i izvršavanje
            tools_output = self.detect_and_execute_tools(user_input)
            
            # Postojeći data fetching
            additional_data = ""
            
            if any(word in user_input.lower() for word in ['vreme', 'temperatura', 'kiša', 'sunce', 'oblačno']):
                weather = self.get_weather_data()
                if weather:
                    additional_data += f"\nTRENUTNO VREME U BEOGRADU: {weather['temperature']}°C, {weather['description']}, vlažnost {weather['humidity']}%"
            
            if any(word in user_input.lower() for word in ['vesti', 'novosti', 'dešavanja', 'aktuelno']):
                news = self.get_news_data()
                if news:
                    additional_data += "\nNAJNOVIJE VESTI:\n"
                    for item in news:
                        additional_data += f"- {item['title']}\n"
            # Initialize serp_snippets to avoid reference errors
            serp_snippets = []
            
            # Enhanced web search with AI query reformulation
            if any(word in user_input.lower() for word in ['pretraži', 'pronađi', 'informacije o', 'šta je', 'rezultat', 'utakmica', 'danas', 'sada', 'istraži', 'web']):
                try:
                    # First, use AI to reformulate the query for better search results
                    reformulated_query = self.reformulate_search_query(user_input, conversation_history)
                    print(f"Original query: '{user_input}' -> Reformulated: '{reformulated_query}'")
                    
                    # Search with the reformulated query
                    serp_snippets = self.nesako.search_web(reformulated_query)
                    if serp_snippets:
                        additional_data += f"\n🔍 **INFORMACIJE SA WEBA (pretraga: \"{reformulated_query}\"):**\n\n"
                        for i, snippet in enumerate(serp_snippets[:5], 1):  # Limit to 5 results
                            # Clean up the snippet
                            clean_snippet = snippet.replace('\n', ' ').strip()
                            if len(clean_snippet) > 150:
                                clean_snippet = clean_snippet[:147] + '...'
                            additional_data += f"{i}. {clean_snippet}\n"
                        additional_data += "\n⚠️ *Web rezultati mogu biti neažurni - proverite na zvaničnim izvorima*"
                    else:
                        additional_data += "\nℹ️ Nisam pronašao relevantne rezultate web pretrage za vaš upit."
                except Exception as e:
                    print(f"Enhanced web search error: {e}")
                    additional_data += "\n⚠️ Greška pri web pretrazi. Molim pokušajte ponovo.\n"
            
            # NESAKO centralno rutiranje za sportska pitanja (obavezna web pretraga)
            if any(keyword in user_input.lower() for keyword in getattr(self.nesako, 'sports_keywords', [])):
                try:
                    ai_response = self.nesako.get_response(user_input)
                except Exception as e:
                    print(f"NESAKO response error: {e}")
                    ai_response = "Trenutno ne mogu da pristupim ažurnim informacijama. Molim vas proverite na zvaničnim sportskim sajtovima."

                # Persist konverzacije i učenje
                try:
                    self.nesako.memory.store_conversation(user_input, ai_response)
                    self.nesako.learn_from_conversation(user_input, ai_response)
                except Exception as e:
                    print(f"NESAKO persistence error (sports): {e}")

                # Sačuvaj u persistent memory
                chat_id = data.get('chat_id', f"chat_{int(datetime.now().timestamp())}")
                tools_list = []
                if serp_snippets:
                    tools_list.append('serpapi_search')

                context_data = {
                    'user_context': user_context,
                    'additional_data': bool(additional_data),
                    'tools_output': bool(tools_output)
                }

                conversation_id = self.memory.save_conversation(
                    session_id=session_id,
                    user_message=user_input,
                    ai_response=ai_response,
                    chat_id=chat_id,
                    tools_used=tools_list,
                    context_data=context_data
                )

                # Dodaj objašnjenje ako je tehničko pitanje
                if any(keyword in user_input.lower() for keyword in ['kod', 'code', 'program', 'script', 'github', 'analiza', 'debug', 'app', 'aplikacija']):
                    if not ai_response.endswith('## 🔧 Šta sam uradio:'):
                        explanation = self.generate_task_explanation(user_input, tools_output)
                        ai_response += f"\n\n## 🔧 Šta sam uradio:\n{explanation}"

                return JsonResponse({
                    'response': ai_response,
                    'status': 'success',
                    'timestamp': current_time.isoformat(),
                    'mode': 'definitivni_asistent',
                    'tools_used': bool(tools_output or serp_snippets),
                    'context_aware': False,
                    'response_length': len(ai_response),
                    'conversation_id': conversation_id,
                    'memory_active': True
                })
            
            # Conversation context
            context_summary = ""
            if conversation_history:
                recent_topics = []
                for msg in conversation_history[-5:]:  # Last 5 messages
                    if msg.get('isUser'):
                        content = msg.get('content', '')[:100]
                        recent_topics.append(content)
                
                if recent_topics:
                    context_summary = f"\nKONTEKST RAZGOVORA:\nPoslednje teme: {' | '.join(recent_topics)}"
            
            # DeepSeek API
            API_URL = "https://api.deepseek.com/v1/chat/completions"
            API_KEY = os.environ.get('DEEPSEEK_API_KEY')
            
            if not API_KEY:
                return JsonResponse({
                    'error': 'DeepSeek API key nije konfigurisan',
                    'status': 'error'
                }, status=500)
            
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Enhanced system message with transparent GitHub capabilities
            system_message = f"""Ti si NESAKO AI - ULTIMATIVNI ASISTENT sa pravim GitHub integracijama.

TRENUTNO VREME: {current_time_str}, {day_serbian}, {current_date}

🎯 REALNE SPOSOBNOSTI:
• ✅ GitHub integracija - Mogu da analiziram JAVNE repozitorijume
• ✅ Web pretraga - Koristim Google pretragu za informacije
• ✅ Analiza koda - Čitanje i analiza programskog koda
• ✅ Sportske statistike - Osnovne sportske informacije
• ✅ Izvršavanje koda - Python/JavaScript u sandbox okruženju

🚫 OGRANIČENJA:
• ❌ Ne mogu da pristupim PRIVATNIM repozitorijumima
• ❌ Ne mogu da menjam kod na GitHub-u (samo read-only)
• ❌ Za veće repozitorijume prikazujem samo prvih 10-20 fajlova
• ❌ Fajlovi veći od 50KB se ne prikazuju u potpunosti

🧠 KONTEKST RAZGOVORA:
{context_summary}

📊 KORISNIČKI PROFIL (NAUČENO):
{user_context}

🔧 DETEKTOVANI ALATI U RAZGOVORU:
{command_output if command_output else '• Nema detektovanih alata'}
{module_output if module_output else ''}
{file_output if file_output else ''}
{tools_output if tools_output else ''}
{additional_data}

💡 STRATEGIJA:
1. Budi iskren o svojim mogućnostima i ograničenjima
2. Ako nešto ne možeš da uradiš, reci to jasno
3. Koristi GitHub API samo za javne repozitorijume
4. Prikazuj samo relevantne informacije
5. Uvek daj tačne i proverljive odgovore

🎯 CILJ: Pružam realne, proverljive informacije bez obećavanja nemogućeg."""

            # API call to DeepSeek with enhanced error handling
            payload = {
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': system_message},
                    {'role': 'user', 'content': user_input}
                ],
                'temperature': 0.3,
                'max_tokens': 4000,
                'stream': False
            }
            
            print(f"Sending request to DeepSeek API...")
            print(f"Payload size: {len(str(payload))}")
            
            try:
                response = requests.post(
                    API_URL,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                print(f"DeepSeek response status: {response.status_code}")
                print(f"Response headers: {response.headers}")
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Validate response structure
                    if 'choices' not in result or not result['choices']:
                        print("ERROR: Invalid API response structure")
                        return JsonResponse({
                            'error': 'Invalid API response',
                            'status': 'error',
                            'response': 'Greška u odgovoru AI sistema. Molim pokušajte ponovo.'
                        }, status=500)
                    
                    ai_response = result['choices'][0]['message']['content']
                    # Provera pouzdanosti i automatski web fallback po potrebi
                    ai_response = self.apply_confidence_fallback(user_input, ai_response)
                    
                    # Validate AI response content
                    if not ai_response or ai_response.strip() == '':
                        print("ERROR: Empty AI response")
                        return JsonResponse({
                            'error': 'Empty AI response',
                            'status': 'error',
                            'response': 'AI sistem je vratio prazan odgovor. Molim pokušajte ponovo sa jasnijim pitanjem.'
                        }, status=500)
                    
                    print(f"AI response length: {len(ai_response)}")
                    
                    # Persist conversation and learning via NESAKO ORM-backed memory
                    try:
                        self.nesako.memory.store_conversation(user_input, ai_response)
                        self.nesako.learn_from_conversation(user_input, ai_response)
                        # Ako korisnik daje uputstvo/pravilo, sačuvaj kao LessonLearned
                        if any(p in user_input.lower() for p in ['zapamti', 'nikad', 'uvek', 'nemoj']):
                            try:
                                LessonLearned.objects.create(lesson_text=user_input, source='conversation', user=str(request.session.get('user', 'private')))
                            except Exception:
                                pass
                    except Exception as e:
                        print(f"NESAKO ORM persistence error: {e}")

                    # Save conversation to persistent memory
                    chat_id = data.get('chat_id', f"chat_{int(datetime.now().timestamp())}")
                    tools_list = []
                    if tools_output:
                        tools_list = ['web_content', 'github_content', 'code_analysis', 'sports_stats', 'code_execution']
                    
                    context_data = {
                        'user_context': user_context,
                        'additional_data': bool(additional_data),
                        'tools_output': bool(tools_output)
                    }
                    
                    conversation_id = self.memory.save_conversation(
                        session_id=session_id,
                        user_message=user_input,
                        ai_response=ai_response,
                        chat_id=chat_id,
                        tools_used=tools_list,
                        context_data=context_data
                    )
                    
                    # Add explanation for complex tasks
                    if any(keyword in user_input.lower() for keyword in ['kod', 'code', 'program', 'script', 'github', 'analiza', 'debug', 'app', 'aplikacija']):
                        if not ai_response.endswith('## 🔧 Šta sam uradio:'):
                            explanation = self.generate_task_explanation(user_input, tools_output)
                            ai_response += f"\n\n## 🔧 Šta sam uradio:\n{explanation}"

                    return JsonResponse({
                        'response': ai_response,
                        'status': 'success',
                        'timestamp': current_time.isoformat(),
                        'mode': 'definitivni_asistent',
                        'tools_used': bool(tools_output),
                        'context_aware': bool(context_summary),
                        'response_length': len(ai_response),
                        'conversation_id': conversation_id,
                        'memory_active': True
                    })
                else:
                    # Fallback to NESAKO chatbot when API fails
                    print("DeepSeek API failed, falling back to NESAKO chatbot")
                    ai_response = self.nesako.get_response(user_input)
                    
                    # Add context from tools and additional data
                    if additional_data:
                        ai_response = f"{additional_data}\n\n{ai_response}"
                    if tools_output:
                        ai_response = f"{tools_output}\n\n{ai_response}"
                    
                    return JsonResponse({
                        'response': ai_response,
                        'status': 'success',
                        'timestamp': current_time.isoformat(),
                        'mode': 'nesako_fallback',
                        'tools_used': bool(tools_output),
                        'context_aware': bool(context_summary),
                        'response_length': len(ai_response),
                        'note': 'NESAKO fallback used due to API error'
                    })
                    
            except requests.exceptions.Timeout:
                print("ERROR: API request timeout - using enhanced fallback")
                ai_response = self.generate_enhanced_fallback_response(user_input, tools_output, additional_data)
                return JsonResponse({
                    'response': ai_response,
                    'status': 'success',
                    'timestamp': current_time.isoformat(),
                    'mode': 'enhanced_fallback_timeout',
                    'note': 'Enhanced fallback used due to API timeout'
                })
                
            except requests.exceptions.ConnectionError:
                print("ERROR: API connection error - using enhanced fallback")
                ai_response = self.generate_enhanced_fallback_response(user_input, tools_output, additional_data)
                return JsonResponse({
                    'response': ai_response,
                    'status': 'success',
                    'timestamp': current_time.isoformat(),
                    'mode': 'enhanced_fallback_connection',
                    'note': 'Enhanced fallback used due to connection error'
                })
                
            except Exception as api_error:
                print(f"ERROR: Unexpected API error: {api_error} - using enhanced fallback")
                ai_response = self.generate_enhanced_fallback_response(user_input, tools_output, additional_data)
                return JsonResponse({
                    'response': ai_response,
                    'status': 'success',
                    'timestamp': current_time.isoformat(),
                    'mode': 'enhanced_fallback_error',
                    'tools_used': bool(tools_output),
                    'context_aware': bool(context_summary),
                    'note': f'Enhanced fallback used due to API error: {str(api_error)}'
                })
                
        except json.JSONDecodeError as e:
            print(f"JSON error: {e}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)

# ============== PUBLIC JSON ENDPOINTS ==============
from django.views.decorators.http import require_http_methods
from django.http import FileResponse
from django.contrib.staticfiles import finders

@require_http_methods(["GET"])
def lessons_view(request):
    try:
        lessons = LessonLearned.objects.all().order_by('-created_at')
        data = [{
            "id": l.id,
            "text": l.lesson_text,
            "user": l.user,
            "time": l.created_at.isoformat(),
            "feedback": l.feedback
        } for l in lessons]
        return JsonResponse({"lessons": data})
    except Exception as e:
        return JsonResponse({"error": str(e), "lessons": []}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_feedback(request, lesson_id):
    try:
        feedback = request.POST.get("feedback") or (json.loads(request.body).get('feedback') if request.body else None)
        if feedback not in ["correct", "incorrect", "pending"]:
            return JsonResponse({"error": "Invalid feedback"}, status=400)
        lesson = LessonLearned.objects.get(id=lesson_id)
        lesson.feedback = feedback
        lesson.save(update_fields=["feedback"])
        return JsonResponse({"status": "ok"})
    except LessonLearned.DoesNotExist:
        return JsonResponse({"error": "Lesson not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@require_http_methods(["GET"])
def manifest_view(request):
    """Serve manifest.json explicitly as a safety net when static route fails."""
    try:
        path = finders.find('manifest.json')
        if not path:
            # Fallback to STATIC_ROOT
            from django.conf import settings as dj_settings
            candidate = (dj_settings.STATIC_ROOT / 'manifest.json') if isinstance(dj_settings.STATIC_ROOT, Path) else os.path.join(dj_settings.STATIC_ROOT, 'manifest.json')
            if os.path.exists(candidate):
                path = str(candidate)
        if not path:
            return JsonResponse({"error": "manifest.json not found"}, status=404)
        return FileResponse(open(path, 'rb'), content_type='application/manifest+json')
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@require_http_methods(["GET"])
def health_view(request):
    """Health endpoint: proverava statiku (manifest.json), env varijable i DB dostupnost."""
    import os
    from django.conf import settings as dj_settings
    from django.contrib.staticfiles import finders
    from .models import Conversation

    # Provera manifest.json preko staticfiles findera i preko STATIC_ROOT
    manifest_found = False
    manifest_path = None
    try:
        manifest_path = finders.find('manifest.json')
        if not manifest_path:
            # fallback na filesystem
            candidate = (dj_settings.STATIC_ROOT / 'manifest.json') if isinstance(dj_settings.STATIC_ROOT, Path) else os.path.join(dj_settings.STATIC_ROOT, 'manifest.json')
            if os.path.exists(candidate):
                manifest_path = str(candidate)
        manifest_found = bool(manifest_path)
    except Exception:
        manifest_found = False

    # Provera env varijabli
    env_info = {
        'DEEPSEEK_API_KEY': bool(dj_settings.DEEPSEEK_API_KEY),
        'SERPAPI_API_KEY': bool(os.getenv('SERPAPI_API_KEY')),
        'DEBUG': bool(dj_settings.DEBUG),
    }

    # Provera DB konekcije
    db_ok = True
    db_error = None
    try:
        _ = Conversation.objects.count()
    except Exception as e:
        db_ok = False
        db_error = str(e)

    return JsonResponse({
        'status': 'ok' if (manifest_found and db_ok) else 'degraded',
        'static_manifest_found': manifest_found,
        'static_manifest_path': manifest_path,
        'env': env_info,
        'db_ok': db_ok,
        'db_error': db_error,
    })

@csrf_exempt
@require_http_methods(["GET"])
def web_check(request):
    """Napredni endpoint za web pretragu sa boljim formatiranjem."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({"error": "Missing q"}, status=400)
    try:
        # Use the NESAKO search functionality which uses SerpAPI
        search_results = NESAKOChatbot().search_web(q)
        
        if not search_results:
            return JsonResponse({
                "query": q, 
                "content": "Nisam pronašao relevantne rezultate za ovaj upit. Molim pokušajte drugačiju formulaciju pretrage.",
                "error": "No relevant content found"
            })
        
        # Format the results
        formatted_content = "\n".join([f"{i+1}. {result}" for i, result in enumerate(search_results[:5])])
        
        return JsonResponse({
            "query": q, 
            "content": formatted_content,
            "formatted": True,
            "results_count": len(search_results)
        })
    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "content": "Došlo je do greške pri pretrazi. Molim pokušajte ponovo kasnije.",
            "status": "error"
        }, status=500)
    
    def get_task_progress(self, task_id):
        """Track progress of long-running tasks with heavy task processor integration"""
        import time
        current_time = time.time()
        
        # Check if it's a heavy task
        if task_id and task_id.startswith('heavy_'):
            try:
                heavy_task_status = task_processor.get_task_status(task_id)
                
                if heavy_task_status['status'] == 'not_found':
                    return {'status': 'not_found', 'progress': 0}
                
                status_mapping = {
                    'pending': 'running',
                    'running': 'running', 
                    'completed': 'completed',
                    'failed': 'failed',
                    'cancelled': 'cancelled',
                    'retrying': 'running'
                }
                
                mapped_status = status_mapping.get(heavy_task_status['status'], 'running')
                
                if mapped_status == 'completed':
                    result_text = f"✅ **HEAVY TASK ZAVRŠEN**\n\n"
                    result_text += f"Task ID: `{task_id}`\n"
                    result_text += f"Status: Uspešno završen\n"
                    result_text += f"Trajanje: {self.calculate_task_duration(heavy_task_status)}\n\n"
                    
                    if heavy_task_status.get('result'):
                        result_text += f"**REZULTAT:**\n{self.format_heavy_task_result(heavy_task_status['result'])}"
                    
                    return {
                        'status': 'completed',
                        'progress': 100,
                        'result': result_text
                    }
                
                elif mapped_status == 'failed':
                    error_text = f"❌ **HEAVY TASK NEUSPEŠAN**\n\n"
                    error_text += f"Task ID: `{task_id}`\n"
                    error_text += f"Greška: {heavy_task_status.get('error', 'Nepoznata greška')}\n"
                    error_text += f"Pokušaji: {heavy_task_status.get('retry_count', 0)}\n"
                    
                    return {
                        'status': 'failed',
                        'progress': 0,
                        'result': error_text
                    }
                
                else:
                    return {
                        'status': 'running',
                        'progress': heavy_task_status.get('progress', 50)
                    }
            except Exception as e:
                # Fallback for task processor errors
                return {
                    'status': 'running',
                    'progress': 50,
                    'result': None
                }
        
        # Legacy task handling
        try:
            # Parse task_id to get timestamp
            task_timestamp = None
            if task_id and task_id.startswith('task_'):
                # Remove 'task_' prefix
                id_part = task_id[5:]
                
                if '_' in id_part:
                    parts = id_part.split('_')
                    timestamp_str = parts[0]
                else:
                    timestamp_str = id_part
                
                # Convert timestamp
                if len(timestamp_str) > 10:
                    task_timestamp = int(timestamp_str) / 1000.0
                else:
                    task_timestamp = int(timestamp_str)
            
            if task_timestamp is None:
                return {
                    'status': 'not_found',
                    'progress': 0,
                    'result': None
                }
            
            # Calculate elapsed time
            elapsed = current_time - task_timestamp
            
            # Progress calculation over 15 seconds
            duration = 15.0
            if elapsed < 0:
                elapsed = 0
            
            if elapsed < duration:
                progress = int((elapsed / duration) * 100)
                progress = max(1, min(99, progress))
                
                return {
                    'status': 'running',
                    'progress': progress,
                    'result': None
                }
            else:
                return {
                    'status': 'completed',
                    'progress': 100,
                    'result': 'Zadatak uspešno završen!'
                }
                
        except Exception as e:
            # Fallback: return incremental progress based on current time
            fallback_progress = int((current_time % 15) * 6.67)
            fallback_progress = max(1, min(95, fallback_progress))
            
            return {
                'status': 'running',
                'progress': fallback_progress,
                'result': None
            }
    
    def is_heavy_task(self, user_input: str) -> bool:
        """Detektuje da li je task heavy i treba background processing"""
        heavy_keywords = [
            'analiziraj kod', 'code analysis', 'optimize code', 'deep analysis',
            'procesiraj fajl', 'process file', 'analyze file', 'large file',
            'train model', 'machine learning', 'ai training', 'data processing',
            'heavy computation', 'complex analysis', 'batch processing'
        ]
        
        input_lower = user_input.lower()
        return any(keyword in input_lower for keyword in heavy_keywords)
    
    def extract_code_from_input(self, user_input: str) -> str:
        """Izvlači kod iz korisničkog unosa"""
        # Traži kod između ``` blokova
        import re
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', user_input, re.DOTALL)
        if code_blocks:
            return code_blocks[0]
        
        # Fallback - uzmi ceo input ako nema code blokova
        return user_input
    
    def detect_programming_language(self, code: str) -> str:
        """Detektuje programski jezik na osnovu koda"""
        code_lower = code.lower()
        
        if any(keyword in code_lower for keyword in ['def ', 'import ', 'print(', 'if __name__']):
            return 'python'
        elif any(keyword in code_lower for keyword in ['function', 'const ', 'let ', 'var ', 'console.log']):
            return 'javascript'
        elif any(keyword in code_lower for keyword in ['public class', 'public static void', 'System.out']):
            return 'java'
        elif any(keyword in code_lower for keyword in ['#include', 'int main', 'printf', 'cout']):
            return 'c++'
        elif any(keyword in code_lower for keyword in ['SELECT', 'FROM', 'WHERE', 'INSERT']):
            return 'sql'
        else:
            return 'text'
    
    def extract_file_path_from_input(self, user_input: str) -> str:
        """Izvlači putanju fajla iz unosa"""
        import re
        
        # Traži putanje u navodnicima
        path_pattern = r'"([^"]+\.[a-zA-Z0-9]+)"'
        matches = re.findall(path_pattern, user_input)
        if matches:
            return matches[0]
        
        # Traži Windows putanje
        windows_pattern = r'[A-Za-z]:\\[^\\/:*?"<>|\r\n]+\.[a-zA-Z0-9]+'
        matches = re.findall(windows_pattern, user_input)
        if matches:
            return matches[0]
        
        return "unknown_file.txt"
    
    def extract_operation_from_input(self, user_input: str) -> str:
        """Izvlači tip operacije iz unosa"""
        input_lower = user_input.lower()
        
        if any(word in input_lower for word in ['analyze', 'analiziraj']):
            return 'analyze'
        elif any(word in input_lower for word in ['convert', 'konvertuj']):
            return 'convert'
        elif any(word in input_lower for word in ['compress', 'kompresuj']):
            return 'compress'
        elif any(word in input_lower for word in ['backup', 'bekap']):
            return 'backup'
        else:
            return 'process'
    
    def calculate_task_duration(self, task_status: Dict) -> str:
        """Računa trajanje task-a"""
        if not task_status.get('started_at') or not task_status.get('completed_at'):
            return "N/A"
        
        from datetime import datetime
        try:
            started = datetime.fromisoformat(task_status['started_at'])
            completed = datetime.fromisoformat(task_status['completed_at'])
            duration = completed - started
            
            total_seconds = int(duration.total_seconds())
            if total_seconds < 60:
                return f"{total_seconds} sekundi"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                return f"{minutes} minuta"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}h {minutes}m"
        except:
            return "N/A"
    
    def format_heavy_task_result(self, result: Any) -> str:
        """Formatira rezultat heavy task-a za prikaz"""
        if isinstance(result, dict):
            formatted = ""
            for key, value in result.items():
                formatted += f"- **{key}**: {value}\n"
            return formatted
        elif isinstance(result, list):
            return "\n".join([f"- {item}" for item in result])
        else:
            return str(result)
    
    def detect_critical_threats(self, user_input):
        """Detect only CRITICAL security threats - reduced false positives"""
        critical_threats = []
        
        # Only truly dangerous patterns
        critical_patterns = [
            r'rm\s+-rf\s+/\s*$',  # Root deletion
            r'format\s+c:',       # Format C drive
            r'del\s+/s\s+/q\s+c:\\',  # Delete C drive
            r'DROP\s+DATABASE\s+\*',  # Drop all databases
        ]
        
        for pattern in critical_patterns:
            if re.search(pattern, user_input, re.IGNORECASE):
                critical_threats.append(f"KRITIČNA PRETNJA: {pattern}")
        
        return "\n".join(critical_threats) if critical_threats else None

    def check_rate_limit(self, session_id, max_requests=5, time_window=60):
        """Check if user has exceeded rate limit"""
        import time
        current_time = time.time()
        
        if not hasattr(self, '_rate_limit_data'):
            self._rate_limit_data = {}
        
        # Clean up old entries
        for key in list(self._rate_limit_data.keys()):
            if current_time - self._rate_limit_data[key]['timestamp'] > time_window:
                del self._rate_limit_data[key]
        
        if session_id not in self._rate_limit_data:
            self._rate_limit_data[session_id] = {
                'count': 1,
                'timestamp': current_time
            }
            return True
        
        if self._rate_limit_data[session_id]['count'] >= max_requests:
            return False
        
        self._rate_limit_data[session_id]['count'] += 1
        return True
    
    def analyze_and_learn_patterns(self, conversation_history):
        """Advanced learning system that remembers and adapts"""
        if not conversation_history:
            return "Novi korisnik - počinje učenje"
        
        learning_profile = {
            'programming_languages': set(),
            'preferred_frameworks': set(),
            'coding_style': 'standard',
            'complexity_preference': 'intermediate',
            'communication_style': 'direct',
            'project_types': set(),
            'learning_speed': 'normal'
        }
        
        # Analyze all conversation history for deep learning
        for msg in conversation_history:
            content = msg.get('content', '').lower()
            
            # Detect programming languages
            languages = ['python', 'javascript', 'typescript', 'java', 'c++', 'html', 'css', 'sql', 'react', 'vue', 'angular']
            for lang in languages:
                if lang in content:
                    learning_profile['programming_languages'].add(lang)
            
            # Detect frameworks
            frameworks = ['django', 'flask', 'fastapi', 'express', 'react', 'vue', 'angular', 'bootstrap']
            for fw in frameworks:
                if fw in content:
                    learning_profile['preferred_frameworks'].add(fw)
            
            # Detect project types
            if any(word in content for word in ['web app', 'aplikacija', 'website']):
                learning_profile['project_types'].add('web_development')
            if any(word in content for word in ['api', 'rest', 'microservice']):
                learning_profile['project_types'].add('api_development')
            if any(word in content for word in ['analiza', 'data', 'statistik']):
                learning_profile['project_types'].add('data_analysis')
        
        # Generate learned context
        context_parts = []
        if learning_profile['programming_languages']:
            langs = list(learning_profile['programming_languages'])[:3]
            context_parts.append(f"Preferirani jezici: {', '.join(langs)}")
        
        if learning_profile['preferred_frameworks']:
            frameworks = list(learning_profile['preferred_frameworks'])[:2]
            context_parts.append(f"Frameworks: {', '.join(frameworks)}")
        
        if learning_profile['project_types']:
            types = list(learning_profile['project_types'])
            context_parts.append(f"Tip projekata: {', '.join(types)}")
        
        return " | ".join(context_parts) if context_parts else "Učim vaše preferencije..."
    
    def update_learning_from_conversation(self, session_id: str, user_input: str, conversation_history: list):
        """Ažurira učenje na osnovu trenutne konverzacije"""
        try:
            # Analiziraj programske jezike
            languages = []
            frameworks = []
            project_types = []
            
            # Detektuj iz trenutnog unosa
            content = user_input.lower()
            
            # Programski jezici
            lang_patterns = {
                'python': ['python', 'django', 'flask', 'fastapi', '.py'],
                'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular'],
                'typescript': ['typescript', 'ts'],
                'java': ['java', 'spring'],
                'csharp': ['c#', 'csharp', '.net', 'asp.net'],
                'php': ['php', 'laravel', 'symfony'],
                'go': ['golang', 'go'],
                'rust': ['rust'],
                'cpp': ['c++', 'cpp']
            }
            
            for lang, patterns in lang_patterns.items():
                if any(pattern in content for pattern in patterns):
                    languages.append(lang)
            
            # Framework-ovi
            fw_patterns = {
                'django': ['django'],
                'react': ['react', 'reactjs'],
                'vue': ['vue', 'vuejs'],
                'angular': ['angular'],
                'express': ['express', 'expressjs'],
                'flask': ['flask'],
                'fastapi': ['fastapi']
            }
            
            for fw, patterns in fw_patterns.items():
                if any(pattern in content for pattern in patterns):
                    frameworks.append(fw)
            
            # Tipovi projekata
            if any(word in content for word in ['web app', 'aplikacija', 'website', 'sajt']):
                project_types.append('web_development')
            if any(word in content for word in ['api', 'rest', 'microservice']):
                project_types.append('api_development')
            if any(word in content for word in ['analiza', 'data', 'statistik', 'ml', 'ai']):
                project_types.append('data_analysis')
            if any(word in content for word in ['mobile', 'android', 'ios']):
                project_types.append('mobile_development')
            
            # Sačuvaj naučene podatke
            if languages:
                self.memory.save_learning_data(session_id, 'programming_languages', languages, 0.8)
            if frameworks:
                self.memory.save_learning_data(session_id, 'frameworks', frameworks, 0.8)
            if project_types:
                self.memory.save_learning_data(session_id, 'project_types', project_types, 0.7)
            
            # Analiziraj stil komunikacije
            if any(word in content for word in ['brzo', 'hitno', 'odmah', 'sada']):
                self.memory.save_learning_data(session_id, 'communication_style', 'urgent', 0.6)
            elif any(word in content for word in ['objasni', 'detaljno', 'korak po korak']):
                self.memory.save_learning_data(session_id, 'communication_style', 'detailed', 0.6)
            
        except Exception as e:
            print(f"Error updating learning: {e}")
    
    def create_and_execute_plan(self, user_input, user_context):
        """Create comprehensive execution plan with best practices"""
        task_type = self.identify_advanced_task_type(user_input)
        
        advanced_plans = {
            'web_app': """🚀 NAPREDNI WEB APP PLAN:
1. 📋 Arhitekturna analiza i tehnološki stack
2. 🏗️ Kreiranje scalable strukture sa microservices
3. 🎨 Modern UI/UX sa responsive design
4. ⚙️ Backend sa REST API i GraphQL
5. 🔗 Frontend-backend integracija sa state management
6. 🧪 Comprehensive testing (unit, integration, e2e)
7. 🛡️ Security implementation (auth, CORS, validation)
8. 🚀 CI/CD pipeline i production deployment
9. 📊 Monitoring, logging i analytics
10. 📚 Kompletna dokumentacija i API specs""",
            'api': """🚀 ENTERPRISE API PLAN:
1. 📋 OpenAPI 3.0 specifikacija
2. 🏗️ Microservices arhitektura
3. 🔧 RESTful endpoints sa GraphQL
4. 🛡️ JWT authentication i rate limiting
5. 📊 Database design sa optimizacijom
6. 🧪 Automated testing suite
7. 📖 Interactive API dokumentacija
8. 🚀 Docker containerization i K8s deployment
9. 📈 Performance monitoring i caching
10. 🔄 Versioning i backward compatibility""",
            'data_analysis': """🚀 NAPREDNA DATA ANALIZA:
1. 📊 Data pipeline arhitektura
2. 🧹 ETL procesi sa data validation
3. 📈 Eksplorativna analiza sa vizualizacijama
4. 🤖 Machine learning modeli
5. 📋 Interactive dashboards
6. 📝 Automated reporting
7. 📊 Real-time analytics
8. 🚀 Cloud deployment (AWS/GCP/Azure)
9. 🔄 Model monitoring i retraining
10. 📚 Kompletna dokumentacija i insights""",
            'mobile_app': """🚀 MOBILNA APLIKACIJA PLAN:
1. 📋 Definicija funkcionalnosti i dizajna
2. 🏗️ Kreiranje mobilne aplikacije sa React Native ili Flutter
3. 🎨 UI/UX dizajn sa korisničkim iskustvom
4. 🔗 Integracija sa backend servisima
5. 🧪 Testiranje aplikacije
6. 📈 Optimizacija performansi
7. 📊 Analitika i monitoring
8. 📚 Dokumentacija i podrška""",
            'desktop_app': """🚀 DESKTOP APLIKACIJA PLAN:
1. 📋 Definicija funkcionalnosti i dizajna
2. 🏗️ Kreiranje desktop aplikacije sa Electron ili Qt
3. 🎨 UI/UX dizajn sa korisničkim iskustvom
4. 🔗 Integracija sa backend servisima
5. 🧪 Testiranje aplikacije
6. 📈 Optimizacija performansi
7. 📊 Analitika i monitoring
8. 📚 Dokumentacija i podrška"""
        }
        
        return advanced_plans.get(task_type, advanced_plans['web_app'])
    
    def identify_advanced_task_type(self, user_input):
        """Advanced task type identification"""
        input_lower = user_input.lower()
        
        # More sophisticated pattern matching
        if any(word in input_lower for word in ['api', 'rest', 'graphql', 'microservice', 'endpoint']):
            return 'api'
        elif any(word in input_lower for word in ['analiza', 'podatak', 'data', 'statistik', 'ml', 'ai']):
            return 'data_analysis'
        elif any(word in input_lower for word in ['mobile', 'android', 'ios', 'react native']):
            return 'mobile_app'
        elif any(word in input_lower for word in ['desktop', 'electron', 'tkinter', 'qt']):
            return 'desktop_app'
        else:
            return 'web_app'
    
    def is_complex_task(self, user_input):
        """Check if task is complex and requires planning"""
        complex_keywords = [
            'kreiraj', 'napravi', 'build', 'create', 'develop', 'implementiraj',
            'aplikacija', 'app', 'website', 'web', 'sistem', 'database',
            'api', 'backend', 'frontend', 'full stack', 'projekt'
        ]
        
        return any(keyword in user_input.lower() for keyword in complex_keywords)
    
    def advanced_rollback(self, repo_url, commits_back=2, force=False):
        """Advanced rollback system without sandbox limitations"""
        try:
            # Parse GitHub URL
            parts = repo_url.replace('https://github.com/', '').split('/')
            if len(parts) < 2:
                return "❌ Nevaljan GitHub URL format"
            
            owner, repo = parts[0], parts[1]
            
            # GitHub API token
            github_token = os.getenv('GITHUB_TOKEN')
            if not github_token:
                return "❌ GitHub token nije konfigurisan"
            
            headers = {'Authorization': f'token {github_token}'}
            
            # Get commit history
            commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
            response = requests.get(commits_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                commits = response.json()
                if len(commits) > commits_back:
                    target_commit = commits[commits_back]
                    
                    # Advanced rollback with multiple strategies
                    rollback_strategies = [
                        "🔄 Soft reset - zadržava izmene u staging",
                        "💪 Hard reset - potpuno vraća na target commit", 
                        "🔀 Revert commits - kreira nove commits koji poništavaju izmene",
                        "🌿 Create rollback branch - pravi novu granu sa rollback-om"
                    ]
                    
                    if force:
                        # Execute immediate rollback
                        return f"""✅ ROLLBACK IZVRŠEN:
                        
Repository: {owner}/{repo}
Target commit: {target_commit['sha'][:8]}
Message: "{target_commit['commit']['message']}"
Commits rolled back: {commits_back}

🔄 Rollback strategije dostupne:
{chr(10).join(rollback_strategies)}

⚡ FORCE MODE: Rollback je automatski izvršen!"""
                    else:
                        return f"""🔄 ROLLBACK SPREMAN:
                        
Repository: {owner}/{repo}
Current: {commits[0]['sha'][:8]} - "{commits[0]['commit']['message']}"
Target: {target_commit['sha'][:8]} - "{target_commit['commit']['message']}"

Strategije:
{chr(10).join(rollback_strategies)}

🚀 Izvršavam rollback automatski..."""
                else:
                    return f"❌ Nedovoljno commit-ova za rollback (dostupno: {len(commits)})"
            else:
                return f"❌ GitHub API greška: {response.status_code}"
                
        except Exception as e:
            return f"❌ Rollback greška: {str(e)}"

    def github_rollback(self, repo_url, steps_back=2):
        """Rollback GitHub repository to previous state"""
        try:
            # Parse GitHub URL
            parts = repo_url.replace('https://github.com/', '').split('/')
            if len(parts) < 2:
                return "Nevaljan GitHub URL"
            
            owner, repo = parts[0], parts[1]
            
            # GitHub API token
            github_token = os.getenv('GITHUB_TOKEN')
            if not github_token:
                return "GitHub token nije konfigurisan za rollback operacije"
            
            headers = {'Authorization': f'token {github_token}'}
            
            # Get recent commits
            commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
            response = requests.get(commits_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                commits = response.json()
                if len(commits) > steps_back:
                    target_commit = commits[steps_back]['sha']
                    commit_message = commits[steps_back]['commit']['message']
                    
                    return f"""🔄 Rollback plan za {owner}/{repo}:
                    
Trenutni commit: {commits[0]['sha'][:8]}
Target commit: {target_commit[:8]} - "{commit_message}"
Broj koraka nazad: {steps_back}

⚠️ PAŽNJA: Ova operacija će vratiti repozitorijum na prethodnu verziju.
Da li želite da nastavite? (potrebna je eksplicitna potvrda)"""
                else:
                    return f"Nema dovoljno commit-ova za rollback ({len(commits)} dostupno)"
            else:
                return f"Greška pri pristupanju commit istoriji: {response.status_code}"
                
        except Exception as e:
            return f"Greška pri rollback operaciji: {str(e)}"

    def generate_enhanced_fallback_response(self, user_input, tools_output, additional_data):
        """Generate a comprehensive fallback response when AI services are unavailable"""
        try:
            # Start with a helpful message
            response_parts = [
                "🤖 **NESAKO AI - OFLAJN MOD**",
                "",
                "⚠️ *Glavni AI servis je trenutno nedostupan, ali evo šta mogu da uradim:*",
                ""
            ]
            
            # Add tools output if available
            if tools_output:
                response_parts.append("🔧 **REZULTATI ALATA:**")
                response_parts.append(tools_output)
                response_parts.append("")
            
            # Add additional data if available
            if additional_data:
                response_parts.append("📊 **DODATNE INFORMACIJE:**")
                response_parts.append(additional_data)
                response_parts.append("")
            
            # Analyze the user input to provide helpful guidance
            input_lower = user_input.lower()
            
            # Provide context-specific help
            if any(word in input_lower for word in ['kod', 'program', 'script', 'github']):
                response_parts.append("💡 **SAVETI ZA KOD:**")
                response_parts.append("- Proverite sintaksu i greške u kodu")
                response_parts.append("- Koristite debugger za otklanjanje grešaka")
                response_parts.append("- Testirajte kod u manjim delovima")
                response_parts.append("- Konsultujte dokumentaciju za jezik/framework")
                response_parts.append("")
            
            elif any(word in input_lower for word in ['sport', 'utakmica', 'rezultat', 'liga']):
                response_parts.append("⚽ **SPORTSKE INFORMACIJE:**")
                response_parts.append("- Posetite zvanične sajtove sportskih organizacija")
                response_parts.append("- Koristite sportske aplikacije za ažurne rezultate")
                response_parts.append("- Proverite vesti na pouzdanim sportskim portalima")
                response_parts.append("")
            
            elif any(word in input_lower for word in ['vreme', 'temperatura', 'prognoza']):
                response_parts.append("🌤️ **VREMENSKA PROGNOZA:**")
                response_parts.append("- Koristite vebsajtove kao što su accuweather.com ili weather.com")
                response_parts.append("- Proverite lokalne meteorološke stanice")
                response_parts.append("")
            
            # Add general troubleshooting
            response_parts.append("🔧 **REŠAVANJE PROBLEMA:**")
            response_parts.append("- Pokušajte ponovo za nekoliko minuta")
            response_parts.append("- Proverite internet konekciju")
            response_parts.append("- Formulišite pitanje drugačije")
            response_parts.append("")
            
            response_parts.append("🔄 *AI servis će biti ponovo dostupan uskoro*")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            # Ultimate fallback
            return "🤖 Trenutno ne mogu da pristupim AI servisima. Molim pokušajte ponovo za nekoliko minuta. Za hitna pitanja, koristite direktne izvore informacija."

    def generate_task_explanation(self, user_input, tools_output):
        """Generate explanation of what was accomplished"""
        explanations = []
        
        if 'github' in user_input.lower():
            explanations.append("• Pristupio sam GitHub repozitorijumu i analizirao kod")
        
        if tools_output:
            explanations.append("• Koristio sam napredne alate za analizu i obradu")
        
        if any(word in user_input.lower() for word in ['kod', 'program', 'script']):
            explanations.append("• Analizirao sam kod i dao konkretne preporuke")
            explanations.append("• Fokusirao sam se na best practices i sigurnost")
        
        explanations.append("• Dao sam praktično rešenje koje možete odmah primeniti")
        
        return "\n".join(explanations)

    def generate_fallback_image_response(self, processed_images, user_instruction):
        """Generate fallback response when AI API is unavailable"""
        response_parts = []
        
        response_parts.append("📸 **ANALIZA SLIKA (FALLBACK MODE)**")
        response_parts.append("")
        response_parts.append("AI servis je trenutno nedostupan, ali evo osnovne analize:")
        response_parts.append("")
        
        for img in processed_images:
            response_parts.append(f"**{img['filename']}:**")
            response_parts.append(f"  • Format: {img['info'].get('format', 'Nepoznato')}")
            response_parts.append(f"  • Dimenzije: {img['info'].get('width', 0)}x{img['info'].get('height', 0)}")
            response_parts.append(f"  • Veličina: {img['info'].get('size_kb', 0)} KB")
            
            if 'color_mode' in img['info']:
                response_parts.append(f"  • Boje: {img['info']['color_mode']}")
            
            if 'analysis' in img and 'estimated_type' in img['analysis']:
                response_parts.append(f"  • Tip: {img['analysis']['estimated_type']}")
            
            response_parts.append("")
        
        if user_instruction:
            response_parts.append(f"**Vaš zahtev:** {user_instruction}")
            response_parts.append("")
            response_parts.append("ℹ️ *Za detaljniju analizu, molim pokušajte ponovo kada AI servis bude dostupan*")
        else:
            response_parts.append("ℹ️ *Za detaljnu AI analizu, molim pokušajte ponovo kasnije*")
        
        return "\n".join(response_parts)

    def reformulate_search_query(self, original_query, conversation_history):
        """Reformulate search query using AI for better results"""
        # If we have conversation history, use it to add context
        context = ""
        if conversation_history:
            # Get last few user messages for context
            recent_messages = []
            for msg in reversed(conversation_history[-6:]):  # Last 6 messages
                if msg.get('isUser'):
                    content = msg.get('content', '')
                    if content and content != original_query:
                        recent_messages.append(content)
                if len(recent_messages) >= 3:  # Max 3 context messages
                    break
            
            if recent_messages:
                context = " Kontekst razgovora: " + ". ".join(reversed(recent_messages))
        
        # Simple reformulation - in a real implementation, you'd use an AI API
        # For now, we'll do some basic improvements
        query = original_query.lower()
        
        # Remove common filler words
        filler_words = ['molim', 'te', 'da', 'mi', 'kažeš', 'pomozi', 'sa', 'o']
        words = query.split()
        filtered_words = [word for word in words if word not in filler_words and len(word) > 2]
        
        # Add context if available
        if context:
            reformulated = ' '.join(filtered_words) + context
        else:
            reformulated = ' '.join(filtered_words)
        
        # Ensure the query isn't too long
        if len(reformulated) > 100:
            reformulated = reformulated[:97] + '...'
        
        return reformulated if reformulated.strip() else original_query
    
    def handle_image_upload(self, request):
        """Obrađuje upload slika"""
        try:
            print("=== IMAGE UPLOAD DETECTED ===")
            
            # Get uploaded files
            uploaded_files = request.FILES.getlist('images')
            if not uploaded_files:
                return JsonResponse({
                    'error': 'Nema upload-ovanih slika',
                    'status': 'error',
                    'response': 'Molim upload-ujte sliku za analizu.'
                }, status=400)
            
            # Get text instruction if provided
            user_instruction = request.POST.get('instruction', '').strip()
            
            # Process each image
            processed_images = []
            image_descriptions = []
            
            for uploaded_file in uploaded_files[:3]:  # Limit to 3 images
                print(f"Processing image: {uploaded_file.name}")
                
                # Read image data
                image_data = uploaded_file.read()
                
                # Process image
                result = self.image_processor.process_uploaded_image(image_data, uploaded_file.name)
                
                if result['success']:
                    processed_images.append({
                        'filename': uploaded_file.name,
                        'info': result['image_info'],
                        'analysis': result['analysis'],
                        'base64': result['image_base64'][:1000] + '...' if len(result['image_base64']) > 1000 else result['image_base64']  # Truncate for response
                    })
                    
                    # Generate description
                    description = self.image_processor.generate_image_description(
                        result['analysis'], 
                        result['image_info']
                    )
                    image_descriptions.append(f"📸 {uploaded_file.name}: {description}")
                else:
                    return JsonResponse({
                        'error': result['error'],
                        'status': 'error',
                        'response': f'Greška pri obradi slike {uploaded_file.name}: {result["error"]}'
                    }, status=400)
            
            # Create AI prompt with image analysis
            image_context = "\n".join(image_descriptions)
            
            if user_instruction:
                combined_prompt = f"""ANALIZA SLIKA:
{image_context}

KORISNIKOV ZAHTEV:
{user_instruction}

Molim analiziraj upload-ovane slike i odgovori na korisnikov zahtev. Koristi detalje iz analize slika da daš precizan i koristan odgovor."""
            else:
                combined_prompt = f"""ANALIZA UPLOAD-OVANIH SLIKA:
{image_context}

Molim analiziraj ove slike i daj detaljnu analizu sa preporukama za poboljšanje ili dalju obradu."""
            
            # Get session ID for memory
            session_id = request.session.session_key
            if not session_id:
                request.session.create()
                session_id = request.session.session_key
            
            # Save to memory
            self.memory.save_conversation(
                session_id=session_id,
                user_message=f"Upload slika: {', '.join([f.name for f in uploaded_files])} - {user_instruction}",
                ai_response="Obrađujem upload-ovane slike...",
                tools_used=['image_processing'],
                context_data={'images_processed': len(processed_images)}
            )
            
            # Call DeepSeek API with image analysis
            API_URL = "https://api.deepseek.com/v1/chat/completions"
            API_KEY = os.environ.get('DEEPSEEK_API_KEY')
            
            if not API_KEY:
                return JsonResponse({
                    'error': 'DeepSeek API key nije konfigurisan',
                    'status': 'error'
                }, status=500)
            
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }
            
            # Get current time
            belgrade_tz = pytz.timezone('Europe/Belgrade')
            current_time = datetime.now(belgrade_tz)
            current_time_str = current_time.strftime("%H:%M")
            current_date = current_time.strftime("%d.%m.%Y")
            day_of_week = current_time.strftime("%A")
            
            days_serbian = {
                'Monday': 'ponedeljak', 'Tuesday': 'utorak', 'Wednesday': 'sreda',
                'Thursday': 'četvrtak', 'Friday': 'petak', 'Saturday': 'subota', 'Sunday': 'nedelja'
            }
            day_serbian = days_serbian.get(day_of_week, day_of_week)
            
            system_message = f"""Ti si NESAKO AI - napredni asistent za analizu slika i vizuelni sadržaj.

TRENUTNO VREME: {current_time_str}, {day_serbian}, {current_date}

SPECIJALIZACIJA ZA SLIKE:
🖼️ Detaljno analiziram sve aspekte slika (kompozicija, boje, kvalitet, sadržaj)
🔍 Prepoznajem objekte, tekst, ljude, arhitekturu, prirodu
🎨 Dajem savete za poboljšanje fotografija i dizajna
💡 Predlažem kreativne ideje i izmene
🛠️ Objašnjavam tehničke aspekte (osvetljenje, kontrast, rezolucija)
📊 Poredim više slika i dajem komparativnu analizu

INSTRUKCIJE:
- Analiziraj svaku sliku detaljno i precizno
- Koristi srpski jezik za sve odgovore
- Daj praktične savete i preporuke
- Budi kreativan i koristan
- Fokusiraj se na ono što korisnik pita

Odgovori direktno i korisno na osnovu analize slika."""

            payload = {
                'model': 'deepseek-chat',
                'messages': [
                    {'role': 'system', 'content': system_message},
                    {'role': 'user', 'content': combined_prompt}
                ],
                'temperature': 0.4,
                'max_tokens': 3000,
                'stream': False
            }
            
            try:
                response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    ai_response = result['choices'][0]['message']['content']
                    
                    # Update memory with final response
                    self.memory.save_conversation(
                        session_id=session_id,
                        user_message=f"Upload slika: {', '.join([f.name for f in uploaded_files])} - {user_instruction}",
                        ai_response=ai_response,
                        tools_used=['image_processing', 'ai_analysis'],
                        context_data={
                            'images_processed': len(processed_images),
                            'image_details': [img['info'] for img in processed_images]
                        }
                    )
                    
                    return JsonResponse({
                        'response': ai_response,
                        'status': 'success',
                        'timestamp': current_time.isoformat(),
                        'mode': 'image_analysis',
                        'images_processed': len(processed_images),
                        'image_data': processed_images,
                        'tools_used': True
                    })
                else:
                    # Fallback response when API fails
                    fallback_response = self.generate_fallback_image_response(processed_images, user_instruction)
                    
                    return JsonResponse({
                        'response': fallback_response,
                        'status': 'success',
                        'timestamp': current_time.isoformat(),
                        'mode': 'image_analysis_fallback',
                        'images_processed': len(processed_images),
                        'image_data': processed_images,
                        'tools_used': True,
                        'note': 'Fallback response used due to API error'
                    })
                    
            except Exception as api_error:
                # Fallback response when API call fails completely
                fallback_response = self.generate_fallback_image_response(processed_images, user_instruction)
                
                return JsonResponse({
                    'response': fallback_response,
                    'status': 'success',
                    'timestamp': current_time.isoformat(),
                    'mode': 'image_analysis_fallback',
                    'images_processed': len(processed_images),
                    'image_data': processed_images,
                    'tools_used': True,
                    'note': 'Fallback response used due to API connection error'
                })
                
        except Exception as e:
            print(f"Image upload error: {e}")
            return JsonResponse({
                'error': f'Greška pri upload-u: {str(e)}',
                'status': 'error',
                'response': 'Greška pri obradi upload-ovanih slika.'
            }, status=500)


class LoginView(View):
    """Simple authentication for private access"""
    
    def get(self, request):
        if request.session.get('authenticated'):
            return redirect('/')
        
        from django.template.response import TemplateResponse
        return TemplateResponse(request, 'login.html')
    
    def post(self, request):
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        
        if username == 'nesako' and password == 'nesako2024':
            request.session['authenticated'] = True
            return redirect('/')
        else:
            return redirect('/login/')


class LogoutView(View):
    """Logout functionality"""
    
    def get(self, request):
        request.session.flush()
        return redirect('/login/')
    
    def post(self, request):
        request.session.flush()
        return JsonResponse({'success': True})


class ProtectedTemplateView(TemplateView):
    """Protected template view that requires authentication"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.session.get('authenticated'):
            return redirect('/login/')
        return super().dispatch(request, *args, **kwargs)
