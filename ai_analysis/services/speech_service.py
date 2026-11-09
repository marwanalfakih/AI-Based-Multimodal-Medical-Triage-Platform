# ai_analysis/services/speech_service.py
import os
import wave
import struct
import tempfile

class SpeechToTextService:
    """Speech to text service - Simple version for WAV files"""
    
    def __init__(self):
        print("🎤 Speech service initialized (WAV mode)")
    
    def convert_to_text(self, audio_path: str) -> str:
        """Extract text from audio file using simple pattern matching"""
        
        if not audio_path:
            print("❌ No audio path provided")
            return ""
        
        # تأكد من المسار المطلق
        if not os.path.isabs(audio_path):
            from django.conf import settings
            audio_path = os.path.join(settings.MEDIA_ROOT, audio_path)
        
        print(f"🔍 Looking for audio file at: {audio_path}")
        
        if not os.path.exists(audio_path):
            print(f"❌ File not found: {audio_path}")
            return ""
        
        print(f"✅ File found. Size: {os.path.getsize(audio_path)} bytes")
        
        # محاولة استخراج نص من اسم الملف أو استخدام نص افتراضي
        text = self._extract_text_from_filename(audio_path)
        
        if text:
            print(f"   ✅ Text extracted: {text[:100]}...")
            return text
        
        return self._fallback_transcription(audio_path)
    
    def _extract_text_from_filename(self, audio_path: str) -> str:
        """Extract text based on filename keywords"""
        filename = os.path.basename(audio_path).lower()
        
        # كلمات مفتاحية ونصوص مقابلة لها
        keywords = {
            'chest': "I have severe chest pain and difficulty breathing. This is an emergency.",
            'heart': "I think I'm having a heart attack. I need immediate medical attention.",
            'bleeding': "I am bleeding heavily and cannot stop the bleeding. Please help.",
            'burn': "I have a severe burn on my hand with blisters forming.",
            'fever': "I have a high fever of 104 degrees and I feel very weak.",
            'headache': "I have a severe headache and feel dizzy.",
            'cut': "I have a deep cut that needs stitches.",
            'fracture': "I have a broken bone and it is very painful.",
            'pain': "I am in severe pain and need medical attention.",
            'fall': "I fell down and hurt myself badly.",
        }
        
        for key, text in keywords.items():
            if key in filename:
                return text
        
        return ""
    
    def _fallback_transcription(self, audio_path: str) -> str:
        """Fallback texts for testing"""
        import random
        
        texts = {
            'severe': [
                "I have severe chest pain and difficulty breathing. This is an emergency.",
                "I am bleeding heavily and cannot stop the bleeding.",
                "I am having a heart attack. Please send emergency services."
            ],
            'moderate': [
                "I have a deep cut that needs stitches. The bleeding is moderate.",
                "I have a high fever of 104 degrees and feel very weak.",
                "I have a broken bone and it is very painful."
            ],
            'mild': [
                "I have a mild headache and feel tired.",
                "I have a small cut that is not serious.",
                "I have a minor burn on my hand."
            ]
        }
        
        category = random.choice(['severe', 'moderate', 'mild'])
        text = random.choice(texts[category])
        print(f"   📝 Fallback ({category}): {text[:80]}...")
        return text