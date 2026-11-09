# train_yolo.py
import os
import shutil
from ultralytics import YOLO

# splitted dataset contains: train/, val/, test/)
DATASET_PATH = "ai_analysis/dataset"

# Path to save trained model
FINAL_MODEL_PATH = "ai_analysis/ml_models/wound_classifier.pt"

# ============================================
# Training
# ============================================

def train_model():
    print("="*60)
    print("🚀 Starting YOLOv8 Training")
    print("="*60)

    # 1. التأكد من وجود مجلد البيانات
    if not os.path.exists(DATASET_PATH):
        print(f"❌ Error: Dataset folder not found at '{DATASET_PATH}'")
        print("   Make sure you have the dataset folder with train/, val/, test/ subfolders")
        return

    # 2. عرض مسار البيانات المطلق للتوضيح
    abs_dataset_path = os.path.abspath(DATASET_PATH)
    print(f"📂 Using dataset at: {abs_dataset_path}")

    # 3. التأكد من وجود المجلدات المطلوبة داخل مجلد البيانات
    required_dirs = ['train', 'val', 'test']
    for d in required_dirs:
        if not os.path.exists(os.path.join(abs_dataset_path, d)):
            print(f"⚠️ Warning: '{d}' folder not found inside dataset directory")

    # 4. تحميل نموذج YOLO
    # نستخدم نموذج تصنيف صغير ليتناسب مع حجم البيانات
    model = YOLO('yolov8n-cls.pt')

    # 5. تدريب النموذج - نمرر المسار إلى المجلد الرئيسي، وليس إلى ملف data.yaml
    results = model.train(
        data=abs_dataset_path,  # ✅ المجلد الرئيسي الذي يحتوي على train/ و val/ و test/
        epochs=30,               # عدد epochs (قلل للاختبار، زد للدقة)
        imgsz=224,               # حجم الصور المدخلة
        batch=16,               # حجم الدفعة
        device='cpu',           # استخدم 'cuda' إذا كان لديك GPU
        workers=0,              # أبقها 0 لتجنب مشاكل Windows
        verbose=True
    )

    # 6. نسخ النموذج من مسار YOLO الافتراضي إلى مسارنا المفضل
    # بعد التدريب، سيكون النموذج في مجلد باسم مثل: 'runs/classify/train/weights/best.pt'
    # نبحث عن الملف
    default_model_path = 'runs/classify/train/weights/best.pt'
    if os.path.exists(default_model_path):
        os.makedirs(os.path.dirname(FINAL_MODEL_PATH), exist_ok=True)
        shutil.copy(default_model_path, FINAL_MODEL_PATH)
        print(f"\n✅ Model saved to: {FINAL_MODEL_PATH}")
    else:
        print("\n⚠️ Could not find the trained model file. Look for it manually in 'runs/classify/'")

    print("\n" + "="*60)
    print("✅ Training Complete!")
    print("="*60)

if __name__ == "__main__":
    # تثبيت المكتبة إذا لزم الأمر (يمكنك تشغيله يدوياً)
    # os.system("pip install ultralytics")
    train_model()