# ai_analysis/services/speech_service.py
import os
import whisper
import tempfile
import subprocess

class SpeechToTextService:
    """Speech to text service using OpenAI Whisper"""
    
    def __init__(self):
        self.model = None
        self.model_name = "base"
        self._load_model()
    
    def _load_model(self):
        try:
            print("🎤 Loading Whisper model...")
            self.model = whisper.load_model(self.model_name)
            print(f"✅ Whisper model '{self.model_name}' loaded successfully")
        except Exception as e:
            print(f"⚠️ Whisper not available: {e}")
            self.model = None
    
    def convert_to_text(self, audio_path: str) -> str:
        """Convert audio file to text"""
        if not audio_path:
            print("❌ No audio path provided")
            return ""
        
        # 🔴 تأكد من المسار المطلق
        if not os.path.isabs(audio_path):
            audio_path = os.path.join(settings.MEDIA_ROOT, audio_path)
        
        print(f"🔍 Looking for audio file at: {audio_path}")
        
        # التحقق من وجود الملف
        if not os.path.exists(audio_path):
            print(f"❌ File not found: {audio_path}")
            return ""
        
        print(f"✅ File found. Size: {os.path.getsize(audio_path)} bytes")
        
        # استخدام Whisper
        if self.model is None:
            print("❌ Whisper model not loaded")
            return ""
        
        try:
            print(f"🎤 Transcribing: {os.path.basename(audio_path)}")
            result = self.model.transcribe(audio_path)
            text = result["text"].strip()
            print(f"   ✅ Transcription successful: {text[:100]}...")
            return text
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return ""