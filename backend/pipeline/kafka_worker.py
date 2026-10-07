"""Database-worker training pipeline. No synthetic data or fabricated metrics."""
import io
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score, mean_squared_error
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from services.preprocessing import build_preprocessor, clean_frame

class EncodedClassifier(ClassifierMixin, BaseEstimator):
    def __init__(self, estimator): self.estimator = estimator
    def fit(self, X, y):
        self.encoder_ = LabelEncoder().fit(y)
        self.classes_ = self.encoder_.classes_
        self.estimator.fit(X, self.encoder_.transform(y))
        return self
    def predict(self, X): return self.encoder_.inverse_transform(self.estimator.predict(X).astype(int))
    def predict_proba(self, X): return self.estimator.predict_proba(X)

class TrainingWorker:
    def __init__(self, db_session_maker=None): self.db_session_maker = db_session_maker
    def update_models_comparison_db(self, project_id, comparison):
        from database.models import KnowledgeCard
        with self.db_session_maker() as db:
            card = db.query(KnowledgeCard).filter_by(project_id=project_id).first()
            if card:
                card.models_comparison_json = comparison.copy()
                db.commit()

    def process_training_job(self, project_id, target, problem_type, imputation_method='Median', features_override=None):
        from database.models import Project, DecisionMemory
        from services.storage.factory import get_storage_provider
        import optuna
        storage = get_storage_provider()
        with self.db_session_maker() as db:
            project = db.query(Project).filter_by(id=project_id).first()
            if not project or not project.dataset_path: raise ValueError('Uploaded dataset is missing')
            data = storage.download_file(project.dataset_path)
            choices = {d.feature_name: d.user_choice if d.override_active else d.decision for d in db.query(DecisionMemory).filter_by(project_id=project_id).all()}
        frame = clean_frame(pd.read_csv(io.BytesIO(data)))
        if target not in frame: raise ValueError(f'Target column {target} is missing')
        frame = frame.dropna(subset=[target])
        if len(frame) < 12: raise ValueError('Training requires at least 12 rows with non-missing targets')
        X, y = frame.drop(columns=[target]), frame[target]
        classification = problem_type == 'classification'
        if X.shape[1] == 0: raise ValueError('Training requires at least one predictor')
        stratify = None
        if classification:
            counts = y.value_counts()
            if len(counts) < 2 or counts.min() < 3: raise ValueError('Classification requires at least 3 rows in every class')
            stratify = y
        # Separate untouched test data from the validation rows used for hyperparameter search.
        test_size = max(.2, y.nunique()/len(y)) if classification else .2
        if test_size > .4: raise ValueError('Too many classes for this dataset size')
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42, stratify=stratify)
        X_fit, X_val, y_fit, y_val = train_test_split(X_train, y_train, test_size=max(.25, y_train.nunique()/len(y_train)) if classification else .25, random_state=43, stratify=y_train if classification else None)
        def metric(actual, predictions):
            return float(f1_score(actual, predictions, average='weighted', zero_division=0)) if classification else float(mean_squared_error(actual, predictions))
        def pipeline(estimator):
            if classification: estimator = EncodedClassifier(estimator)
            return Pipeline([('preprocess', build_preprocessor(X_train, choices, imputation_method)), ('model', estimator)])
        forest = RandomForestClassifier if classification else RandomForestRegressor
        def objective(trial):
            estimator = forest(n_estimators=trial.suggest_int('n_estimators', 30, 80), max_depth=trial.suggest_int('max_depth', 3, 10), random_state=42, n_jobs=2)
            fitted = pipeline(estimator).fit(X_fit, y_fit)
            return metric(y_val, fitted.predict(X_val))
        study = optuna.create_study(direction='maximize' if classification else 'minimize', sampler=optuna.samplers.TPESampler(seed=42))
        study.optimize(objective, n_trials=3)
        candidates = {'Random Forest': forest(**study.best_params, random_state=42, n_jobs=2)}
        try:
            import xgboost as xgb
            candidates['XGBoost'] = (xgb.XGBClassifier if classification else xgb.XGBRegressor)(n_estimators=60, max_depth=4, random_state=42, n_jobs=2)
        except ImportError: pass
        try:
            import lightgbm as lgb
            candidates['LightGBM'] = (lgb.LGBMClassifier if classification else lgb.LGBMRegressor)(n_estimators=60, max_depth=4, random_state=42, n_jobs=2, verbosity=-1)
        except ImportError: pass
        candidates['Neural Network'] = (MLPClassifier if classification else MLPRegressor)(hidden_layer_sizes=(32,16), max_iter=120, random_state=42)
        comparison = {name: {'status': 'Idle', 'metric': None} for name in candidates}
        self.update_models_comparison_db(project_id, comparison)
        trained = {}
        for name, estimator in candidates.items():
            comparison[name] = {'status': 'Training', 'metric': None}
            self.update_models_comparison_db(project_id, comparison)
            try:
                fitted = pipeline(estimator).fit(X_train, y_train)
                predictions = fitted.predict(X_test)
                score = metric(y_test, predictions)
                model_path = storage.upload_model(project_id, name.lower().replace(' ', '_'), pickle.dumps(fitted))
                comparison[name] = {'status': 'Trained', 'metric': score, 'artifact_path': model_path, 'accuracy': float(accuracy_score(y_test, predictions)) if classification else None}
                trained[name] = fitted
            except Exception as error:
                comparison[name] = {'status': 'Failed', 'metric': None, 'error': str(error)}
            self.update_models_comparison_db(project_id, comparison)
        if not trained: raise ValueError('All candidate models failed to train')
        champion_name = (max if classification else min)(trained, key=lambda name: comparison[name]['metric'])
        champion = trained[champion_name]
        preprocessing = champion.named_steps['preprocess']
        encoded = preprocessing.transform(X_test.head(30))
        names = preprocessing.get_feature_names_out().tolist()
        wrapped = champion.named_steps['model']
        estimator = wrapped.estimator if classification else wrapped
        explanation_method = 'SHAP'
        local_drivers = []
        try:
            import shap
            if not hasattr(estimator, 'feature_importances_'): raise ValueError('Tree SHAP unavailable for this estimator')
            explainer = shap.TreeExplainer(estimator)
            values = explainer.shap_values(encoded)
            if isinstance(values, list): values = values[-1]
            values = np.asarray(values)
            if values.ndim == 3: values = values[:, :, -1]
            global_values = np.abs(values).mean(axis=0)
            for index in np.argsort(np.abs(values[0]))[::-1][:8]:
                local_drivers.append({'feature': names[index], 'value': str(round(float(encoded[0,index]),4)), 'impact': f'{float(values[0,index]):+.4f} SHAP'})
        except Exception:
            from sklearn.inspection import permutation_importance
            result = permutation_importance(estimator, encoded, wrapped.encoder_.transform(y_test.head(30)) if classification else y_test.head(30), n_repeats=3, random_state=42)
            global_values = np.maximum(result.importances_mean, 0)
            explanation_method = 'Permutation importance'
        global_importance = sorted([{'feature': name, 'shap': float(value), 'type': explanation_method} for name,value in zip(names, global_values)], key=lambda item:item['shap'], reverse=True)
        row = X_test.head(1)
        prediction = champion.predict(row)[0]
        probability = float(champion.predict_proba(row)[0].max()) if classification else None
        local = {'customerId': str(row.index[0]), 'prediction': str(prediction), 'probability': probability, 'risk': f'Predicted class: {prediction}' if classification else f'Predicted value: {float(prediction):.4f}', 'drivers': local_drivers, 'explanation_method': explanation_method}
        score = comparison[champion_name]['metric']
        trials = [{'trial': trial.number+1, 'params': trial.params, 'f1': trial.value, 'status': 'Completed (Best)' if trial.number == study.best_trial.number else 'Completed'} for trial in study.trials]
        return {'best_model': champion_name, 'best_f1': score if classification else None, 'best_mse': None if classification else score, 'best_accuracy': comparison[champion_name]['accuracy'], 'trials_run': len(trained), 'hpo_trials': trials, 'top_features': [item['feature'] for item in global_importance[:8]], 'shap_global': global_importance, 'shap_local': local, 'model_path': comparison[champion_name]['artifact_path'], 'models_comparison': comparison}
