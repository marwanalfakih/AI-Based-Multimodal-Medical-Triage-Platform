# ai_analysis/services/clinical_nlp_service.py
import re
from typing import Dict, List, Tuple
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification


class ClinicalNLPService:
    """Advanced clinical NLP service with NER and Assertion"""

    def __init__(self):
        self.ner_pipeline = None
        self.assertion_pipeline = None
        self._load_models()
    
    def _load_models(self):
        try:
            print("📚 Loading Clinical NER model...")
            self.ner_pipeline = pipeline(
                "token-classification",
                model="silpakanneganti/bert-medical-ner",
                aggregation_strategy="simple"
            )
            
            print("📚 Loading Clinical Assertion model...")
            ASSERT_MODEL = "bvanaken/clinical-assertion-negation-bert"
            tokenizer = AutoTokenizer.from_pretrained(ASSERT_MODEL)
            model = AutoModelForSequenceClassification.from_pretrained(ASSERT_MODEL)
            self.assertion_pipeline = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer
            )
            
            print("✅ Clinical NLP models loaded")
        except Exception as e:
            print(f"⚠️ Clinical NLP not available: {e}")
    
    def analyze(self, text: str) -> Dict:
        """Analyze clinical text and extract structured information"""
        if not text or not self.ner_pipeline:
            return {
                'symptoms': [],
                'medications': [],
                'injuries': [],
                'timing': [],
                'summary': 'No text provided for analysis'
            }
        
        text_lower = text.lower()
        
        # ========== 1. Detect Injuries from Keywords ==========
        injury_keywords = {
            "🔥 Burns (حروق)": ["burn", "burns", "burnt", "scalding", "scalded"],
            "🟣 Bruises (كدمات)": ["bruise", "bruises", "bruising", "contusion"],
            "🔪 Cut (جروح سطحية)": ["cut", "cuts", "slicing", "sliced"],
            "🩹 Abrasions (سحجات)": ["abrasion", "abrasions", "scrape", "graze"],
            "🗡️ Stab Wound (طعنات)": ["stab", "stabbed", "puncture"],
            "🩸 Laceration (جروح غائرة)": ["laceration", "lacerations", "tear", "gash"]
        }
        
        detected_injuries = []
        for injury_type, keywords in injury_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    detected_injuries.append(injury_type)
                    break
        
        # ========== 2. Detect Medications ==========
        med_keywords = {
            "Tylenol": ["tylenol", "acetaminophen", "paracetamol"],
            "Advil/Ibuprofen": ["advil", "ibuprofen", "motrin"],
            "Aspirin": ["aspirin", "asa"],
            "Antibiotic": ["antibiotic", "amoxicillin", "cephalexin"],
            "Ointment/Cream": ["ointment", "cream", "topical"],
        }
        
        detected_medications = []
        for med_name, keywords in med_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    detected_medications.append(med_name)
                    break
        
        # ========== 3. Detect Timing ==========
        time_patterns = [
            (r'(\d+)\s*(?:minute|min)\s*ago', 'minutes ago'),
            (r'(\d+)\s*(?:hour|hr)\s*ago', 'hours ago'),
            (r'(\d+)\s*(?:day)\s*ago', 'days ago'),
            (r'yesterday', 'yesterday'),
            (r'today', 'today'),
            (r'(\d+)\s*(?:week)\s*ago', 'weeks ago'),
            (r'(\d+)\s*(?:month)\s*ago', 'months ago'),
        ]
        
        timing_info = []
        for pattern, unit in time_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if match.groups():
                    val = match.group(1)
                    timing_info.append(f"{val} {unit}")
                else:
                    timing_info.append(unit)
        
        # ========== 4. Extract Symptoms using NER ==========
        ner_results = self.ner_pipeline(text)
        
        symptoms_raw = []
        for entity in ner_results:
            if entity['entity_group'] in ["Sign_symptom", "Detailed_description", "Clinical_event"]:
                symptoms_raw.append(entity['word'])
        
        # ========== 5. Assertion for Symptoms (Present/Absent) ==========
        sentences = re.split(r'(?<=[.!?])\s+', text)
        negation_words = ['no', 'not', "don't", "doesn't", "didn't", 'without', 'denies', 'denied']
        
        symptoms = []
        for symptom in set(symptoms_raw):
            symptom_lower = symptom.lower()
            for sentence in sentences:
                if symptom_lower in sentence.lower():
                    is_negated = any(neg in sentence.lower() for neg in negation_words)
                    status = "❌ ABSENT" if is_negated else "✅ PRESENT"
                    symptoms.append({
                        "symptom": symptom,
                        "status": status,
                        "is_present": not is_negated
                    })
                    break
        
        # If no symptoms from NER, try keyword matching
        if not symptoms:
            common_symptoms = {
                "pain": "ألم",
                "bleeding": "نزيف",
                "fever": "حمى",
                "nausea": "غثيان",
                "vomiting": "قيء",
                "dizziness": "دوار",
                "swelling": "تورم",
                "redness": "احمرار",
                "headache": "صداع",
            }
            for eng, arb in common_symptoms.items():
                if eng in text_lower:
                    symptoms.append({
                        "symptom": f"{eng} ({arb})",
                        "status": "✅ PRESENT",
                        "is_present": True
                    })
        
        # ========== 6. Generate Summary ==========
        summary_parts = []
        if detected_injuries:
            summary_parts.append(f"**Detected Injuries:** {', '.join(detected_injuries)}")
        if detected_medications:
            summary_parts.append(f"**Medications:** {', '.join(detected_medications)}")
        if timing_info:
            summary_parts.append(f"**Timing:** {', '.join(timing_info)}")
        if symptoms:
            present_symptoms = [s['symptom'] for s in symptoms if s['is_present']]
            if present_symptoms:
                summary_parts.append(f"**Symptoms:** {', '.join(present_symptoms[:5])}")
        
        summary = "\n".join(summary_parts) if summary_parts else "No clinical information extracted"
        
        return {
            'symptoms': symptoms,
            'medications': detected_medications,
            'injuries': detected_injuries,
            'timing': timing_info,
            'summary': summary,
            'raw_text': text
        }