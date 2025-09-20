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
        if not results:
            return "Nisam pronašao relevantne rezultate pretrage."
        
        response = "Rezultati web pretrage:\n\n"
        for i, result in enumerate(results, 1):
            # Limit each result to prevent overly long responses
            if len(result) > 200:
                result = result[:197] + "..."
            response += f"{i}. {result}\n"
        response += "\nIzvor: Google Search API\n\n⚠️ *Ove informacije mogu biti neažurne ili netačne*"
        return response

    def get_response(self, user_input: str) -> str:
        # Sportska pitanja obavezno idu kroz web pretragu
        if any(keyword in user_input.lower() for keyword in self.sports_keywords):
            results = self.search_web(user_input)
            if results:
                # Add disclaimer to make it clear this is from web search
                formatted = self.format_search_results(results)
                return f"🔍 **Informacije sa weba (možda nisu ažurne):**\n\n{formatted}\n\n⚠️ *Molim proverite na zvaničnim izvorima za najtačnije informacije*"
            return "Trenutno nemam pristup ažurnim informacijama. Molim vas proverite na zvaničnim sportskim sajtovima."

        # Naučeni odgovori (pattern-based)
        learned = self.memory.get_learned_response(user_input)
        if learned:
            # Add disclaimer for learned responses
            return f"{learned}\n\nℹ️ *Ovo je naučeni odgovor baziran na prethodnim interakcijama*"

        # Direktna memorija po ključu (ako korisnik kaže "zapamti ...")
        direct_mem = self.memory.retrieve_memory(user_input)
        if direct_mem:
            # Add disclaimer for memory-based responses
            return f"{direct_mem}\n\nℹ️ *Ovo je zapamćena informacija iz prethodnih razgovora*"

        # Generalni odgovor preko DeepSeek (ako je konfigurisan) ili fallback
        response = self.generate_response(user_input)
        
        # Add accuracy disclaimer to AI responses
        if "nisam siguran" not in response.lower() and "nemam" not in response.lower():
            response += "\n\nℹ️ *Ovo je AI generisan odgovor - molim proverite informacije ako su kritične*"
        
        return response

    def generate_response(self, user_input: str) -> str:
        # Blokiraj sportska pitanja bez pretrage
        if any(keyword in user_input.lower() for keyword in self.sports_keywords):
            return "Za sportske informacije moram koristiti web pretragu. Pokušajte ponovo."

        # Enhanced system prompt with strict anti-hallucination instructions
        enhanced_system_prompt = self.system_prompt + """
        
STRICT ANTI-HALLUCINATION PROTOCOL:
1. NIKAD NE IZMIŠLJAJ INFORMACIJE - koristi samo ono što znaš iz pouzdanih izvora
2. Ako nisi 100% siguran u odgovor, reci "Nisam siguran" ili "Ne mogu da potvrdim"
3. Nikad ne daj tačne brojeve, datume ili činjenice bez apsolutne sigurnosti
4. Za sve trenutne informacije koristi web pretragu
5. Ako nemaš pristup ažurnim podacima, reci to jasno
6. Preferiraj oprez i tačnost preko brzine odgovora
7. Ne pretpostavljaj - traži dodatne informacije ako je potrebno
8. Koristi samo verifikovane podatke iz sistemskog konteksta

ODGOVORI U SKLADU SA PROTOKOLOM:
- "Trenutno nemam pristup ažurnim informacijama o tome"
- "Nisam siguran u tačnost te informacije"
- "Molim vas proverite na zvaničnim izvorima za najtačnije podatke"
- "Ne mogu da potvrdim ove informacije bez web pretrage"
- "Za tačne i ažurne podatke, preporučujem direktnu proveru"
"""

        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": enhanced_system_prompt},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.1,  # Very low temperature to reduce creativity
            "max_tokens": 300,
            "top_p": 0.1,  # Very low top_p to focus on most likely responses
            "frequency_penalty": 0.5,  # Penalize frequent phrases to reduce repetition
            "presence_penalty": 0.5  # Penalize new concepts to stay on topic
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
                        # Validate response doesn't contain hallucinations
                        validated_content = self.validate_response_for_hallucinations(content, user_input)
                        
                        # učenje iz konverzacije
                        try:
                            self.learn_from_conversation(user_input, validated_content)
                            self.memory.store_conversation(user_input, validated_content)
                        except Exception:
                            pass
                        return validated_content
                # ako API ne odgovori korektno
                return "Trenutno ne mogu da dohvatim odgovor od AI servisa. Molim pokušajte ponovo."
            else:
                # Fallback bez API ključa - beži od izmišljanja
                fallback_response = "Trenutno nemam pristup AI servisu za generisanje odgovora. Molim pokušajte ponovo kasnije ili koristite web pretragu za tačne informacije."
                try:
                    self.learn_from_conversation(user_input, fallback_response)
                    self.memory.store_conversation(user_input, fallback_response)
                except Exception:
                    pass
                return fallback_response
        except Exception as e:
            return f"Trenutno ne mogu da obradim vaš zahtev zbog tehničke greške: {str(e)}"

    def validate_response_for_hallucinations(self, response: str, user_input: str) -> str:
        """
        Validates the response for potential hallucinations and adds disclaimers
        """
        # List of phrases that indicate uncertainty or potential hallucinations
        uncertain_phrases = [
            'verovatno', 'možda', 'pretpostavljam', 'rekao bih', 'čini mi se',
            'mislim da', 'vrv', 'moguće', 'potencijalno', 'izgleda', 'sigurno',
            'definitivno', 'apsolutno', '100%', 'nema sumnje'
        ]
        
        # Check if response contains uncertain or overconfident language
        response_lower = response.lower()
        has_uncertainty = any(phrase in response_lower for phrase in uncertain_phrases)
        
        # Check for specific factual claims that might be hallucinations
        factual_keywords = [
            'je', 'su', 'ima', 'bio', 'bila', 'bilo', 'tačno', 'sigurno',
            'rezultat', 'pobedio', 'izgubio', 'utakmica', 'šampion', 'takmičenje',
            'statistika', 'broj', 'podatak', 'istina', 'činjenica'
        ]
        has_factual_claims = any(keyword in response_lower for keyword in factual_keywords)
        
        # Always add disclaimer for factual content
        if has_factual_claims:
            disclaimer = "\n\n⚠️ *Molim proverite ove informacije na zvaničnim izvorima - ovo je AI generisan odgovor koji može sadržati netačnosti*"
            # Make sure we don't add the disclaimer multiple times
            if disclaimer not in response:
                response += disclaimer
        elif has_uncertainty:
            disclaimer = "\n\nℹ️ *Ovo je AI generisan odgovor baziran na trenutnim informacijama - molim proverite za kritične podatke*"
            if disclaimer not in response:
                response += disclaimer
        else:
            # Add general disclaimer for all AI responses
            disclaimer = "\n\nℹ️ *AI generisan odgovor - preporučujem proveru na zvaničnim izvorima za važne informacije*"
            if disclaimer not in response:
                response += disclaimer
        
        # Additional check for sports-related content
        sports_keywords = ['utakmica', 'rezultat', 'tim', 'igrač', 'liga', 'šampionat']
        if any(keyword in response_lower for keyword in sports_keywords):
            sports_disclaimer = "\n\n⚽ *Za najtačnije sportske informacije preporučujem proveru na zvaničnim sportskim sajtovima*"
            if sports_disclaimer not in response:
                response += sports_disclaimer
        
        return response

    def remember_instruction(self, instruction: str) -> str:
        key = f"instruction_{hash(instruction)}"
        try:
            self.memory.store_memory(key, instruction)
            return "Zapamtio sam vaše uputstvo."
        except Exception:
            return "Nisam uspeo da zapamtim uputstvo."
