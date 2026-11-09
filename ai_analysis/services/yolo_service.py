# ai_analysis/services/yolo_service.py
import os
import torch
import numpy as np
import cv2
from ultralytics import YOLO
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image, preprocess_image
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from PIL import Image
from typing import Dict, Tuple, Optional

class YOLOService:
    """YOLOv8 based wound classification service with XAI support"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.cam = None
        self.class_names = []
        
        # Default path - adjust to your model location
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'models', 'wound_classifier.pt'
            )
        
        if os.path.exists(model_path):
            self.load_model(model_path)
        else:
            print(f"⚠️ YOLO model not found at {model_path}")
    
    def load_model(self, model_path: str):
        """Load YOLOv8 model and setup Grad-CAM"""
        try:
            self.model = YOLO(model_path)
            self.model.model.requires_grad_(True)
            self.model.model.train()
            
            # Get class names from model
            self.class_names = list(self.model.names.values())
            
            # Setup Grad-CAM for explainability
            target_layers = [self.model.model.model[-2]]
            
            # Create wrapper for Grad-CAM
            class YOLOWrapper(torch.nn.Module):
                def __init__(self, model):
                    super().__init__()
                    self.model = model
                
                def forward(self, x):
                    device = next(self.model.parameters()).device
                    if x.device != device:
                        x = x.to(device)
                    result = self.model(x)
                    if isinstance(result, tuple):
                        return result[0]
                    return result
            
            wrapped_model = YOLOWrapper(self.model.model)
            self.cam = GradCAM(model=wrapped_model, target_layers=target_layers)
            
            print(f"✅ YOLO model loaded from {model_path}")
            print(f"   Classes: {self.class_names}")
            
        except Exception as e:
            print(f"❌ Error loading YOLO model: {e}")
    
    def classify_wound(self, image_pil: Image.Image) -> Dict[str, float]:
        """Classify wound image and return probabilities"""
        if self.model is None:
            return {"error": "Model not loaded"}
        
        if image_pil is None:
            return {"error": "No image provided"}
        
        try:
            results = self.model.predict(image_pil, verbose=False)
            result = results[0]
            probs = result.probs.data.cpu().numpy()
            
            return {self.class_names[i]: float(probs[i]) for i in range(len(self.class_names))}
            
        except Exception as e:
            print(f"❌ Classification error: {e}")
            return {"error": str(e)}
    
    def explain_decision(self, image_pil: Image.Image) -> Tuple[np.ndarray, str]:
        """Generate Grad-CAM heatmap to explain model decision"""
        if self.cam is None:
            return np.array(image_pil), "XAI not available - model not loaded"
        
        if image_pil is None:
            return None, "No image provided"
        
        try:
            # Preprocess image
            img = np.array(image_pil)
            img = cv2.resize(img, (224, 224))
            rgb_img_float = np.float32(img) / 255
            input_tensor = preprocess_image(rgb_img_float, mean=[0.0, 0.0, 0.0], std=[1.0, 1.0, 1.0])
            
            # Get device
            device = next(self.model.model.parameters()).device
            input_tensor = input_tensor.to(device)
            input_tensor.requires_grad = True
            
            # Get prediction
            preds = self.model.model(input_tensor)
            if isinstance(preds, tuple):
                preds = preds[0]
            top_class_index = torch.argmax(preds[0]).item()
            
            # Generate heatmap
            targets = [ClassifierOutputTarget(top_class_index)]
            grayscale_cam = self.cam(input_tensor=input_tensor, targets=targets)
            grayscale_cam = grayscale_cam[0, :]
            visualization = show_cam_on_image(rgb_img_float, grayscale_cam, use_rgb=True)
            
            explanation = f"The highlighted area shows where the model focused to classify this as '{self.class_names[top_class_index]}'"
            
            return visualization, explanation
            
        except Exception as e:
            print(f"❌ XAI error: {e}")
            return np.array(image_pil), f"Error: {str(e)}"