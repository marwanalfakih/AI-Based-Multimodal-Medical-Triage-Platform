# AI- Based Multimodal Medical Triage Platform

AI-powered web-based triage system built with Django. A web-based medical triage platform that helps patients submit emergency cases and enables doctors and hospitals to review, prioritize, and manage incoming medical situations. The system combines a full Django web application with a multimodal AI pipeline that analyzes text, images, and voice input to produce an explainable urgency score and a Red/Yellow/Green triage recommendation.

## Features
- Multimodal input (text, voice, images)
- AI analysis (MaxViT, Whisper, NLP)
- Triage classification (Red/Yellow/Green)
- Explainable AI (Grad-CAM)
- Doctor dashboard & admin panel

## Tech Stack
Python, Django, PyTorch, timm, Whisper, OpenCV, NumPy, Whisper, Grad-CAM, Transformers, SQLite, Bootstrap, HTML, CSS, JavaScript


## Setup
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

## License
MIT — see LICENSE for details.

## License
MIT — see LICENSE for details.
