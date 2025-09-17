import os
import json
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class CommandGenerator:
    """Napredni generator komandi za Git Bash, CMD i PowerShell"""
    
    def __init__(self):
        self.command_templates = {
            'git': {
                'init': 'git init',
                'clone': 'git clone {repo_url}',
                'add': 'git add {files}',
                'commit': 'git commit -m "{message}"',
                'push': 'git push {remote} {branch}',
                'pull': 'git pull {remote} {branch}',
                'status': 'git status',
                'log': 'git log --oneline -n {count}',
                'branch': 'git branch {branch_name}',
                'checkout': 'git checkout {branch_name}',
                'merge': 'git merge {branch_name}',
                'reset': 'git reset --{type} {commit}',
                'stash': 'git stash {action}',
                'remote': 'git remote add {name} {url}',
                'tag': 'git tag {tag_name}',
                'diff': 'git diff {file}',
                'rollback': 'git reset --hard HEAD~{steps}'
            },
            'npm': {
                'init': 'npm init -y',
                'install': 'npm install {package}',
                'install_dev': 'npm install --save-dev {package}',
                'install_global': 'npm install -g {package}',
                'uninstall': 'npm uninstall {package}',
                'update': 'npm update {package}',
                'run': 'npm run {script}',
                'start': 'npm start',
                'test': 'npm test',
                'build': 'npm run build',
                'audit': 'npm audit fix',
                'list': 'npm list --depth=0'
            },
            'python': {
                'install': 'pip install {package}',
                'install_requirements': 'pip install -r requirements.txt',
                'freeze': 'pip freeze > requirements.txt',
                'uninstall': 'pip uninstall {package}',
                'upgrade': 'pip install --upgrade {package}',
                'venv_create': 'python -m venv {env_name}',
                'venv_activate_win': '{env_name}\\Scripts\\activate',
                'venv_activate_bash': 'source {env_name}/bin/activate',
                'run': 'python {file}',
                'django_start': 'python manage.py runserver {port}',
                'django_migrate': 'python manage.py migrate',
                'django_makemigrations': 'python manage.py makemigrations'
            },
            'docker': {
                'build': 'docker build -t {image_name} .',
                'run': 'docker run -d -p {host_port}:{container_port} {image_name}',
                'stop': 'docker stop {container_id}',
                'remove': 'docker rm {container_id}',
                'images': 'docker images',
                'ps': 'docker ps -a',
                'logs': 'docker logs {container_id}',
                'exec': 'docker exec -it {container_id} /bin/bash',
                'compose_up': 'docker-compose up -d',
                'compose_down': 'docker-compose down'
            },
            'file_operations': {
                'create_dir': {
                    'cmd': 'mkdir "{path}"',
                    'powershell': 'New-Item -ItemType Directory -Path "{path}"',
                    'bash': 'mkdir -p "{path}"'
                },
                'copy_file': {
                    'cmd': 'copy "{source}" "{destination}"',
                    'powershell': 'Copy-Item "{source}" "{destination}"',
                    'bash': 'cp "{source}" "{destination}"'
                },
                'move_file': {
                    'cmd': 'move "{source}" "{destination}"',
                    'powershell': 'Move-Item "{source}" "{destination}"',
                    'bash': 'mv "{source}" "{destination}"'
                },
                'delete_file': {
                    'cmd': 'del "{path}"',
                    'powershell': 'Remove-Item "{path}"',
                    'bash': 'rm "{path}"'
                },
                'list_files': {
                    'cmd': 'dir "{path}"',
                    'powershell': 'Get-ChildItem "{path}"',
                    'bash': 'ls -la "{path}"'
                }
            }
        }
        
        self.desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    
    def detect_command_intent(self, user_input: str) -> Dict:
        """Detektuje nameru korisnika za komande"""
        input_lower = user_input.lower()
        
        # Git komande
        git_patterns = {
            'clone': ['clone', 'kloniraj', 'preuzmi repo'],
            'init': ['git init', 'inicijalizuj git', 'napravi git'],
            'commit': ['commit', 'commituj', 'sačuvaj izmene'],
            'push': ['push', 'pošalji', 'upload'],
            'pull': ['pull', 'povuci', 'ažuriraj'],
            'status': ['status', 'stanje', 'šta je novo'],
            'add': ['add', 'dodaj', 'stage'],
            'rollback': ['rollback', 'vrati', 'poništi', 'reset']
        }
        
        # NPM/Node komande
        npm_patterns = {
            'install': ['npm install', 'instaliraj paket', 'dodaj dependency'],
            'start': ['npm start', 'pokreni app', 'startuj'],
            'build': ['npm build', 'build app', 'kompajliraj'],
            'init': ['npm init', 'inicijalizuj npm', 'napravi package.json']
        }
        
        # Python komande
        python_patterns = {
            'install': ['pip install', 'instaliraj python paket'],
            'run': ['python run', 'pokreni python', 'izvršava python'],
            'venv': ['virtual environment', 'venv', 'virtuelno okruženje'],
            'django': ['django', 'runserver', 'migrate']
        }
        
        # File operations
        file_patterns = {
            'create_folder': ['napravi folder', 'kreiraj direktorijum', 'mkdir'],
            'copy': ['kopiraj', 'copy', 'dupliraj'],
            'move': ['premesti', 'move', 'mv'],
            'delete': ['obriši', 'delete', 'ukloni']
        }
        
        detected_commands = []
        
        # Proveri Git komande
        for command, patterns in git_patterns.items():
            if any(pattern in input_lower for pattern in patterns):
                detected_commands.append({
                    'type': 'git',
                    'command': command,
                    'confidence': 0.8
                })
        
        # Proveri NPM komande
        for command, patterns in npm_patterns.items():
            if any(pattern in input_lower for pattern in patterns):
                detected_commands.append({
                    'type': 'npm',
                    'command': command,
                    'confidence': 0.8
                })
        
        # Proveri Python komande
        for command, patterns in python_patterns.items():
            if any(pattern in input_lower for pattern in patterns):
                detected_commands.append({
                    'type': 'python',
                    'command': command,
                    'confidence': 0.8
                })
        
        # Proveri File operations
        for command, patterns in file_patterns.items():
            if any(pattern in input_lower for pattern in patterns):
                detected_commands.append({
                    'type': 'file_operation',
                    'command': command,
                    'confidence': 0.7
                })
        
        return {
            'detected_commands': detected_commands,
            'has_commands': len(detected_commands) > 0,
            'primary_type': detected_commands[0]['type'] if detected_commands else None
        }
    
    def extract_parameters(self, user_input: str, command_type: str, command: str) -> Dict:
        """Izvlači parametre iz korisničkog unosa"""
        params = {}
        input_lower = user_input.lower()
        
        # Git parametri
        if command_type == 'git':
            if command == 'clone':
                # Traži GitHub/GitLab URL
                url_pattern = r'https?://(?:github\.com|gitlab\.com)/[\w\-\.]+/[\w\-\.]+'
                match = re.search(url_pattern, user_input)
                if match:
                    params['repo_url'] = match.group()
                
            elif command == 'commit':
                # Traži commit message
                message_patterns = [
                    r'"([^"]+)"',  # Tekst u navodnicima
                    r"'([^']+)'",  # Tekst u apostrofima
                ]
                for pattern in message_patterns:
                    match = re.search(pattern, user_input)
                    if match:
                        params['message'] = match.group(1)
                        break
                if 'message' not in params:
                    params['message'] = 'Update code'
            
            elif command == 'push' or command == 'pull':
                params['remote'] = 'origin'
                params['branch'] = 'main'
                # Traži branch name
                branch_pattern = r'(?:branch|grana)\s+(\w+)'
                match = re.search(branch_pattern, input_lower)
                if match:
                    params['branch'] = match.group(1)
            
            elif command == 'rollback':
                # Traži broj koraka
                steps_pattern = r'(\d+)\s*(?:korak|step|commit)'
                match = re.search(steps_pattern, input_lower)
                if match:
                    params['steps'] = match.group(1)
                else:
                    params['steps'] = '1'
        
        # NPM parametri
        elif command_type == 'npm':
            if command in ['install', 'uninstall', 'update']:
                # Traži package name
                package_patterns = [
                    r'(?:package|paket)\s+(\S+)',
                    r'(?:install|instaliraj)\s+(\S+)',
                    r'npm\s+install\s+(\S+)'
                ]
                for pattern in package_patterns:
                    match = re.search(pattern, input_lower)
                    if match:
                        params['package'] = match.group(1)
                        break
        
        # Python parametri
        elif command_type == 'python':
            if command == 'install':
                # Traži package name
                package_pattern = r'(?:pip install|instaliraj)\s+(\S+)'
                match = re.search(package_pattern, input_lower)
                if match:
                    params['package'] = match.group(1)
            
            elif command == 'venv':
                # Traži env name
                env_pattern = r'(?:venv|environment)\s+(\w+)'
                match = re.search(env_pattern, input_lower)
                if match:
                    params['env_name'] = match.group(1)
                else:
                    params['env_name'] = 'venv'
            
            elif command == 'run':
                # Traži file name
                file_pattern = r'(?:run|pokreni)\s+(\S+\.py)'
                match = re.search(file_pattern, user_input)
                if match:
                    params['file'] = match.group(1)
        
        # File operation parametri
        elif command_type == 'file_operation':
            if command == 'create_folder':
                # Traži folder name/path
                folder_patterns = [
                    r'(?:folder|direktorijum)\s+"([^"]+)"',
                    r'(?:folder|direktorijum)\s+(\S+)',
                    r'mkdir\s+"([^"]+)"',
                    r'mkdir\s+(\S+)'
                ]
                for pattern in folder_patterns:
                    match = re.search(pattern, user_input)
                    if match:
                        folder_name = match.group(1)
                        # Ako je relativna putanja, dodaj desktop
                        if not os.path.isabs(folder_name):
                            params['path'] = os.path.join(self.desktop_path, folder_name)
                        else:
                            params['path'] = folder_name
                        break
        
        return params
    
    def generate_commands(self, user_input: str) -> Dict:
        """Generiše komande na osnovu korisničkog unosa"""
        intent = self.detect_command_intent(user_input)
        
        if not intent['has_commands']:
            return {
                'success': False,
                'message': 'Nisam detektovao komande u vašem zahtevu.'
            }
        
        generated_commands = []
        
        for detected in intent['detected_commands']:
            command_type = detected['type']
            command = detected['command']
            
            # Izvuci parametre
            params = self.extract_parameters(user_input, command_type, command)
            
            # Generiši komande za različite shell-ove
            if command_type == 'file_operation':
                # File operations imaju različite komande za različite shell-ove
                if command in self.command_templates['file_operations']:
                    templates = self.command_templates['file_operations'][command]
                    
                    cmd_commands = []
                    for shell, template in templates.items():
                        try:
                            formatted_command = template.format(**params)
                            cmd_commands.append({
                                'shell': shell,
                                'command': formatted_command,
                                'description': f'{command} - {shell}'
                            })
                        except KeyError as e:
                            # Ako nema dovoljno parametara, dodaj placeholder
                            missing_param = str(e).strip("'")
                            params[missing_param] = f'<{missing_param}>'
                            formatted_command = template.format(**params)
                            cmd_commands.append({
                                'shell': shell,
                                'command': formatted_command,
                                'description': f'{command} - {shell} (potrebno dopuniti {missing_param})'
                            })
                    
                    generated_commands.append({
                        'type': command_type,
                        'command': command,
                        'commands': cmd_commands,
                        'parameters': params
                    })
            else:
                # Ostale komande
                if command_type in self.command_templates and command in self.command_templates[command_type]:
                    template = self.command_templates[command_type][command]
                    
                    try:
                        formatted_command = template.format(**params)
                        description = f'{command_type.upper()} - {command}'
                        
                        generated_commands.append({
                            'type': command_type,
                            'command': command,
                            'commands': [{
                                'shell': 'all',
                                'command': formatted_command,
                                'description': description
                            }],
                            'parameters': params
                        })
                    except KeyError as e:
                        # Ako nema dovoljno parametara
                        missing_param = str(e).strip("'")
                        params[missing_param] = f'<{missing_param}>'
                        formatted_command = template.format(**params)
                        
                        generated_commands.append({
                            'type': command_type,
                            'command': command,
                            'commands': [{
                                'shell': 'all',
                                'command': formatted_command,
                                'description': f'{command_type.upper()} - {command} (potrebno dopuniti {missing_param})'
                            }],
                            'parameters': params
                        })
        
        return {
            'success': True,
            'commands': generated_commands,
            'total_commands': len(generated_commands),
            'detected_intent': intent
        }
    
    def format_commands_for_display(self, commands_result: Dict) -> str:
        """Formatira komande za prikaz korisniku"""
        if not commands_result['success']:
            return commands_result['message']
        
        output = []
        output.append("🔧 **GENERIRANE KOMANDE - COPY/PASTE SPREMNE:**\n")
        
        for i, cmd_group in enumerate(commands_result['commands'], 1):
            output.append(f"**{i}. {cmd_group['type'].upper()} - {cmd_group['command']}**")
            
            for cmd in cmd_group['commands']:
                shell_icon = {
                    'cmd': '🖥️ CMD:',
                    'powershell': '💙 PowerShell:',
                    'bash': '🐧 Git Bash:',
                    'all': '⚡ Komanda:'
                }.get(cmd['shell'], '📝')
                
                output.append(f"{shell_icon}")
                output.append(f"```")
                output.append(cmd['command'])
                output.append(f"```")
                
                if cmd['description']:
                    output.append(f"*{cmd['description']}*")
                output.append("")
            
            # Prikaži parametre ako postoje
            if cmd_group['parameters']:
                output.append("**Parametri:**")
                for param, value in cmd_group['parameters'].items():
                    output.append(f"- {param}: `{value}`")
                output.append("")
        
        output.append("💡 **NAPOMENE:**")
        output.append("- Komande su spremne za copy/paste")
        output.append("- Zamenite `<parametar>` sa stvarnim vrednostima")
        output.append("- Proverite putanje pre izvršavanja")
        output.append("- Za Git komande, budite u Git repozitorijumu")
        
        return "\n".join(output)
    
    def create_batch_file(self, commands: List[str], filename: str = None) -> str:
        """Kreira .bat fajl sa komandama"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"nesako_commands_{timestamp}.bat"
        
        batch_path = os.path.join(self.desktop_path, filename)
        
        try:
            with open(batch_path, 'w', encoding='utf-8') as f:
                f.write("@echo off\n")
                f.write("echo NESAKO AI - Generated Commands\n")
                f.write("echo ================================\n")
                f.write("pause\n\n")
                
                for i, command in enumerate(commands, 1):
                    f.write(f"echo Executing command {i}: {command}\n")
                    f.write(f"{command}\n")
                    f.write("if %errorlevel% neq 0 (\n")
                    f.write(f"    echo Error executing command {i}\n")
                    f.write("    pause\n")
                    f.write(")\n\n")
                
                f.write("echo All commands completed!\n")
                f.write("pause\n")
            
            return f"✅ Batch fajl kreiran: {batch_path}"
            
        except Exception as e:
            return f"❌ Greška pri kreiranju batch fajla: {str(e)}"
    
    def get_command_help(self, command_type: str = None) -> str:
        """Vraća help za komande"""
        if not command_type:
            return """🔧 **DOSTUPNI TIPOVI KOMANDI:**

**Git komande:**
- clone, init, add, commit, push, pull, status, rollback

**NPM komande:**
- init, install, start, build, test, run

**Python komande:**
- install, run, venv (virtual environment), django

**File operacije:**
- create_folder, copy, move, delete, list

**Primeri korišćenja:**
- "kloniraj https://github.com/user/repo"
- "commituj sa porukom 'fix bug'"
- "instaliraj react paket"
- "napravi folder TestProject na desktopu"
- "pokreni python app.py"

Jednostavno opišite šta želite da uradite, a ja ću generisati odgovarajuće komande!"""
        
        if command_type in self.command_templates:
            commands = list(self.command_templates[command_type].keys())
            return f"**{command_type.upper()} komande:**\n" + "\n".join([f"- {cmd}" for cmd in commands])
        
        return f"Nepoznat tip komande: {command_type}"
