import re
from typing import Dict, List, Tuple

from ai_analysis.services.clinical_nlp_service import ClinicalNLPService


class NLPService:
    """Text severity analysis with Clinical NLP integration"""

    SEVERITY_KEYWORDS = {

        'high': {
            'chest pain': 0.95,
            'difficulty breathing': 0.90,
            'severe bleeding': 0.95,
            'unconscious': 0.98,
            'stroke': 0.95,
            'heart attack': 0.98,
            'burn': 0.90,
            'severe burn': 0.95,
            'blister': 0.90,
            'blistering': 0.90,
            'boiling': 0.95,
            'stab': 0.95,
            'not breathing': 0.99,
            'cardiac arrest': 0.99,
        },

        'medium': {
            'fracture': 0.70,
            'moderate bleeding': 0.65,
            'high fever': 0.70,
            'dehydration': 0.60,
            'infection': 0.65,
            'vomiting': 0.60,
            'dizziness': 0.60,
            'cut': 0.60,
            'bruise': 0.55,
            'laceration': 0.75,
            'abrasion': 0.50,
        },

        'low': {
            'minor cut': 0.30,
            'headache': 0.25,
            'cold': 0.20,
            'cough': 0.25,
            'rash': 0.30,
            'minor injury': 0.25,
        }
    }

    CLINICAL_INJURY_SCORE = {

        "🔥 Burns (حروق)": 90,
        "🟣 Bruises (كدمات)": 50,
        "🔪 Cut (جروح سطحية)": 60,
        "🩹 Abrasions (سحجات)": 45,
        "🩸 Laceration (جروح غائرة)": 80,
        "🗡️ Stab Wound (طعنات)": 95

    }

    def __init__(self):

        self.text = ""

        try:
            self.clinical_service = ClinicalNLPService()

        except Exception:

            self.clinical_service = None

    def analyze(self, text: str) -> Dict:

        self.text = text.lower()

        high_score, high_matches = self._calculate_score("high")

        medium_score, medium_matches = self._calculate_score("medium")

        low_score, low_matches = self._calculate_score("low")

        weighted = (
            high_score * 1.0 +
            medium_score * 0.6 +
            low_score * 0.2
        )

        severity_score = (weighted / 1.8) * 100

        clinical_results = {
            "injuries": [],
            "symptoms": []
        }

        if self.clinical_service:

            try:

                clinical_results = (
                    self.clinical_service.analyze(text)
                )

            except Exception as e:

                print(
                    f"Clinical NLP Error: {e}"
                )

        injuries = clinical_results.get(
            "injuries",
            []
        )

        symptoms = clinical_results.get(
            "symptoms",
            []
        )

        for injury in injuries:

            if injury in self.CLINICAL_INJURY_SCORE:

                severity_score = max(
                    severity_score,
                    self.CLINICAL_INJURY_SCORE[injury]
                )

        severity_score = min(
            severity_score,
            100
        )

        return {

            "score":
            round(
                severity_score,
                2
            ),

            "keywords":

            (
                high_matches
                +
                medium_matches
                +
                low_matches
            ),

            "clinical_injuries":
            injuries,

            "symptoms":
            symptoms,

            "suggested_level":

            self._get_level(
                severity_score
            ),

            "explanation":

            self._generate_explanation(

                severity_score,

                injuries

            )
        }

    def _calculate_score(
        self,
        level
    ):

        matches = []

        total = 0

        for keyword, weight in (
            self.SEVERITY_KEYWORDS[level]
            .items()
        ):

            if keyword in self.text:

                matches.append(
                    keyword
                )

                total = max(
                    total,
                    weight
                )

        return total, matches

    def _get_level(
        self,
        score
    ):

        if score >= 75:

            return "red"

        elif score >= 40:

            return "yellow"

        return "green"

    def _generate_explanation(

        self,

        score,

        injuries

    ):

        if injuries:

            return (
                "Clinical findings: "
                +
                ", ".join(
                    injuries
                )
            )

        if score >= 75:

            return (
                "Critical condition detected"
            )

        elif score >= 40:

            return (
                "Moderate severity"
            )

        return (
            "Low severity"
        )