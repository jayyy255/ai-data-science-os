import os
import json
from google import genai

class GeminiService:
    def __init__(self):
        # Configure SDK key from env, prioritizing /app/.env file values to bypass Docker Compose overrides
        env_path = "/app/.env"
        if os.path.exists(env_path):
            try:
                with open(env_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            if k.strip() == "GEMINI_API_KEY":
                                os.environ["GEMINI_API_KEY"] = v.strip()
            except Exception as env_err:
                print(f"Failed to load /app/.env manually: {env_err}")

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
            return {'problem_type': 'classification', 'target_variable': target, 'business_goal': description or name, 'recommended_metrics': ['f1_score', 'accuracy'], 'suggested_models': ['Random Forest', 'XGBoost', 'LightGBM', 'Neural Network']}

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
            return {'problem_type': 'classification', 'target_variable': target, 'business_goal': description or name, 'recommended_metrics': ['f1_score', 'accuracy'], 'suggested_models': ['Random Forest', 'XGBoost', 'LightGBM', 'Neural Network']}

    def analyze_eda_profile(self, name: str, eda_profile: dict) -> str:
        """
        Uses Gemini (gemini-2.5-flash) to write a dynamic data scientist summary audit of the EDA profile.
        """
        if not self.client_enabled:
            return f"Dataset Profile Summary for '{name}': Computed {eda_profile.get('rows_count')} rows across {eda_profile.get('columns_count')} features. Numerical features: {eda_profile.get('numerical_count')}, Categorical: {eda_profile.get('categorical_count')}. Missing value rate is {round(eda_profile.get('missing_pct', 0), 2)}%."

        try:
            prompt = f"""
            You are an expert Data Scientist.
            Analyze the following statistical profile of the dataset:
            Project/Dataset Name: {name}
            Total Rows: {eda_profile.get('rows_count')}
            Total Columns: {eda_profile.get('columns_count')}
            Missing Cells Pct: {eda_profile.get('missing_pct')}%
            Numerical Columns Count: {eda_profile.get('numerical_count')}
            Categorical Columns Count: {eda_profile.get('categorical_count')}
            Imbalance Warning: {eda_profile.get('is_imbalanced')}
            
            Write a concise, professional 3-4 sentence dataset assessment report. Highlight any data quality concerns, distribution balances, missing value density, and what steps should be taken (e.g. scaling, encoding, imputation). Make it descriptive and grounded.
            """
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            print(f"Gemini API Error in analyze_eda_profile: {e}")
            return f"Dataset Profile Summary for '{name}': Computed {eda_profile.get('rows_count')} rows across {eda_profile.get('columns_count')} features. Missing rate is {round(eda_profile.get('missing_pct', 0), 2)}%."

    def assistant_chat(self, question: str, knowledge_card: dict, timeline: list) -> str:
        """
        Converse with user using LangGraph grounding concept based on active project state.
        """
        if not self.client_enabled:
            model = knowledge_card.get('best_model') or 'None'
            return ("Gemini is not configured. Here is the current project context: "
                    f"{knowledge_card.get('rows_count', 0)} rows, {knowledge_card.get('columns_count', 0)} columns; "
                    f"status: {knowledge_card.get('status')}; champion: {model}; "
                    f"F1: {knowledge_card.get('best_f1')}; MSE: {knowledge_card.get('best_mse')}. "
                    f"Preprocessing: {json.dumps(knowledge_card.get('decisions', []))}. "
                    "Configure GEMINI_API_KEY on the server for conversational explanations.")

        try:
            context = f"""
            You are a project-aware Data Science Companion.
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
            err_msg = str(e)
            # Log precise diagnostics on the server side (visible to us in container logs/CLI)
            print(f"DIAGNOSTIC ERROR - Gemini API Key Issue: {err_msg}")
            
            # Return generic friendly fallback to the client
            return "Sorry for the inconvenience, the chat is unavailable right now. It shall be back shortly."
