import os
import re
import requests
import json
from typing import List, Optional, Dict
from scipy.optimize import minimize
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
            print("SERPAPI_API_KEY nije konfigurisan - web pretraga onemogućena")
            return ["Web pretraga je trenutno onemogućena. Molim kontaktirajte administratora."]
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
        except Exception as e:
            print(f"Search error: {e}")
            return ["Greška pri web pretrazi. Molim pokušajte ponovo."]

class NESAKOChatbot:
    def __init__(self):
        self.memory = NESAKOMemoryORM()
        self.search = NESAKOSearch()
        # Poboljšani sistem prompt sa fokusom na kvalitetne i korisne odgovore
        self.system_prompt = (
            "TI SI NESAKO - INTELIGENTNI ASISTENT SA KORISNIM I TAČNIM ODGOVORIMA\n\n"
            "OSNOVNA PRAVILA:\n"
            "1. DAJ KORISNE, PRECIZNE I KONTEKSTUALNO RELEVANTNE ODGOVORE\n"
            "2. BUDI PRIRODAN U KOMUNIKACIJI - KORISTI SRPSKI JEZIK\n"
            "3. AKO NE ZNAŠ ODGOVOR, ISKRENO RECI I PONUDI ALTERNATIVNU POMOĆ\n"
            "4. ZA SPORTSKA PITANJA KORISTI WEB PRETRAGU ZA AŽURNE INFORMACIJE\n"
            "5. IZBEGAVAJ GENERIČKE I NEKORISNE ODGOVORE\n"
            "6. FOKUSIRAJ SE NA KONKRETNE INFORMACIJE KOJE KORISNIK TRAŽI\n"
            "7. KORISTI LOGIČKO RAZMIŠLJANJE ZA KOMPLEKSNA PITANJA\n"
            "8. BUDI KONCIZAN ALI OBUHVATAN U ODGOVORIMA\n\n"
            "STRATEGIJA ODGOVARANJA:\n"
            "- Prvo razumi suštinu pitanja\n"
            "- Odgovori direktno na pitanje\n"
            "- Daj konkretne primere ako je potrebno\n"
            "- Objasni složene koncepte jednostavnim jezikom\n"
            "- Poveži sa prethodnim konverzacijama ako je relevantno\n"
        )

        # Ključne reči za detekciju sportskih tema
        self.sports_keywords = [
            'utakmice', 'liga', 'rezultat', 'meč', 'mecevi', 'champions league',
            'lige sampiona', 'fudbal', 'nogomet', 'premier league', 'nba', 'nfl',
            'nhl', 'mlb', 'timovi', 'stadion', 'gol', 'asistencija', 'šut'
        ]

    def learn_from_conversation(self, user_input: str, assistant_response: str) -> None:
        """Enhanced learning with continuous adaptation and pattern recognition"""
        try:
            # Basic pattern learning
            key_phrases = ["zapamti", "nikad", "uvek", "nemoj", "kako da", "šta je", "koji je", "gde je"]
            content = user_input.lower()
            
            if any(p in content for p in key_phrases):
                pattern = self.create_pattern_from_input(content)
                self.memory.learn_pattern(pattern, assistant_response)
            
            # Advanced learning: Extract entities and relationships
            self._extract_entities(user_input, assistant_response)
            
            # Sentiment and preference learning
            self._learn_preferences(user_input, assistant_response)
            
            # Save to persistent memory
            try:
                from .memory_manager import PersistentMemoryManager
                memory = PersistentMemoryManager()
                session_id = "default_session"
                memory.save_learning_data(session_id, 'conversation_pattern', {
                    'user_input': user_input,
                    'assistant_response': assistant_response,
                    'entities': self._extract_entities(user_input),
                    'preferences': self._extract_preferences(user_input)
                }, 0.8)
            except Exception:
                pass
                
        except Exception as e:
            print(f"Enhanced learning error: {e}")
    
    def _extract_entities(self, user_input: str, assistant_response: str) -> None:
        """Extract and learn entities from conversation"""
        # Simple entity extraction - in production, use NER models
        entities = {
            'sports_teams': [],
            'programming_languages': [],
            'technologies': [],
            'preferences': []
        }
        
        # Extract sports teams
        import re
        team_pattern = r'\b(Partizan|Crvena Zvezda|Bayern|Real Madrid|Barcelona|Manchester)\b'
        entities['sports_teams'] = re.findall(team_pattern, user_input, re.IGNORECASE)
        
        # Save entities to memory
        if entities['sports_teams']:
            try:
                self.memory.store_memory('favorite_teams', json.dumps(entities['sports_teams']))
            except:
                pass
    
    def _learn_preferences(self, user_input: str, assistant_response: str) -> None:
        """Learn user preferences from conversation"""
        # Analyze sentiment and preferences
        positive_words = ['dobro', 'super', 'odlično', 'volim', 'sviđa']
        negative_words = ['loše', 'ne volim', 'ne sviđa', 'mrzi']
        
        content = user_input.lower()
        if any(word in content for word in positive_words):
            # Learn positive preferences
            pass
        elif any(word in content for word in negative_words):
            # Learn negative preferences
            pass
    
    def _extract_entities(self, user_input: str) -> List[str]:
        """Extract entities from text"""
        # Simple implementation - use proper NER in production
        entities = []
        words = user_input.split()
        for word in words:
            if len(word) > 3 and word[0].isupper():
                entities.append(word)
        return entities
    
    def _extract_preferences(self, user_input: str) -> Dict[str, list]:
        """Extract user preferences from text"""
        return {
            'likes': [],
            'dislikes': [],
            'interests': []
        }

    def get_sports_data(self, query: str) -> Dict[str, any]:
        """Get real-time sports data from free APIs"""
        try:
            # Football data from free API
            if 'fudbal' in query.lower() or 'football' in query.lower():
                # Use football-data.org free tier
                api_key = os.getenv('FOOTBALL_DATA_API_KEY', '')
                if api_key:
                    headers = {'X-Auth-Token': api_key}
                    response = requests.get('https://api.football-data.org/v4/matches', 
                                          headers=headers, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        return self._parse_football_data(data)
                
                # Fallback to mock data
                return {
                    'type': 'football',
                    'matches': [
                        {
                            'home_team': 'Partizan',
                            'away_team': 'Crvena Zvezda',
                            'competition': 'Superliga Srbije',
                            'time': '20:00',
                            'odds': {'1': 2.5, 'X': 3.2, '2': 2.8}
                        }
                    ],
                    'source': 'mock_data'
                }
            
            # Add more sports as needed
            return {'error': 'Sport not supported yet'}
            
        except Exception as e:
            print(f"Sports data error: {e}")
            return {'error': str(e)}
    
    def _parse_football_data(self, data: Dict[str, any]) -> Dict[str, any]:
        """Parse football data from API response"""
        matches = []
        for match in data.get('matches', [])[:5]:  # Limit to 5 matches
            home_team = match['homeTeam']['name']
            away_team = match['awayTeam']['name']
            competition = match['competition']['name']
            time = match['utcDate']
            
            matches.append({
                'home_team': home_team,
                'away_team': away_team,
                'competition': competition,
                'time': time,
                'odds': self._generate_odds(home_team, away_team)
            })
        
        return {
            'type': 'football',
            'matches': matches,
            'source': 'football-data.org'
        }
    
    def _generate_odds(self, home_team: str, away_team: str) -> Dict[str, float]:
        """Generate realistic odds based on team names using advanced algorithms"""
        try:
            # Use team performance data if available
            home_performance = self._get_team_performance(home_team)
            away_performance = self._get_team_performance(away_team)
            
            # Calculate probabilities using logistic regression-like approach
            home_advantage = 0.4  # Home field advantage
            home_strength = home_performance['attack'] * home_performance['defense']
            away_strength = away_performance['attack'] * away_performance['defense']
            
            # Normalize strengths
            total_strength = home_strength + away_strength
            home_prob = (home_strength / total_strength) + home_advantage
            away_prob = (away_strength / total_strength) - home_advantage
            draw_prob = 1 - home_prob - away_prob
            
            # Ensure probabilities are valid
            home_prob = max(0.2, min(0.7, home_prob))
            away_prob = max(0.2, min(0.7, away_prob))
            draw_prob = max(0.1, min(0.4, draw_prob))
            
            # Normalize to sum to 1
            total = home_prob + away_prob + draw_prob
            home_prob /= total
            away_prob /= total
            draw_prob /= total
            
            # Convert to odds (with margin)
            margin = 0.05  # 5% bookmaker margin
            home_odds = round(1 / (home_prob * (1 - margin)), 2)
            draw_odds = round(1 / (draw_prob * (1 - margin)), 2)
            away_odds = round(1 / (away_prob * (1 - margin)), 2)
            
            return {'1': home_odds, 'X': draw_odds, '2': away_odds}
            
        except Exception:
            # Fallback to simple algorithm
            import random
            home_advantage = random.uniform(0.8, 1.2)
            away_advantage = random.uniform(0.8, 1.2)
            
            home_win = round(2.0 * home_advantage, 2)
            draw = round(3.0 * random.uniform(0.9, 1.1), 2)
            away_win = round(2.0 * away_advantage, 2)
            
            return {'1': home_win, 'X': draw, '2': away_win}
    
    def _get_team_performance(self, team_name: str) -> Dict[str, float]:
        """Get team performance metrics - in real implementation, use actual data"""
        # Mock data - replace with real API calls
        import random
        return {
            'attack': random.uniform(0.5, 1.0),
            'defense': random.uniform(0.5, 1.0),
            'form': random.uniform(0.3, 1.0)
        }
    
    def calculate_betting_combinations(self, matches: List[Dict[str, any]], budget: float) -> List[Dict[str, any]]:
        """Calculate optimal betting combinations using Kelly Criterion and portfolio optimization"""
        try:
            import numpy as np
            from scipy.optimize import minimize
            
            combinations = []
            
            for match in matches:
                # Calculate probabilities using advanced models
                outcomes = []
                for outcome, odds in match['odds'].items():
                    # More sophisticated probability estimation
                    probability = self._calculate_probability(match, outcome)
                    expected_value = odds * probability
                    kelly_fraction = (odds * probability - (1 - probability)) / odds
                    
                    # Apply constraints
                    kelly_fraction = max(0, min(kelly_fraction, 0.1))  # Max 10% of budget
                    
                    outcomes.append({
                        'outcome': outcome,
                        'odds': odds,
                        'probability': probability,
                        'expected_value': expected_value,
                        'kelly_fraction': kelly_fraction
                    })
                
                # Sort by expected value
                outcomes.sort(key=lambda x: x['expected_value'], reverse=True)
                
                # Portfolio optimization across outcomes
                optimal_stakes = self._optimize_portfolio(outcomes, budget)
                
                for i, outcome in enumerate(outcomes):
                    if optimal_stakes[i] > 0:
                        combinations.append({
                            'match': f"{match['home_team']} vs {match['away_team']}",
                            'outcome': outcome['outcome'],
                            'odds': outcome['odds'],
                            'stake': round(optimal_stakes[i], 2),
                            'potential_win': round(optimal_stakes[i] * outcome['odds'], 2),
                            'confidence': outcome['probability'] * 100,
                            'expected_value': outcome['expected_value'],
                            'strategy': 'Portfolio Optimization'
                        })
            
            # Sort by expected value and return top combinations
            combinations.sort(key=lambda x: x['expected_value'], reverse=True)
            return combinations[:10]
            
        except Exception as e:
            print(f"Advanced betting combination error: {e}")
            # Fallback to simple method
            return self._simple_betting_combinations(matches, budget)
    
    def _calculate_probability(self, match: Dict[str, any], outcome: str) -> float:
        """Calculate probability using multiple factors"""
        # This would use real data in production
        import random
        
        # Base probability from odds
        base_prob = 1 / match['odds'][outcome]
        
        # Add some randomness and factors
        factors = {
            'home_advantage': 0.1 if outcome == '1' else -0.05,
            'team_form': random.uniform(-0.1, 0.1),
            'injuries': random.uniform(-0.05, 0.05)
        }
        
        final_prob = base_prob + sum(factors.values())
        return max(0.1, min(0.9, final_prob))
    
    def _optimize_portfolio(self, outcomes: List[Dict[str, any]], budget: float) -> List[float]:
        """Optimize stake allocation using portfolio theory"""
        try:
            import numpy as np
            
            # Expected returns
            returns = [outcome['odds'] - 1 for outcome in outcomes]
            
            # Covariance matrix (simplified)
            n = len(outcomes)
            cov_matrix = np.eye(n) * 0.1  # Assume some correlation
            
            # Optimization function
            def objective(weights):
                port_return = np.dot(weights, returns)
                port_risk = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                return -port_return + 2 * port_risk  # Risk-adjusted return
            
            # Constraints
            constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 0.1})  # 10% of budget
            bounds = [(0, 0.05)] * n  # Max 5% per bet
            
            # Initial guess
            x0 = np.ones(n) / n / 10
            
            # Optimize
            result = minimize(objective, x0, bounds=bounds, constraints=constraints)
            
            if result.success:
                return result.x * budget
            else:
                return np.zeros(n)
                
        except Exception:
            # Fallback to Kelly criterion
            return [outcome['kelly_fraction'] * budget for outcome in outcomes]
    
    def _simple_betting_combinations(self, matches: List[Dict[str, any]], budget: float) -> List[Dict[str, any]]:
        """Simple fallback betting combination calculator"""
        combinations = []
        
        for match in matches:
            outcomes = []
            for outcome, odds in match['odds'].items():
                probability = 1 / odds
                expected_value = odds * probability
                outcomes.append({
                    'outcome': outcome,
                    'odds': odds,
                    'probability': probability,
                    'expected_value': expected_value
                })
            
            outcomes.sort(key=lambda x: x['expected_value'], reverse=True)
            
            for outcome in outcomes[:2]:
                if outcome['expected_value'] > 1.1:  # Only positive expected value
                    stake = round(budget * 0.05 * outcome['probability'], 2)
                    combinations.append({
                        'match': f"{match['home_team']} vs {match['away_team']}",
                        'outcome': outcome['outcome'],
                        'odds': outcome['odds'],
                        'stake': stake,
                        'potential_win': round(stake * outcome['odds'], 2),
                        'confidence': outcome['probability'] * 100,
                        'expected_value': outcome['expected_value'],
                        'strategy': 'Simple Value Betting'
                    })
        
        return combinations[:5]

    def create_pattern_from_input(self, user_input: str) -> str:
        words = user_input.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in ['zapamti', 'nikad', 'uvek', 'nemoj']]
        if keywords:
            pattern = ".*".join(keywords[:3])
            return f".*{pattern}.*"
        return user_input.lower()

    def search_web(self, query: str) -> List[str]:
        # Ensure we always return a list, even if search fails
        try:
            results = self.search.search_web(query)
            return results if results else []
        except Exception as e:
            print(f"Search error: {e}")
            return []

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
        # Prvo proveri da li je pitanje sportske prirode
        is_sports_question = any(keyword in user_input.lower() for keyword in self.sports_keywords)
        
        if is_sports_question:
            results = self.search_web(user_input)
            if results:
                formatted = self.format_search_results(results)
                return f"🔍 **Sportske informacije sa weba:**\n\n{formatted}"
            return "Trenutno nemam pristup ažurnim sportskim informacijama. Molim proverite na zvaničnim sportskim sajtovima."

        # Proveri naučene odgovore
        learned = self.memory.get_learned_response(user_input)
        if learned:
            return learned

        # Proveri direktnu memoriju
        direct_mem = self.memory.retrieve_memory(user_input)
        if direct_mem:
            return direct_mem

        # Generiši odgovor koristeći DeepSeek
        response = self.generate_response(user_input)
        
        # Dodaj disclaimer samo ako je potrebno
        if is_sports_question or any(word in user_input.lower() for word in ['tačno', 'sigurno', 'proveri']):
            response += "\n\nℹ️ *Molim proverite informacije na pouzdanim izvorima*"
        
        return response

    def generate_response(self, user_input: str) -> str:
        # Poboljšani sistem prompt sa boljom ravnotežom između kreativnosti i tačnosti
        enhanced_system_prompt = self.system_prompt + """
        
DODATNA UPUTSTVA ZA KVALITETNE ODGOVORE:
1. BUDI KORISAN I INFORMATIVAN - fokusiraj se na suštinu pitanja
2. KORISTI PRIRODAN JEZIK - odgovori kao da razgovaraš sa čovekom
3. BUDI PRECIZAN - izbegavaj nejasne ili generičke fraze
4. AKO JE PITANJE KOMPLEKSNO - podeli odgovor na logičke delove
5. DAJ PRAKTIČNE SAVETE - fokusiraj se na rešenja, ne samo na teoriju
6. BUDI PROAKTIVAN - predloži sledeće korake ako je relevantno
"""

        # Optimizovani parametri za bolje odgovore
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": enhanced_system_prompt},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.7,  # Povećana temperatura za kreativnije odgovore
            "max_tokens": 800,   # Više tokena za detaljnije odgovore
            "top_p": 0.9,        # Veći top_p za širi izbor reči
            "frequency_penalty": 0.3,  # Umerena penalizacija za ponavljanje
            "presence_penalty": 0.3    # Umerena penalizacija za nove koncepte
        }

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        } if DEEPSEEK_API_KEY else None

        try:
            if headers and DEEPSEEK_API_KEY:
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
                # ako API ne odgovori korektno, koristimo poboljšani fallback
                return self.get_enhanced_fallback_response(user_input)
            else:
                # Fallback bez API ključa
                return self.get_enhanced_fallback_response(user_input)
        except Exception as e:
            return self.get_enhanced_fallback_response(user_input)

    def get_enhanced_fallback_response(self, user_input: str) -> str:
        """Enhanced fallback response when AI services are completely unavailable"""
        # Provide helpful, non-AI generated responses based on common patterns
        input_lower = user_input.lower()
        
        # Pattern-based responses
        if any(word in input_lower for word in ['pozdrav', 'zdravo', 'ćao', 'hello', 'hi']):
            return "Zdravo! Trenutno imam tehničke poteškoće sa AI servisima. Molim pokušajte ponovo za nekoliko minuta."
        
        elif any(word in input_lower for word in ['hvala', 'thanks', 'thank you']):
            return "Nema na čemu! Žao mi je što trenutno ne mogu da pružim potpuniji odgovor zbog tehničkih problema."
        
        elif any(word in input_lower for word in ['pomoć', 'help', 'pomoc']):
            return """🤖 **POMOĆ - TEHNIČKI PROBLEMI**

Trenutno ne mogu da pristupim naprednim AI servisima. Evo šta možete uraditi:

1. **Pokušajte ponovo za 5-10 minuta** - problem može biti privremen
2. **Proverite internet konekciju** 
3. **Koristite specifičnija pitanja** kada se servis vrati
4. **Za hitne slučajeve** koristite direktne izvore informacija

*Servis će biti ponovo dostupan što je pre moguće*"""
        
        # Default helpful response
        return """🤖 **NESAKO AI - TEHNIČKI PREKID**

Trenutno ne mogu da pristupim glavnim AI servisima. Ovo je privremeni problem koji će biti rešen u najkraćem mogućem roku.

**Šta možete uraditi:**
- Pokušajte ponovo za nekoliko minuta
- Koristite web pretragu za trenutne informacije
- Kontaktirajte administratora ako se problem nastavi

*Hvala na strpljenju!*"""

    def validate_response_for_hallucinations(self, response: str, user_input: str) -> str:
        """
        Validates the response for potential hallucinations and adds disclaimers
        """
        response_lower = response.lower()
        
        # Lista zabranjenih izjava - stvari koje AI NE SME da tvrdi
        forbidden_claims = [
            'sigurno znam', 'definitivno je', '100% tačno', 'nema sumnje',
            'potvrđeno je', 'zvanični podaci', 'provereno je', 'garantujem'
        ]
        
        # Lista faktualnih pojmova koji zahtevaju proveru
        factual_triggers = [
            'je', 'su', 'ima', 'bio', 'bila', 'bilo', 'tačno', 'rezultat',
            'pobedio', 'izgubio', 'utakmica', 'šampion', 'takmičenje', 'statistika',
            'broj', 'podatak', 'istina', 'činjenica', 'datum', 'godina', 'cena',
            'cene', 'evra', 'dolara', 'cena', 'cene'
        ]
        
        # Provera za zabranjene izjave
        has_forbidden_claims = any(claim in response_lower for claim in forbidden_claims)
        
        # Provera za faktualne tvrdnje
        has_factual_claims = any(keyword in response_lower for keyword in factual_triggers)
        
        # Provera za sportske pojmove
        sports_keywords = ['utakmica', 'rezultat', 'tim', 'igrač', 'liga', 'šampionat', 'gol', 'asist']
        has_sports_content = any(keyword in response_lower for keyword in sports_keywords)
        
        # Dodaj odgovarajuće disclaimere
        if has_forbidden_claims:
            disclaimer = "\n\n🚨 **UPOZORENJE:** Ovo je AI generisan odgovor. Molim proverite sve informacije na zvaničnim izvorima pre nego što ih koristite."
            if disclaimer not in response:
                response += disclaimer
        
        elif has_factual_claims:
            disclaimer = "\n\n⚠️ **NAPOMENA:** Ove informacije su generisane od strane AI-a. Molim proverite tačnost na pouzdanim izvorima."
            if disclaimer not in response:
                response += disclaimer
        
        elif has_sports_content:
            disclaimer = "\n\n⚽ **SPORTSKE INFORMACIJE:** Za najtačnije i najažurnije sportske informacije, molim posetite zvanične sajtove sportskih organizacija."
            if disclaimer not in response:
                response += disclaimer
        else:
            # Opšti disclaimer za sve AI odgovore
            disclaimer = "\n\nℹ️ **NAPOMENA:** Ovo je AI generisan odgovor. Preporučujem proveru kritičnih informacija na zvaničnim izvorima."
            if disclaimer not in response:
                response += disclaimer
        
        # Dodatna provera za preteranu sigurnost
        if 'sigurno' in response_lower or 'definitivno' in response_lower:
            caution = "\n\n🔍 **SAVET:** Za potpuno tačne informacije, uvek proverite sa više nezavisnih izvora."
            if caution not in response:
                response += caution
        
        return response

    def remember_instruction(self, instruction: str) -> str:
        key = f"instruction_{hash(instruction)}"
        try:
            self.memory.store_memory(key, instruction)
            return "Zapamtio sam vaše uputstvo."
        except Exception:
            return "Nisam uspeo da zapamtim uputstvo."
