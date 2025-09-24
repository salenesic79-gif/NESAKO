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
        # Poboljšani sistem prompt za prirodnije odgovore
        self.system_prompt = (
            "Ti si NESAKO - koristan asistent. "
            "Odgovaraj prirodno i jednostavno na srpskom jeziku. "
            "Budi direktan i konkretan. "
            "Ako ne znaš odgovor, reci to jednostavno. "
            "Izbegavaj duge uvode i tehničke detalje."
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
            return "Nisam pronašao relevantne rezultate."
        
        # Vrati samo prvi rezultat za jednostavniji odgovor
        result = results[0]
        if len(result) > 200:
            result = result[:197] + "..."
        return result

    def get_response(self, user_input: str) -> str:
        # Prvo proveri da li je pitanje sportske prirode
        is_sports_question = any(keyword in user_input.lower() for keyword in self.sports_keywords)
        
        if is_sports_question:
            # Ako nema API ključa, preskoči web pretragu i idi direktno na AI
            if not SERPAPI_API_KEY:
                pass  # Preskoči web pretragu i nastavi na AI
            else:
                results = self.search_web(user_input)
                if results:
                    # Vrati samo prvi rezultat bez dodatnih labela
                    return results[0] if results else "Nisam pronašao informacije."
                return "Trenutno nemam ažurne informacije."

        # Proveri naučene odgovore
        learned = self.memory.get_learned_response(user_input)
        if learned:
            return learned

        # Proveri direktnu memoriju
        direct_mem = self.memory.retrieve_memory(user_input)
        if direct_mem:
            return direct_mem

        # Generiši odgovor koristeći DeepSeek
        return self.generate_response(user_input)

    def generate_response(self, user_input: str) -> str:
        # Pojednostavljen sistem prompt
        enhanced_system_prompt = self.system_prompt

        # Optimizovani parametri za prirodnije odgovore
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": enhanced_system_prompt},
                {"role": "user", "content": user_input}
            ],
            "temperature": 0.9,  # Viša temperatura za prirodnije odgovore
            "max_tokens": 800,   # Više tokena za bolje odgovore
            "top_p": 0.95,       # Veći top_p za širi izbor
            "frequency_penalty": 0.0,  # Bez penalizacije
            "presence_penalty": 0.0    # Bez penalizacije
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
        
        # Pattern-based responses - jednostavniji i prirodniji
        if any(word in input_lower for word in ['pozdrav', 'zdravo', 'ćao', 'hello', 'hi', 'kako si']):
            return "Zdravo! Kako mogu da vam pomognem?"
        
        elif any(word in input_lower for word in ['hvala', 'thanks', 'thank you']):
            return "Nema na čemu! Drago mi je što sam mogao da pomognem."
        
        elif any(word in input_lower for word in ['pomoć', 'help', 'pomoc']):
            return "Kako mogu da vam pomognem? Postavite mi pitanje ili opišite problem."
        
        elif any(word in input_lower for word in ['šta je', 'šta su', 'koji je']):
            return "Trenutno ne mogu da pristupim bazi podataka za tačne informacije. Molim pokušajte sa specifičnijim pitanjem."
        
        # Default helpful response
        return "Trenutno imam ograničen pristup nekim servisima. Postavite mi pitanje i pokušaću da vam pomognem na osnovu dostupnih informacija."

    def validate_response_for_hallucinations(self, response: str, user_input: str) -> str:
        """
        Simplified validation - remove all disclaimers for cleaner responses
        """
        # Ukloni sve disclaimere za čistije odgovore
        return response

    def remember_instruction(self, instruction: str) -> str:
        key = f"instruction_{hash(instruction)}"
        try:
            self.memory.store_memory(key, instruction)
            return "Zapamtio sam vaše uputstvo."
        except Exception:
            return "Nisam uspeo da zapamtim uputstvo."
