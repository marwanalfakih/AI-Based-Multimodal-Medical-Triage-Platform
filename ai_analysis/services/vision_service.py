# ai_analysis/services/vision_service.py
import os
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
from torchvision import transforms
from typing import Dict, List, Tuple, Optional
import timm
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
import base64
import io
import cv2

# إعدادات النموذج
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

# أسماء الفئات حسب ترتيب النموذج
CLASSES = ["Abrasions", "Bruises", "Burns", "Cut", "Laceration", "Stab_wound"]

# أسماء العرض مع أيقونات
CLASS_DISPLAY = {
    "Abrasions": "Abrasions (سحجات)",
    "Bruises": "Bruises (كدمات)",
    "Burns": "Burns (حروق)",
    "Cut": "Cut (جروح سطحية)",
    "Laceration": "Laceration (جروح غائرة)",
    "Stab_wound": "Stab Wound (طعنات)",
}

# شدة الإصابة لكل فئة (من 0-100)
SEVERITY_MAP = {
    "Burns": 90,
    "Stab_wound": 95,
    "Laceration": 85,
    "Cut": 70,
    "Abrasions": 50,
    "Bruises": 40,
}

# العلاج المقترح
TREATMENT_MAP = {
    "Burns": "Cool with running water for 15-20 minutes, cover with sterile dressing, seek medical attention",
    "Stab_wound": "Apply pressure, DO NOT remove any embedded object, seek immediate emergency care",
    "Laceration": "Apply pressure to stop bleeding, seek medical attention for possible stitches",
    "Cut": "Clean with soap and water, apply pressure, cover with sterile bandage",
    "Abrasions": "Clean gently with mild soap, apply antibiotic ointment, cover with bandage",
    "Bruises": "Apply ice pack for 15-20 minutes, rest, elevate if possible",
}


class VisionService:
    """Vision service using MaxViT-Tiny model with Grad-CAM explainability"""

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.cam = None
        self.classes = CLASSES
        self.class_display = CLASS_DISPLAY
        self.img_size = 224
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'ml_models', 'best.pt'
            )
        
        self.model_path = model_path
        self._load_model()
    
    def _load_model(self):
        """Load MaxViT-Tiny model from checkpoint"""
        try:
            print(f"🔍 Loading MaxViT model from: {self.model_path}")
            
            if not os.path.exists(self.model_path):
                print(f"❌ Model not found at {self.model_path}")
                self.model = None
                return
            
            # تحميل checkpoint
            ckpt = torch.load(self.model_path, map_location="cpu", weights_only=False)
            
            # استخراج معلومات النموذج
            if isinstance(ckpt, dict) and "state_dict" in ckpt:
                timm_id = ckpt.get("timm_id", "maxvit_tiny_tf_224")
                num_classes = ckpt.get("num_classes", len(CLASSES))
                self.classes = ckpt.get("classes", CLASSES)
                self.img_size = 224
               
                state_dict = ckpt["state_dict"]
                print(f"  Architecture: {timm_id}")
                print(f"  Classes ({num_classes}): {self.classes}")
                print(f"  Using forced image size: {self.img_size} (ignoring checkpoint)")
            else:
                timm_id = "maxvit_tiny_tf_224"
                num_classes = len(CLASSES)
                self.img_size = 224
                state_dict = ckpt
                print(f"  Assuming {timm_id}, {num_classes} classes")
                print(f"  Using default image size: {self.img_size}")
            
            # بناء النموذج
            try:
                self.model = timm.create_model(
                    timm_id,
                    pretrained=False,
                    num_classes=num_classes,
                    img_size=self.img_size,
                )
            except TypeError:
                self.model = timm.create_model(
                    timm_id, pretrained=False, num_classes=num_classes
                )
            
            # تحميل الأوزان مع تجاهل أخطاء الحجم
            missing, unexpected = self.model.load_state_dict(state_dict, strict=False)
            if missing:
                print(f"  ⚠️ Missing keys: {len(missing)}")
            if unexpected:
                print(f"  ⚠️ Unexpected keys: {len(unexpected)}")
            
            self.model = self.model.to(self.device).eval()
            
            # إعداد Grad-CAM
            target_layer = self._get_target_layer()
            self.cam = GradCAM(model=self.model, target_layers=[target_layer])
            
            # إعداد preprocessing
            self.preprocess = transforms.Compose([
                transforms.Resize((self.img_size, self.img_size)),
                transforms.ToTensor(),
                transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD)
            ])
            
            print(f"✅ MaxViT model loaded successfully on {self.device}")
            print(f"   Image size: {self.img_size}")
            
        except Exception as e:
            print(f"❌ Error loading MaxViT model: {e}")
            import traceback
            traceback.print_exc()
            self.model = None


    def _get_target_layer(self):
        """Get target layer for Grad-CAM"""
        try:
            return self.model.stages[-1].blocks[-1].norm2
        except (AttributeError, IndexError):
            try:
                return self.model.stages[-1].blocks[-1]
            except (AttributeError, IndexError):
                try:
                    return self.model.stages[-1]
                except (AttributeError, IndexError):
                    return list(self.model.modules())[-3]
    
    def predict(self, image_pil: Image.Image) -> Dict:
        """Classify wound image and return all probabilities"""
        if self.model is None:
            return self._fallback_analysis()
        
        try:
            if image_pil.mode != "RGB":
                image_pil = image_pil.convert("RGB")
            
            # Preprocess
            img_tensor = self.preprocess(image_pil)
            img_tensor = img_tensor.unsqueeze(0).to(self.device)
            
            # Inference
            with torch.no_grad():
                logits = self.model(img_tensor)
                probs = F.softmax(logits, dim=1)[0].cpu().numpy()
            
            # Prepare all predictions with percentages
            all_predictions = {}
            for i, cls in enumerate(self.classes):
                display_name = CLASS_DISPLAY.get(cls, cls)
                percentage = float(probs[i]) * 100
                all_predictions[display_name] = round(percentage, 2)
            
            # Get top prediction
            top_idx = np.argmax(probs)
            top_class = self.classes[top_idx]
            top_confidence = float(probs[top_idx]) * 100
            
            return {
                'injury_type': top_class,
                'display_name': CLASS_DISPLAY.get(top_class, top_class),
                'confidence': top_confidence,
                'severity_score': SEVERITY_MAP.get(top_class, 50),
                'severity_level': self._get_severity_level(SEVERITY_MAP.get(top_class, 50)),
                'recommended_treatment': TREATMENT_MAP.get(top_class, 'Consult a healthcare provider'),
                'all_predictions': all_predictions,
                'probabilities': {cls: float(probs[i]) for i, cls in enumerate(self.classes)}
            }
            
        except Exception as e:
            print(f"Vision prediction error: {e}")
            return self._fallback_analysis()
    
    def analyze_image(self, image_path: str) -> Dict:
        """Analyze image from file path"""
        try:
            image = Image.open(image_path)
            return self.predict(image)
        except Exception as e:
            print(f"Error analyzing image {image_path}: {e}")
            return self._fallback_analysis()
    
    def analyze_multiple(self, image_paths: List[str]) -> Dict:
        """Analyze multiple images and combine results"""
        if not image_paths:
            return {
                'score': 0, 
                'suggested_level': 'green',
                'primary_injury': 'unknown',
                'all_predictions': {},
                'individual_analyses': []
            }
        
        results = [self.analyze_image(path) for path in image_paths]
        
        # Find most severe
        most_severe = max(results, key=lambda x: x.get('severity_score', 0))
        
        # Calculate combined score
        scores = [r.get('severity_score', 0) for r in results]
        combined_score = sum(scores) / len(scores) if scores else 0
        
        return {
            'score': combined_score,
            'suggested_level': 'red' if combined_score >= 70 else ('yellow' if combined_score >= 40 else 'green'),
            'primary_injury': most_severe.get('injury_type', 'unknown'),
            'display_name': most_severe.get('display_name', 'Unknown'),
            'confidence': most_severe.get('confidence', 0),
            'severity_level': most_severe.get('severity_level', 'unknown'),
            'recommended_treatment': most_severe.get('recommended_treatment', ''),
            'all_predictions': most_severe.get('all_predictions', {}),
            'individual_analyses': results
        }
    
    def generate_heatmap(self, image_pil: Image.Image) -> Tuple[Optional[str], str, Dict]:
        """Generate Grad-CAM heatmap and return as base64 with predictions"""
        if self.cam is None or self.model is None:
            return None, "XAI not available", {}
        
        try:
            if image_pil.mode != "RGB":
                image_pil = image_pil.convert("RGB")
            
            # Resize for visualization
            img_resized = image_pil.resize((self.img_size, self.img_size))
            rgb_img_float = np.float32(np.array(img_resized)) / 255.0
            
            # Preprocess
            img_tensor = self.preprocess(image_pil)
            input_tensor = img_tensor.unsqueeze(0).to(self.device)
            
            # Get predictions
            with torch.no_grad():
                logits = self.model(input_tensor)
                probs = F.softmax(logits, dim=1)[0].cpu().numpy()
                top_class_index = int(torch.argmax(logits[0]).item())
            
            # Prepare all predictions
            all_predictions = {}
            for i, cls in enumerate(self.classes):
                display_name = CLASS_DISPLAY.get(cls, cls)
                percentage = float(probs[i]) * 100
                all_predictions[display_name] = round(percentage, 2)
            
            # Generate heatmap
            targets = [ClassifierOutputTarget(top_class_index)]
            grayscale_cam = self.cam(input_tensor=input_tensor, targets=targets)
            grayscale_cam = grayscale_cam[0, :]
            visualization = show_cam_on_image(rgb_img_float, grayscale_cam, use_rgb=True)
            
            # Convert to base64
            visualization_bgr = cv2.cvtColor(visualization, cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode('.png', visualization_bgr)
            heatmap_base64 = base64.b64encode(buffer).decode()
            
            top_class = self.classes[top_class_index]
            confidence = float(probs[top_class_index]) * 100
            
            explanation = f"The highlighted area shows where the model focused to classify this as '{CLASS_DISPLAY.get(top_class, top_class)}' with {confidence:.1f}% confidence"
            
            return f"data:image/png;base64,{heatmap_base64}", explanation, all_predictions
            
        except Exception as e:
            print(f"XAI error: {e}")
            import traceback
            traceback.print_exc()
            return None, f"Error: {str(e)}", {}
    
    def explain_decision(self, image_pil: Image.Image) -> Tuple[Optional[np.ndarray], str]:
        """Legacy method for explain decision"""
        heatmap, explanation, _ = self.generate_heatmap(image_pil)
        return heatmap, explanation
    
    def _get_severity_level(self, score: float) -> str:
        if score >= 75:
            return 'severe'
        elif score >= 45:
            return 'moderate'
        return 'mild'
    
    def _fallback_analysis(self) -> Dict:
        return {
            'injury_type': 'unknown',
            'display_name': 'Unknown',
            'confidence': 0,
            'severity_score': 50,
            'severity_level': 'unknown',
            'recommended_treatment': 'Please consult a healthcare provider',
            'all_predictions': {},
            'probabilities': {}
        }