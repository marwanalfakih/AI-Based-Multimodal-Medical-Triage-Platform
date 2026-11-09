# ai_analysis/services/triage_service.py
from typing import Dict, List, Optional
from .nlp_service import NLPService
from .speech_service import SpeechToTextService
from .vision_service import VisionService
from .clinical_nlp_service import ClinicalNLPService


class TriageService:
    """Main service - integrates image, text, and voice analysis"""
    
    def __init__(self):
        print("\n" + "="*50)
        print("🚑 Initializing TriageService")
        print("="*50)
        
        self.nlp_service = NLPService()
        self.vision_service = VisionService()
        self.speech_service = SpeechToTextService()
        self.clinical_nlp = ClinicalNLPService()
        
        print("="*50 + "\n")
    
    def analyze_case(
        self,
        text: Optional[str] = None,
        image_paths: Optional[List[str]] = None,
        audio_path: Optional[str] = None
    ) -> Dict:
        """Analyze case using all available inputs"""
        
        print(f"\n🔍 Analyzing:")
        print(f"   Text: {'Yes' if text else 'No'}")
        print(f"   Images: {'Yes' if image_paths else 'No'} ({len(image_paths) if image_paths else 0})")
        print(f"   Audio: {'Yes' if audio_path else 'No'}")
        
        result = {'has_text_input': False, 'has_images': False, 'has_voice': False}
        
        # ========== 1. Speech to Text ==========
        final_text = text or ""
        if audio_path and not final_text:
            transcribed = self.speech_service.convert_to_text(audio_path)
            if transcribed:
                final_text = transcribed
                result['has_voice'] = True
        
        # ========== 2. Text Analysis ==========
        nlp_score = 25
        clinical_result = {}
        if final_text:
            result['has_text_input'] = True
            basic = self.nlp_service.analyze(final_text)
            print("="*50)
            print(f"📝 NLP RAW RESULT: {basic}")
            print(f"   Score from nlp_service: {basic.get('score')}")
            print("="*50)
            
            nlp_score = basic.get('score', 25)
            clinical_result = self.clinical_nlp.analyze(final_text)

            
        
        # ========== 3. Image Analysis (MaxViT) ==========
        vision_score = 25
        vision_injury = "unknown"
        vision_confidence = 0
        if image_paths:
            result['has_images'] = True
            print(f"🖼️ Analyzing {len(image_paths)} images with MaxViT...")
            vision = self.vision_service.analyze_multiple(image_paths)
            vision_score = vision.get('score', 25)
            vision_injury = vision.get('primary_injury', 'unknown')
            vision_confidence = vision.get('confidence', 0)
            print(f"   Vision score: {vision_score}")
            print(f"   Primary injury: {vision_injury}")
        
        # ========== 4. Composite Score ==========
        if result['has_text_input'] and result['has_images']:
            composite_score = (nlp_score * 0.6) + (vision_score * 0.4)
        elif result['has_text_input']:
            composite_score = nlp_score
        elif result['has_images']:
            composite_score = vision_score
        else:
            composite_score = 25
        
        # ========== 5. Triage Level ==========
        if composite_score >= 70:
            suggested_level = 'red'
        elif composite_score >= 40:
            suggested_level = 'yellow'
        else:
            suggested_level = 'green'
        
        print(f"✅ Result: Score={composite_score:.0f}, Level={suggested_level.upper()}")
        
        return {
            'nlp_score': nlp_score,
            'vision_score': vision_score,
            'composite_score': round(composite_score, 2),
            'suggested_level': suggested_level,
            'vision_injury': vision_injury,
            'vision_confidence': vision_confidence,
            'symptoms': clinical_result.get('symptoms', []),
            'medications': clinical_result.get('medications', []),
            'detected_injuries': clinical_result.get('injuries', []),
            'has_text_input': result['has_text_input'],
            'has_images': result['has_images'],
            'has_voice': result['has_voice']
        }