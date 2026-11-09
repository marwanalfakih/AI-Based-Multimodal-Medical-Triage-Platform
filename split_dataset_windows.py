# split_dataset_windows.py
import os
import shutil
import random
from pathlib import Path

def split_dataset(source_dir, dest_dir, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
    """
    Split dataset into train, validation, and test sets
    Source directory should have folders for each class
    """
    
    # Create destination directories
    for split in ['train', 'val', 'test']:
        os.makedirs(os.path.join(dest_dir, split), exist_ok=True)
    
    # Get all categories from source directory
    categories = []
    for item in os.listdir(source_dir):
        item_path = os.path.join(source_dir, item)
        if os.path.isdir(item_path):
            categories.append(item)
    
    print(f"Found {len(categories)} categories: {categories}")
    print("="*50)
    
    # Statistics
    stats = {}
    total_images = 0
    
    for category in categories:
        source_path = os.path.join(source_dir, category)
        
        # Get all images
        images = [f for f in os.listdir(source_path) 
                 if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'))]
        
        if not images:
            print(f"⚠️ Warning: No images found in {category}")
            continue
        
        # Shuffle images
        random.shuffle(images)
        
        # Split indices
        total = len(images)
        total_images += total
        train_end = int(total * train_ratio)
        val_end = train_end + int(total * val_ratio)
        
        train_images = images[:train_end]
        val_images = images[train_end:val_end]
        test_images = images[val_end:]
        
        stats[category] = {
            'total': total,
            'train': len(train_images),
            'val': len(val_images),
            'test': len(test_images)
        }
        
        # Create category folders in destination
        for split in ['train', 'val', 'test']:
            os.makedirs(os.path.join(dest_dir, split, category), exist_ok=True)
        
        # Copy images to destination
        for img in train_images:
            src = os.path.join(source_path, img)
            dst = os.path.join(dest_dir, 'train', category, img)
            shutil.copy2(src, dst)
        
        for img in val_images:
            src = os.path.join(source_path, img)
            dst = os.path.join(dest_dir, 'val', category, img)
            shutil.copy2(src, dst)
        
        for img in test_images:
            src = os.path.join(source_path, img)
            dst = os.path.join(dest_dir, 'test', category, img)
            shutil.copy2(src, dst)
        
        print(f"{category}: {len(train_images)} train | {len(val_images)} val | {len(test_images)} test (total: {total})")
    
    # Print summary
    print("\n" + "="*50)
    print("📊 DATASET SPLIT SUMMARY")
    print("="*50)
    
    total_train = sum([s['train'] for s in stats.values()])
    total_val = sum([s['val'] for s in stats.values()])
    total_test = sum([s['test'] for s in stats.values()])
    
    print(f"📁 Training:   {total_train} images ({total_train/total_images*100:.1f}%)")
    print(f"📁 Validation: {total_val} images ({total_val/total_images*100:.1f}%)")
    print(f"📁 Test:       {total_test} images ({total_test/total_images*100:.1f}%)")
    print(f"📊 Total:      {total_images} images")
    print("="*50)
    
    return stats

if __name__ == "__main__":
    # ============================================
    # ⚠️ CHANGE THESE PATHS TO MATCH YOUR SETUP ⚠️
    # ============================================
    
    # Where your original images are (with folders for each class)
    SOURCE_DIR = r"Wound_dataset"
    
    # Where to save the split dataset
    DEST_DIR = r"dataset"
    
    # Run the split
    print("🚀 Starting dataset split...")
    print(f"📂 Source: {SOURCE_DIR}")
    print(f"📂 Destination: {DEST_DIR}")
    print("")
    
    stats = split_dataset(SOURCE_DIR, DEST_DIR)
    
    print("\n✅ Dataset split completed successfully!")