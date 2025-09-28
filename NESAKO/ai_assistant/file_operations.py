import os
import shutil
import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime

class FileOperationsManager:
    """Napredni sistem za file operacije direktno na desktopu"""
    
    def __init__(self):
        self.desktop_path = Path.home() / "Desktop"
        self.operations_log = []
        self.allowed_extensions = {
            'text': ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml'],
            'office': ['.docx', '.xlsx', '.pptx', '.pdf'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'],
            'data': ['.csv', '.json', '.xml', '.yaml', '.sql']
        }
    
    def create_folder(self, folder_name: str, parent_path: str = None) -> Dict:
        """Kreira folder na desktopu ili u specifičnoj lokaciji"""
        try:
            if parent_path:
                base_path = Path(parent_path)
            else:
                base_path = self.desktop_path
            
            folder_path = base_path / folder_name
            
            if folder_path.exists():
                return {
                    'success': False,
                    'message': f'Folder "{folder_name}" već postoji',
                    'path': str(folder_path)
                }
            
            folder_path.mkdir(parents=True, exist_ok=False)
            
            self.log_operation('create_folder', {
                'folder_name': folder_name,
                'path': str(folder_path),
                'parent': str(base_path)
            })
            
            return {
                'success': True,
                'message': f'Folder "{folder_name}" uspešno kreiran',
                'path': str(folder_path)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Greška pri kreiranju foldera: {str(e)}',
                'error': str(e)
            }
    
    def create_file(self, filename: str, content: str = "", folder_path: str = None) -> Dict:
        """Kreira fajl sa sadržajem"""
        try:
            if folder_path:
                base_path = Path(folder_path)
            else:
                base_path = self.desktop_path
            
            file_path = base_path / filename
            
            if file_path.exists():
                return {
                    'success': False,
                    'message': f'Fajl "{filename}" već postoji',
                    'path': str(file_path)
                }
            
            # Kreiraj parent direktorijume ako ne postoje
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Kreiraj fajl sa sadržajem
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.log_operation('create_file', {
                'filename': filename,
                'path': str(file_path),
                'size': len(content),
                'content_preview': content[:100] if content else 'Empty file'
            })
            
            return {
                'success': True,
                'message': f'Fajl "{filename}" uspešno kreiran',
                'path': str(file_path),
                'size': len(content)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Greška pri kreiranju fajla: {str(e)}',
                'error': str(e)
            }
    
    def modify_file(self, file_path: str, new_content: str, backup: bool = True) -> Dict:
        """Modifikuje postojeći fajl"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {
                    'success': False,
                    'message': f'Fajl "{file_path}" ne postoji'
                }
            
            # Kreiraj backup ako je potrebno
            if backup:
                backup_path = file_path.with_suffix(f'{file_path.suffix}.backup')
                shutil.copy2(file_path, backup_path)
            
            # Modifikuj fajl
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            self.log_operation('modify_file', {
                'file_path': str(file_path),
                'backup_created': backup,
                'new_size': len(new_content)
            })
            
            return {
                'success': True,
                'message': f'Fajl "{file_path.name}" uspešno modifikovan',
                'path': str(file_path),
                'backup_created': backup
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Greška pri modifikaciji fajla: {str(e)}',
                'error': str(e)
            }
    
    def copy_file(self, source_path: str, destination_path: str) -> Dict:
        """Kopira fajl"""
        try:
            source = Path(source_path)
            destination = Path(destination_path)
            
            if not source.exists():
                return {
                    'success': False,
                    'message': f'Source fajl "{source}" ne postoji'
                }
            
            # Kreiraj destination direktorijum ako ne postoji
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.copy2(source, destination)
            
            self.log_operation('copy_file', {
                'source': str(source),
                'destination': str(destination),
                'size': source.stat().st_size
            })
            
            return {
                'success': True,
                'message': f'Fajl kopiran sa "{source.name}" na "{destination}"',
                'source': str(source),
                'destination': str(destination)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Greška pri kopiranju fajla: {str(e)}',
                'error': str(e)
            }
    
    def move_file(self, source_path: str, destination_path: str) -> Dict:
        """Premešta fajl"""
        try:
            source = Path(source_path)
            destination = Path(destination_path)
            
            if not source.exists():
                return {
                    'success': False,
                    'message': f'Source fajl "{source}" ne postoji'
                }
            
            # Kreiraj destination direktorijum ako ne postoji
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(source), str(destination))
            
            self.log_operation('move_file', {
                'source': str(source),
                'destination': str(destination)
            })
            
            return {
                'success': True,
                'message': f'Fajl premešten sa "{source}" na "{destination}"',
                'source': str(source),
                'destination': str(destination)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Greška pri premeštanju fajla: {str(e)}',
                'error': str(e)
            }
    
    def delete_file(self, file_path: str, to_recycle_bin: bool = True) -> Dict:
        """Briše fajl (opciono u recycle bin)"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {
                    'success': False,
                    'message': f'Fajl "{file_path}" ne postoji'
                }
            
            if to_recycle_bin:
                try:
                    # Pokušaj sa send2trash bibliotekom
                    import send2trash
                    send2trash.send2trash(str(file_path))
                    delete_method = 'recycle_bin'
                except ImportError:
                    # Fallback na obično brisanje
                    file_path.unlink()
                    delete_method = 'permanent'
            else:
                file_path.unlink()
                delete_method = 'permanent'
            
            self.log_operation('delete_file', {
                'file_path': str(file_path),
                'delete_method': delete_method
            })
            
            return {
                'success': True,
                'message': f'Fajl "{file_path.name}" uspešno obrisan ({delete_method})',
                'path': str(file_path),
                'method': delete_method
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Greška pri brisanju fajla: {str(e)}',
                'error': str(e)
            }
    
    def list_desktop_contents(self) -> Dict:
        """Lista sadržaj desktopa"""
        try:
            contents = {
                'folders': [],
                'files': [],
                'total_items': 0
            }
            
            for item in self.desktop_path.iterdir():
                if item.is_dir():
                    contents['folders'].append({
                        'name': item.name,
                        'path': str(item),
                        'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    })
                else:
                    contents['files'].append({
                        'name': item.name,
                        'path': str(item),
                        'size': item.stat().st_size,
                        'extension': item.suffix,
                        'modified': datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                    })
            
            contents['total_items'] = len(contents['folders']) + len(contents['files'])
            
            return {
                'success': True,
                'contents': contents,
                'desktop_path': str(self.desktop_path)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Greška pri listovanju desktopa: {str(e)}',
                'error': str(e)
            }
    
    def create_project_structure(self, project_name: str, project_type: str = 'web') -> Dict:
        """Kreira kompletnu strukturu projekta"""
        try:
            project_path = self.desktop_path / project_name
            
            if project_path.exists():
                return {
                    'success': False,
                    'message': f'Projekat "{project_name}" već postoji'
                }
            
            # Kreiraj osnovnu strukturu
            project_path.mkdir()
            
            structures = {
                'web': {
                    'folders': ['src', 'public', 'assets', 'css', 'js'],
                    'files': {
                        'index.html': '<!DOCTYPE html>\n<html>\n<head>\n    <title>Project</title>\n</head>\n<body>\n    <h1>Hello World</h1>\n</body>\n</html>',
                        'README.md': f'# {project_name}\n\nWeb projekat kreiran od strane NESAKO AI',
                        'package.json': json.dumps({
                            'name': project_name.lower(),
                            'version': '1.0.0',
                            'description': 'NESAKO AI generated project'
                        }, indent=2)
                    }
                },
                'python': {
                    'folders': ['src', 'tests', 'docs'],
                    'files': {
                        'main.py': '#!/usr/bin/env python3\n\ndef main():\n    print("Hello World")\n\nif __name__ == "__main__":\n    main()',
                        'requirements.txt': 'requests>=2.25.0\n',
                        'README.md': f'# {project_name}\n\nPython projekat kreiran od strane NESAKO AI'
                    }
                }
            }
            
            structure = structures.get(project_type, structures['web'])
            
            # Kreiraj foldere
            for folder in structure['folders']:
                (project_path / folder).mkdir()
            
            # Kreiraj fajlove
            for filename, content in structure['files'].items():
                with open(project_path / filename, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            self.log_operation('create_project', {
                'project_name': project_name,
                'project_type': project_type,
                'path': str(project_path),
                'folders_created': len(structure['folders']),
                'files_created': len(structure['files'])
            })
            
            return {
                'success': True,
                'message': f'Projekat "{project_name}" ({project_type}) uspešno kreiran',
                'path': str(project_path),
                'structure': structure
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Greška pri kreiranju projekta: {str(e)}',
                'error': str(e)
            }
    
    def detect_file_operation_request(self, user_input: str) -> Dict:
        """Detektuje zahtev za file operacije"""
        input_lower = user_input.lower()
        
        operations = {
            'create_folder': [
                'napravi folder', 'kreiraj direktorijum', 'mkdir',
                'nova fascikla', 'create folder', 'new directory'
            ],
            'create_file': [
                'napravi fajl', 'kreiraj fajl', 'create file',
                'novi fajl', 'new file', 'touch'
            ],
            'create_project': [
                'napravi projekat', 'kreiraj projekat', 'create project',
                'novi projekat', 'new project', 'setup project'
            ],
            'list_desktop': [
                'prikaži desktop', 'lista desktop', 'show desktop',
                'desktop contents', 'šta je na desktopu'
            ],
            'copy_file': [
                'kopiraj fajl', 'copy file', 'duplicate file'
            ],
            'move_file': [
                'premesti fajl', 'move file', 'relocate file'
            ],
            'delete_file': [
                'obriši fajl', 'delete file', 'remove file'
            ],
            'github_sync': [
                'prebaci na github', 'github sync', 'sačuvaj na github',
                'push na github', 'commit i push', 'git commit i push'
            ]
        }
        
        detected = []
        
        for operation, keywords in operations.items():
            if any(keyword in input_lower for keyword in keywords):
                detected.append({
                    'operation': operation,
                    'confidence': 0.8
                })
        
        return {
            'detected_operations': detected,
            'has_file_operation': len(detected) > 0
        }
    
    def log_operation(self, operation_type: str, details: Dict):
        """Loguje file operaciju"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation_type,
            'details': details
        }
        self.operations_log.append(log_entry)
        
        # Čuvaj samo poslednih 100 operacija
        if len(self.operations_log) > 100:
            self.operations_log = self.operations_log[-100:]
    
    def get_operations_log(self) -> List[Dict]:
        """Vraća log file operacija"""
        return self.operations_log
