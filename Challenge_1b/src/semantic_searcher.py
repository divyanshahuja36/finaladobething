from sentence_transformers import SentenceTransformer, util
import re

# --- Configuration for Intelligent Ranking ---

# Titles that are generic and should be down-weighted.
PENALIZED_TITLES = {
    "introduction", "conclusion", "summary", "preface", "contents",
    "table of contents", "abstract", "foreword", "epilogue"
}

# Keywords that indicate actionable or highly relevant content for different personas.
# This makes the ranking persona-aware.
ACTIONABLE_KEYWORD_BOOSTS = {
    "Travel Planner": {
        "keywords": [
            "hotel", "restaurant", "budget", "itinerary", "plan", "schedule",
            "activities", "packing", "tips", "things to do", "nightlife",
            "accommodation", "attractions", "transportation", "booking", "tour",
            "guide", "travel", "destination", "sightseeing", "flights"
        ],
        "boost_factor": 1.25
    },
    "Food Contractor": {
        "keywords": [
            "menu", "recipe", "ingredient", "catering", "food", "cuisine", "cooking",
            "restaurant", "chef", "kitchen", "dining", "meal", "service", "nutrition",
            "preparation", "contract", "supplier", "procurement", "cost", "quality"
        ],
        "boost_factor": 1.3
    },
    "HR Professional": {
        "keywords": [
            "employee", "policy", "compliance", "recruitment", "hiring", "performance",
            "training", "onboarding", "benefits", "payroll", "management", "staff",
            "workplace", "procedures", "regulations", "human resources", "personnel",
            "development", "evaluation", "compensation"
        ],
        "boost_factor": 1.2
    },
    "Researcher": {
        "keywords": [
            "methodology", "methods", "results", "findings", "data", "analysis",
            "study", "experiment", "conclusion", "discussion"
        ],
        "boost_factor": 1.3
    }
}


class SemanticSearcher:
    """
    A class to handle semantic search with multi-factor intelligent ranking.
    """

    def __init__(self, model_path: str):
        """
        Initializes the SemanticSearcher by loading a pre-trained model.
        """
        try:
            self.model = SentenceTransformer(model_path)
        except Exception as e:
            print(f"Error loading model from {model_path}: {e}")
            raise

    def get_final_score(self, base_score: float, section_title: str, persona: str) -> float:
        """
        Calculates a final, adjusted score by applying penalties and boosts.
        """
        final_score = base_score
        title_lower = section_title.lower().strip()

        # 1. Apply Penalty for generic titles
        if title_lower in PENALIZED_TITLES:
            # Researchers might find value in conclusions, so we make the penalty conditional
            if not (persona == "Researcher" and title_lower == "conclusion"):
                final_score *= 0.70  # Reduce score by 30% for generic titles

        # 2. Apply Boost for actionable keywords based on persona
        best_match_persona = None
        for key in ACTIONABLE_KEYWORD_BOOSTS:
            if key.lower() in persona.lower():
                best_match_persona = key
                break

        if best_match_persona:
            persona_config = ACTIONABLE_KEYWORD_BOOSTS[best_match_persona]
            boost_factor = persona_config["boost_factor"]
            keywords = persona_config["keywords"]

            for keyword in keywords:
                # Use regex for whole word matching to avoid partial matches (e.g., 'plan' in 'planet')
                if re.search(r'\b' + re.escape(keyword) + r'\b', title_lower):
                    final_score *= boost_factor
                    break  # Apply boost only once per title

        return final_score

    def rank_chunks(self, query: str, chunks: list[dict], persona: str) -> list[dict]:
        """
        Ranks text chunks using a combination of semantic similarity and rule-based
        scoring for persona-specific relevance.
        """
        if not chunks:
            return []

        query_embedding = self.model.encode(query, convert_to_tensor=True)
        chunk_texts = [chunk['text'] for chunk in chunks]
        chunk_embeddings = self.model.encode(
            chunk_texts, convert_to_tensor=True)

        cosine_scores = util.cos_sim(query_embedding, chunk_embeddings)[0]

        for i, chunk in enumerate(chunks):
            base_score = cosine_scores[i].item()
            section_title = chunk.get("section_title", "")

            # Calculate the final, intelligent score
            final_score = self.get_final_score(
                base_score, section_title, persona)

            # For debugging if needed
            chunk['base_similarity_score'] = base_score
            chunk['final_score'] = final_score

        # Sort by the new, more intelligent final_score
        ranked_chunks = sorted(
            chunks, key=lambda x: x['final_score'], reverse=True)

        # Assign importance_rank based on the new order
        for i, chunk in enumerate(ranked_chunks):
            chunk['importance_rank'] = i + 1

        return ranked_chunks
