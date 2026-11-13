"""Computation-only training implementation, imported only by sandbox operations."""
import io
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score, mean_squared_error
from services.preprocessing import build_preprocessor, clean_frame
from pipeline.kafka_worker import EncodedClassifier
import optuna

def train(data, config, storage):
    target, problem_type = config['target'], config['problem_type']
    imputation_method = config.get('imputation_method', 'Median')
    choices = config.get('choices', {})
    project_id = 'sandbox'
    events = []
    def record_comparison(comparison):
        event = {'event': 'candidate_progress', 'models': {name: dict(value) for name, value in comparison.items()}}
        events.append(event)
        print(json.dumps(event), flush=True)
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
    from services.model_search import model_factories, TRIALS_PER_MODEL
    factories = model_factories(classification)
    comparison = {name: {'status': 'Idle', 'metric': None} for name in factories}
    record_comparison(comparison)
    trained = {}
    trials = []
    for name, factory in factories.items():
        comparison[name] = {'status': 'Training', 'phase': 'Optimizing', 'metric': None}
        record_comparison(comparison)
        try:
            def objective(trial):
                fitted = pipeline(factory(trial)).fit(X_fit, y_fit)
                return metric(y_val, fitted.predict(X_val))
            study = optuna.create_study(direction='maximize' if classification else 'minimize', sampler=optuna.samplers.TPESampler(seed=42))
            study.optimize(objective, n_trials=TRIALS_PER_MODEL)
            for trial in study.trials:
                trials.append({'trial': len(trials)+1, 'model': name, 'params': trial.params,
                    'f1': trial.value, 'metric_name': 'Weighted F1' if classification else 'MSE',
                    'status': 'Completed (Best)' if trial.number == study.best_trial.number else 'Completed'})
            fitted = pipeline(factory(study.best_trial)).fit(X_train, y_train)
            predictions = fitted.predict(X_test)
            score = metric(y_test, predictions)
            model_path = storage.upload_model(project_id, name.lower().replace(' ', '_'), pickle.dumps(fitted))
            comparison[name] = {'status': 'Trained', 'metric': score, 'validation_metric': study.best_value,
                'best_params': study.best_params, 'hpo_trials': len(study.trials), 'artifact_path': model_path,
                'accuracy': float(accuracy_score(y_test, predictions)) if classification else None}
            trained[name] = fitted
        except Exception as error:
            comparison[name] = {'status': 'Failed', 'metric': None, 'error': str(error)}
        record_comparison(comparison)
    if not trained: raise ValueError('All candidate models failed to train')
    champion_name = (max if classification else min)(trained, key=lambda name: comparison[name]['validation_metric'])
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
        if isinstance(values, list): values = np.stack(values, axis=-1)
        values = np.asarray(values)
        if values.ndim == 3:
            global_values = np.abs(values).mean(axis=(0, 2))
            class_index = int(champion.predict_proba(X_test.head(1))[0].argmax())
            values = values[:, :, class_index]
        else:
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
    selection = {'selected_model': champion_name, 'basis': 'validation', 'metric': 'weighted F1' if classification else 'MSE', 'direction': 'maximize' if classification else 'minimize', 'validation_score': comparison[champion_name]['validation_metric'], 'test_score': comparison[champion_name]['metric'], 'reason': f"Selected {champion_name} by {'highest validation weighted F1' if classification else 'lowest validation MSE'}; held-out test scores did not determine selection."}
    events.append({'event': 'champion_selected', **selection})
    return {'execution_log': events, 'model_selection': selection, 'best_model': champion_name, 'best_f1': score if classification else None, 'best_mse': None if classification else score, 'best_accuracy': comparison[champion_name]['accuracy'], 'trials_run': len(trained), 'hpo_trials': trials, 'top_features': [item['feature'] for item in global_importance[:8]], 'shap_global': global_importance, 'shap_local': local, 'model_path': comparison[champion_name]['artifact_path'], 'models_comparison': comparison}
