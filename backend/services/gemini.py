import os
import json
from google import genai

# Fallback mock answers for robust local-first execution without active API keys
MOCK_UNDERSTANDING = {
    "problem_type": "classification",
    "target_variable": "churn",
    "business_goal": "Identify customers likely to terminate subscription services to target with retention promotions.",
    "recommended_metrics": ["f1_score", "accuracy", "roc_auc"],
    "suggested_models": ["XGBoost", "LightGBM", "Random Forest"]
}

class GeminiService:
    def __init__(self):
        # Configure SDK key if available in env
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            self.client = genai.Client(api_key=api_key)
            self.client_enabled = True
        else:
            self.client_enabled = False

    def understand_project(self, name: str, description: str, target: str) -> dict:
        """
        Uses Gemini to parse business descriptions and suggest problem type, goals and model targets.
        """
        if not self.client_enabled:
            return MOCK_UNDERSTANDING

        try:
            prompt = f"""
            You are an expert AI Data Science Assistant.
            Analyze the following project setup details:
            Project Name: {name}
            Target Column: {target}
            Description: {description}
            
            Return a JSON object containing:
            1. "problem_type" (either "classification" or "regression")
            2. "target_variable" (the target column parameter)
            3. "business_goal" (summarized project goal description)
            4. "recommended_metrics" (array of metrics: f1_score, accuracy, rmse, mae, r2)
            5. "suggested_models" (array of machine learning models suitable for this type of task)
            
            Do not wrap in markdown syntax. Return raw JSON string.
            """
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return json.loads(response.text.strip())
        except Exception as e:
            print(f"Gemini API Error in understand_project: {e}")
            return MOCK_UNDERSTANDING

    def assistant_chat(self, question: str, knowledge_card: dict, timeline: list) -> str:
        """
        Converse with user using LangGraph grounding concept based on active project state.
        """
        if not self.client_enabled:
            # simple mock chatbot rules if API key not present
            q = question.lower()
            if "xgboost" in q:
                return "XGBoost was chosen as champion model based on HPO validations. It achieves 0.91 F1 compared to 0.86 for Random Forest."
            return f"Understood query. Current active model is {knowledge_card.get('best_model', 'None')} with validation score of {knowledge_card.get('best_f1', 'N/A')}."

        try:
            context = f"""
            You are a project-aware AI Data Science Companion.
            Here is the active project's Knowledge Card context:
            {json.dumps(knowledge_card, indent=2)}
            
            Here are recent project timeline logs:
            {json.dumps(timeline, indent=2)}
            
            Answer the user's question accurately using ONLY this project context.
            User Question: {question}
            """
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=context
            )
            return response.text.strip()
        except Exception as e:
            return f"Error interacting with Gemini API: {e}"
