# AI- Based Multimodal Medical Triage Platform

AI-powered web-based triage system built with Django.

## Features
- Multimodal input (text, voice, images)
- AI analysis (MaxViT, Whisper, NLP)
- Triage classification (Red/Yellow/Green)
- Explainable AI (Grad-CAM)
- Doctor dashboard & admin panel

## Tech Stack
Python, Django, PyTorch, timm, Whisper, Transformers, SQLite, Bootstrap

## Setup
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver