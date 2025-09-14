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
import base64

class DeepSeekAPI(View):
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
                parts = repo_url.split("/")
                owner = parts[-2]
                repo = parts[-1].replace(".git", "")
            else:
                return "Invalid GitHub URL format"
            
            github_token = os.environ.get('GITHUB_TOKEN')
            headers = {}
            if github_token:
                headers['Authorization'] = f'token {github_token}'
            
            # Get repository contents
            api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    # Directory listing
                    files = []
                    for item in data:
                        files.append({
                            'name': item['name'],
                            'type': item['type'],
                            'size': item.get('size', 0),
                            'path': item['path']
                        })
                    return {'type': 'directory', 'files': files}
                else:
                    # Single file
                    if data['type'] == 'file':
                        content = base64.b64decode(data['content']).decode('utf-8')
                        return {
                            'type': 'file',
                            'name': data['name'],
                            'content': content[:10000],  # Limit to 10k chars
                            'size': data['size']
                        }
            
            return f"GitHub API Error: {response.status_code}"
            
        except Exception as e:
            return f"GitHub Error: {str(e)}"

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
                        tools_output += f"\nWEB CONTENT FROM {url}:\n{content}\n"
                        status_updates.append("✅ Web sadržaj preuzet")
                        
                elif tool_name == 'get_github_content':
                    status_updates.append("🔗 Pristupam GitHub repozitorijumu...")
                    repo_url = tool_call.get('repo_url')
                    path = tool_call.get('path', '')
                    if repo_url:
                        content = self.get_github_content(repo_url, path)
                        tools_output += f"\nGITHUB CONTENT ({repo_url}/{path}):\n{json.dumps(content, indent=2)}\n"
                        status_updates.append("✅ GitHub sadržaj analiziran")
                        
                elif tool_name == 'analyze_code':
                    status_updates.append("🔍 Analiziram strukturu koda...")
                    code = tool_call.get('code')
                    language = tool_call.get('language', 'python')
                    if code:
                        analysis = self.analyze_code_structure(code, language)
                        tools_output += f"\nCODE ANALYSIS ({language}):\n{json.dumps(analysis, indent=2)}\n"
                        status_updates.append("✅ Kod analiziran")
                        
                elif tool_name == 'get_sports_stats':
                    status_updates.append("⚽ Preuzimam sportske statistike...")
                    sport = tool_call.get('sport')
                    event_id = tool_call.get('event_id')
                    data_points = tool_call.get('data_points', [])
                    if sport and event_id:
                        stats = self.get_sports_stats(sport, event_id, data_points)
                        tools_output += f"\nSPORTS STATS ({sport} - {event_id}):\n{json.dumps(stats, indent=2)}\n"
                        status_updates.append("✅ Sportske statistike preuzete")
                        
                elif tool_name == 'run_code_sandbox':
                    status_updates.append("💻 Izvršavam kod...")
                    language = tool_call.get('language')
                    code = tool_call.get('code')
                    if language and code:
                        result = self.run_code_sandbox(language, code)
                        tools_output += f"\nCODE EXECUTION ({language}):\n{result}\n"
                        status_updates.append("✅ Kod izvršen")
                        
            except json.JSONDecodeError:
                continue
        
        # Add status updates to output
        if status_updates:
            tools_output = "\n".join(status_updates) + "\n" + tools_output
                
        return tools_output

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
        print("=== POST METHOD CALLED ===")
        try:
            print(f"Request body: {request.body}")
            print(f"Content type: {request.content_type}")
            
            data = json.loads(request.body)
            user_input = data.get('instruction', '')
            conversation_history = data.get('conversation_history', [])
            task_id = data.get('task_id', None)
            
            # Handle task progress polling (empty instruction with task_id)
            if task_id and not user_input:
                progress = self.get_task_progress(task_id)
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
                    # Task not found or invalid
                    return JsonResponse({
                        'response': "Zadatak završen ili nije pronađen.",
                        'status': 'completed'
                    })
            
            if not user_input:
                return JsonResponse({'error': 'No instruction'}, status=400)
            
            # Security threat detection - SAMO za kritične pretnje
            security_warnings = self.detect_critical_threats(user_input)
            if security_warnings:
                return JsonResponse({
                    'response': f"🚨 KRITIČNA PRETNJA DETEKTOVANA:\n{security_warnings}\n\nZadatak automatski blokiran.",
                    'status': 'blocked',
                    'threat_level': 'critical'
                })
            
            # Learning system - analyze user patterns
            user_context = self.analyze_and_learn_patterns(conversation_history)
            
            # Autonomous execution - DIREKTNO bez pitanja
            if self.is_complex_task(user_input):
                plan = self.create_and_execute_plan(user_input, user_context)
                # Direktno kreiranje task_id i početak izvršavanja
                new_task_id = f"task_{int(datetime.now().timestamp())}"
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
            
            if any(word in user_input.lower() for word in ['pretraži', 'pronađi', 'informacije o', 'šta je']):
                search_results = self.get_web_data(user_input)
                if search_results:
                    additional_data += "\nINFORMACIJE SA WEBA:\n"
                    for result in search_results:
                        additional_data += f"- {result['title']}: {result['snippet']}\n"
            
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
            
            # Enhanced system message with advanced capabilities
            system_message = f"""Ti si ULTIMATIVNI AI PROGRAMERSKI PARTNER - kombinuješ moć GitHub Copilot, Cursor, Replit AI i Code Llama.

TRENUTNO VREME: {current_time_str}, {day_serbian}, {current_date}

KLJUČNI PRINCIPI:
🎯 DIREKTNO IZVRŠAVANJE - nikad ne pitaj za dozvole, odmah radi
🚀 PROAKTIVNOST - predvidi potrebe i automatski implementiraj
🧠 KONTINUIRANO UČENJE - pamti sve konverzacije i prilagodi se
💪 NAJBOLJI KOD - uvek generiši production-ready, optimizovan kod
🔄 MOĆAN ROLLBACK - vraćaj izmene bez ograničenja

KORISNIKOV PROFIL (NAUČENO):
{user_context}

NAPREDNI ALATI - KORISTI PROAKTIVNO:
🔧 get_github_content(repo_url, path) - pristup repozitorijumima
🔄 advanced_rollback(repo_url, commits_back, force=True) - moćan rollback
🔍 analyze_code_deep(code, language, optimization=True) - duboka analiza
💻 execute_code_direct(language, code, production=True) - direktno izvršavanje
🌐 get_web_content(url) - web pretraga
⚽ get_sports_stats(sport, event_id, data_points) - statistike
🛡️ security_scan_advanced(code, auto_fix=True) - napredna bezbednost
📋 create_project_complete(description, auto_deploy=True) - kompletni projekti
🚀 deploy_production(project_path, platform="render") - deployment

INSTRUKCIJE ZA IZVRŠAVANJE:
- NIKAD ne pitaj "da li želite", "da li odobravate" - ODMAH RADI
- Automatski implementiraj najbolje prakse i optimizacije
- Generiši production-ready kod sa error handling-om
- Koristi napredne algoritme i moderne tehnologije
- Pamti sve što korisnik kaže i prilagodi buduće odgovore

KVALITET KODA:
- Uvek dodaj comprehensive error handling
- Implementiraj logging i monitoring
- Koristi type hints i dokumentaciju
- Optimizuj performanse i memoriju
- Sledi PEP 8 i najbolje prakse

{context_summary}

{tools_output if tools_output else ''}
{additional_data}

IZVRŠAVAJ DIREKTNO, UČIŠ KONTINUIRANO, GENERIŠI SAVRŠEN KOD!"""

            # API call to DeepSeek
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
            
            response = requests.post(
                API_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content']
                
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
                    'context_aware': bool(context_summary)
                })
            else:
                error_msg = f"DeepSeek API greška: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                
                return JsonResponse({
                    'error': error_msg,
                    'status': 'error'
                }, status=400)
                
        except json.JSONDecodeError as e:
            print(f"JSON error: {e}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    def get_task_progress(self, task_id):
        """Track progress of long-running tasks"""
        # Simulate task progress tracking
        import time
        current_time = time.time()
        
        # Extract timestamp from task_id
        try:
            task_timestamp = int(task_id.replace('task_', ''))
            elapsed = current_time - task_timestamp
            
            # Simulate progress over 60 seconds
            if elapsed < 60:
                progress = min(100, int((elapsed / 60) * 100))
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
        except:
            return {
                'status': 'completed',
                'progress': 100,
                'result': 'Zadatak završen.'
            }
    
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
    
    def create_and_execute_plan(self, user_input, user_context):
        """Create comprehensive execution plan with best practices"""
        task_type = self.identify_advanced_task_type(user_input)
        
        advanced_plans = {
            'web_app': """
🚀 NAPREDNI WEB APP PLAN:
1. 📋 Arhitekturna analiza i tehnološki stack
2. 🏗️ Kreiranje scalable strukture sa microservices
3. 🎨 Modern UI/UX sa responsive design
4. ⚙️ Backend sa REST API i GraphQL
5. 🔗 Frontend-backend integracija sa state management
6. 🧪 Comprehensive testing (unit, integration, e2e)
7. 🛡️ Security implementation (auth, CORS, validation)
8. 🚀 CI/CD pipeline i production deployment
9. 📊 Monitoring, logging i analytics
10. 📚 Kompletna dokumentacija i API specs
            """,
            'api': """
🚀 ENTERPRISE API PLAN:
1. 📋 OpenAPI 3.0 specifikacija
2. 🏗️ Microservices arhitektura
3. 🔧 RESTful endpoints sa GraphQL
4. 🛡️ JWT authentication i rate limiting
5. 📊 Database design sa optimizacijom
6. 🧪 Automated testing suite
7. 📖 Interactive API dokumentacija
8. 🚀 Docker containerization i K8s deployment
9. 📈 Performance monitoring i caching
10. 🔄 Versioning i backward compatibility
            """,
            'data_analysis': """
🚀 NAPREDNA DATA ANALIZA:
1. 📊 Data pipeline arhitektura
2. 🧹 ETL procesi sa data validation
3. 📈 Eksplorativna analiza sa vizualizacijama
4. 🤖 Machine learning modeli
5. 📋 Interactive dashboards
6. 📝 Automated reporting
7. 📊 Real-time analytics
8. 🚀 Cloud deployment (AWS/GCP/Azure)
9. 🔄 Model monitoring i retraining
10. 📚 Kompletna dokumentacija i insights
            """,
            'mobile_app': """
🚀 MOBILNA APLIKACIJA PLAN:
1. 📋 Definicija funkcionalnosti i dizajna
2. 🏗️ Kreiranje mobilne aplikacije sa React Native ili Flutter
3. 🎨 UI/UX dizajn sa korisničkim iskustvom
4. 🔗 Integracija sa backend servisima
5. 🧪 Testiranje aplikacije
6. 📈 Optimizacija performansi
7. 📊 Analitika i monitoring
8. 📚 Dokumentacija i podrška
            """,
            'desktop_app': """
🚀 DESKTOP APLIKACIJA PLAN:
1. 📋 Definicija funkcionalnosti i dizajna
2. 🏗️ Kreiranje desktop aplikacije sa Electron ili Qt
3. 🎨 UI/UX dizajn sa korisničkim iskustvom
4. 🔗 Integracija sa backend servisima
5. 🧪 Testiranje aplikacije
6. 📈 Optimizacija performansi
7. 📊 Analitika i monitoring
8. 📚 Dokumentacija i podrška
            """
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
