import os
import re
import requests
import json
from typing import List, Optional
from .models import MemoryEntry, Conversation, LearningData

SERPAPI_API_KEY = os.getenv('SERPAPI_API_KEY', '')
DEEPSEEK_API_URL = os.getenv('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')

class NESAKOMemoryORM:
    """ORM-backed persistent memory using Django models."""

    def store_memory(self, key: str, value: str) -> None:
        entry, _ = MemoryEntry.objects.update_or_create(
            key=key,
            defaults={
                'value': value,
            }
        )

    def retrieve_memory(self, key: str) -> Optional[str]:
        try:
            return MemoryEntry.objects.get(key=key).value
        except MemoryEntry.DoesNotExist:
            return None

    def store_conversation(self, user_input: str, assistant_response: str) -> None:
        Conversation.objects.create(user_input=user_input, assistant_response=assistant_response)

    def learn_pattern(self, pattern: str, response: str) -> None:
        obj, created = LearningData.objects.get_or_create(pattern=pattern, defaults={'response': response, 'usage_count': 1})
        if not created:
            obj.response = response
            obj.usage_count = obj.usage_count + 1
            obj.save(update_fields=['response', 'usage_count'])

    def get_learned_response(self, user_input: str) -> Optional[str]:
        for ld in LearningData.objects.all():
            if re.search(ld.pattern, user_input, re.IGNORECASE):
                ld.usage_count = ld.usage_count + 1
                ld.save(update_fields=['usage_count'])
                return ld.response
        return None

class NESAKOSearch:
    def __init__(self, api_key: str = SERPAPI_API_KEY):
        self.api_key = api_key or ''

    def search_web(self, query: str) -> List[str]:
        if not self.api_key:
            return []
        try:
            params = {
                'q': query,
                'api_key': self.api_key,
                'engine': 'google'
            }
            r = requests.get('https://serpapi.com/search', params=params, timeout=12)
            data = r.json() if r.ok else {}
            if 'organic_results' in data:
                return [item.get('snippet', '') for item in data.get('organic_results', [])[:3] if item.get('snippet')]
            return []
        except Exception:
            return []

class NESAKOChatbot:
    def __init__(self):
        self.memory = NESAKOMemoryORM()
        self.search = NESAKOSearch()
        # Sistem poruka sa strogim pravilima (naglasak na sportskim pitanjima)
        self.system_prompt = (
            "TI SI NESAKO - PREVIŠE JE VAŽNO DA NE LAŽEŠ!\n\n"
            "PRAVILA:\n"
            "1. ZA SVA SPORTSKA PITANJA MORAŠ KORISTITI WEB PRETRAGU\n"
            "2. NIKAD NE IZMIŠLJAJ REZULTATE, DATUME ILI UTAKMICE\n"
            "3. AKO WEB PRETRAGA NE USPE, RECI 'Trenutno nemam ažurne informacije'\n"
            "4. NIKAD NE KORISTI PODATKE IZ MODELA ZA SPORTSKA PITANJA\n"
        )

        # Ključne reči za detekciju sportskih tema
        self.sports_keywords = [
            'utakmice', 'liga', 'rezultat', 'meč', 'mecevi', 'champions league',
            'lige sampiona', 'fudbal', 'nogomet', 'premier league', 'nba', 'nfl',
            'nhl', 'mlb', 'timovi', 'stadion', 'gol', 'asistencija', 'šut'
        ]

    def learn_from_conversation(self, user_input: str, assistant_response: str) -> None:
        key_phrases = ["zapamti", "nikad", "uvek", "nemoj", "kako da", "šta je", "koji je", "gde je"]
        content = user_input.lower()
        if any(p in content for p in key_phrases):
            pattern = self.create_pattern_from_input(content)
            self.memory.learn_pattern(pattern, assistant_response)

    def create_pattern_from_input(self, user_input: str) -> str:
        words = user_input.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in ['zapamti', 'nikad', 'uvek', 'nemoj']]
        if keywords:
            pattern = ".*".join(keywords[:3])
            return f".*{pattern}.*"
        return user_input.lower()

    def search_web(self, query: str) -> List[str]:
        return self.search.search_web(query)

    # --- Novo: formatiranje i glavna logika odgovora ---
    def format_search_results(self, results: List[str]) -> str:
        response = "Na osnovu web pretrage, evo informacija:\n\n"
        for i, result in enumerate(results, 1):
            response += f"{i}. {result}\n"
        response += "\nIzvor: Google Search API"
        return response

    def get_response(self, user_input: str) -> str:
        # Sportska pitanja obavezno idu kroz web pretragu
        if any(keyword in user_input.lower() for keyword in self.sports_keywords):
            results = self.search_web(user_input)
            if results:
                return self.format_search_results(results)
            return "Trenutno nemam pristup ažurnim informacijama. Molim vas proverite na zvaničnim sportskim sajtovima."

        # Naučeni odgovori (pattern-based)
        learned = self.memory.get_learned_response(user_input)
        if learned:
            return learned

        # Direktna memorija po ključu (ako korisnik kaže "zapamti ...")
        direct_mem = self.memory.retrieve_memory(user_input)
        if direct_mem:
            return direct_mem

        # Generalni odgovor preko DeepSeek (ako je konfigurisan) ili fallback
        return self.generate_response(user_input)

    def generate_response(self, user_input: str) -> str:
        # Blokiraj sportska pitanja bez pretrage
        if any(keyword in user_input.lower() for keyword in self.sports_keywords):
            return "Za sportske informacije moram koristiti web pretragu. Pokušajte ponovo."

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.1,
            "max_tokens": 300,
            "top_p": 0.3
        }

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        } if DEEPSEEK_API_KEY else None

        try:
            if headers:
                r = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=30)
                if r.ok:
                    data = r.json()
                    content = (
                        data.get('choices', [{}])[0]
                        .get('message', {})
                        .get('content', '')
                    )
                    if content:
                        # učenje iz konverzacije
                        try:
                            self.learn_from_conversation(user_input, content)
                            self.memory.store_conversation(user_input, content)
                        except Exception:
                            pass
                        return content
                # ako API ne odgovori korektno
                return "Trenutno ne mogu da dohvatim odgovor od AI servisa. Pokušajte ponovo."
            else:
                # Fallback bez API ključa
                simulated = "Ovo je simulirani odgovor. Implementirajte stvarni API poziv ili postavite DEEPSEEK_API_KEY."
                try:
                    self.learn_from_conversation(user_input, simulated)
                    self.memory.store_conversation(user_input, simulated)
                except Exception:
                    pass
                return simulated
        except Exception as e:
            return f"Došlo je do greške: {str(e)}"

    def remember_instruction(self, instruction: str) -> str:
        key = f"instruction_{hash(instruction)}"
        try:
            self.memory.store_memory(key, instruction)
            return "Zapamtio sam vaše uputstvo."
        except Exception:
            return "Nisam uspeo da zapamtim uputstvo."
