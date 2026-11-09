# ai_analysis/services/nlp_service.py
import re
from typing import Dict, List, Tuple

class NLPService:
    """Natural Language Processing service for text analysis"""
    
    # Medical keywords with severity weights (0-1)
    SEVERITY_KEYWORDS = {
        # High severity (red)
        'high': {
            'chest pain': 0.95,
            'difficulty breathing': 0.90,
            'severe bleeding': 0.95,
            'unconscious': 0.98,
            'stroke': 0.95,
            'heart attack': 0.98,
            'severe burn': 0.90,
            'severe allergic reaction': 0.92,
            'choking': 0.95,
            'seizure': 0.90,
            'head injury': 0.88,
            'severe head trauma': 0.95,
            'not breathing': 0.99,
            'cardiac arrest': 0.99,
            'suicidal': 0.95,
        },
        # Medium severity (yellow)
        'medium': {
            'fracture': 0.70,
            'moderate bleeding': 0.65,
            'high fever': 0.70,
            'dehydration': 0.60,
            'asthma attack': 0.75,
            'moderate burn': 0.65,
            'vomiting': 0.60,
            'diarrhea': 0.55,
            'infection': 0.65,
            'dizziness': 0.60,
            'fainting': 0.70,
            'abdominal pain': 0.65,
        },
        # Low severity (green)
        'low': {
            'minor cut': 0.30,
            'cold': 0.20,
            'headache': 0.25,
            'rash': 0.30,
            'sore throat': 0.20,
            'cough': 0.25,
            'mild pain': 0.35,
            'minor burn': 0.30,
            'insect bite': 0.20,
            'minor injury': 0.25,
        }
    }
    
    def __init__(self):
        self.text = ""
    
    def analyze(self, text: str) -> Dict:
        """Analyze text and return severity score with explanations"""
        self.text = text.lower()
        
        # Calculate scores from keywords
        high_score, high_matches = self._calculate_score('high')
        medium_score, medium_matches = self._calculate_score('medium')
        low_score, low_matches = self._calculate_score('low')
        
        # Calculate final score (weighted)
        total_weighted = (high_score * 1.0) + (medium_score * 0.5) + (low_score * 0.2)
        max_possible = 1.0 + 0.5 + 0.2
        severity_score = (total_weighted / max_possible) * 100
        
        # Detect urgency indicators
        urgency_indicators = self._detect_urgency()
        
        # Extract medical entities
        medical_entities = self._extract_medical_entities()
        
        # Prepare explanation
        keywords = []
        for level, weight in [('high', 1.0), ('medium', 0.7), ('low', 0.4)]:
            if level == 'high' and high_matches:
                for match in high_matches[:5]:
                    keywords.append({
                        'word': match,
                        'severity': 'high',
                        'score': self.SEVERITY_KEYWORDS['high'].get(match, 0.8) * 100
                    })
            elif level == 'medium' and medium_matches:
                for match in medium_matches[:3]:
                    keywords.append({
                        'word': match,
                        'severity': 'medium',
                        'score': self.SEVERITY_KEYWORDS['medium'].get(match, 0.6) * 100
                    })
            elif level == 'low' and low_matches:
                for match in low_matches[:2]:
                    keywords.append({
                        'word': match,
                        'severity': 'low',
                        'score': self.SEVERITY_KEYWORDS['low'].get(match, 0.3) * 100
                    })
        
        return {
            'score': round(severity_score, 2),
            'keywords': keywords,
            'entities': medical_entities,
            'urgency_indicators': urgency_indicators,
            'suggested_level': self._get_suggested_level(severity_score),
            'explanation': self._generate_explanation(severity_score, high_matches, medium_matches)
        }
    
    def _calculate_score(self, level: str) -> Tuple[float, List[str]]:
        """Calculate score for a severity level"""
        matches = []
        total_score = 0.0
        
        for keyword, weight in self.SEVERITY_KEYWORDS[level].items():
            if keyword in self.text:
                matches.append(keyword)
                total_score += weight
        
        if matches:
            # Cap at 1.0
            return min(total_score / len(matches), 1.0), matches
        return 0.0, []
    
    def _detect_urgency(self) -> List[str]:
        """Detect urgency indicators in text"""
        urgency_patterns = [
            (r'\bimmediately\b', 'Immediate'),
            (r'\bemergency\b', 'Emergency mentioned'),
            (r'\b(?:need|must) see doctor\b', 'Urgent request'),
            (r'\b(?:blood|bleeding)\b', 'Bleeding mentioned'),
            (r'\b(?:can\'t|cannot|unable to) breathe\b', 'Breathing difficulty'),
        ]
        
        indicators = []
        for pattern, description in urgency_patterns:
            if re.search(pattern, self.text):
                indicators.append(description)
        
        return indicators
    
    def _extract_medical_entities(self) -> List[Dict]:
        """Extract medical entities from text"""
        entities = []
        
        # Simple entity extraction (can be enhanced with NER model)
        body_parts = ['chest', 'head', 'stomach', 'arm', 'leg', 'back', 'neck']
        symptoms = ['pain', 'bleeding', 'fever', 'nausea', 'dizziness', 'swelling']
        
        for part in body_parts:
            if part in self.text:
                entities.append({'type': 'body_part', 'value': part})
        
        for symptom in symptoms:
            if symptom in self.text:
                entities.append({'type': 'symptom', 'value': symptom})
        
        return entities
    
    def _get_suggested_level(self, score: float) -> str:
        """Get suggested triage level based on score"""
        if score >= 70:
            return 'red'
        elif score >= 40:
            return 'yellow'
        else:
            return 'green'
    
    def _generate_explanation(self, score: float, high_matches: List[str], medium_matches: List[str]) -> str:
        """Generate human-readable explanation"""
        if score >= 70:
            if high_matches:
                return f"High severity indicators detected: {', '.join(high_matches[:3])}. Immediate attention recommended."
            else:
                return "High severity level based on symptom analysis. Immediate attention recommended."
        elif score >= 40:
            if medium_matches:
                return f"Moderate severity indicators: {', '.join(medium_matches[:3])}. Urgent care recommended."
            else:
                return "Moderate severity level. Prompt medical attention recommended."
        else:
            return "Low severity symptoms. Non-urgent care recommended."
        

        