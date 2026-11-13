"""Fixed operation registry. No shell commands or generated Python are accepted."""
import io
import os
import pickle
import socket
import numpy as np
import pandas as pd
from services.preprocessing import clean_frame, transformed_preview

def predict(payload, files):
    model = pickle.loads(files['model.pkl'])
    required = model.named_steps['preprocess'].feature_names_in_.tolist()
    frame = pd.DataFrame(payload['rows'])
    missing = set(required) - set(frame.columns)
    if missing: raise ValueError('Missing columns: ' + ', '.join(sorted(missing)))
    try:
        frame = clean_frame(frame[required])
        predictions = model.predict(frame).tolist()
        result = {'predictions': predictions, 'target': payload['target']}
        if payload['problem_type'] == 'classification':
            result['probabilities'] = model.predict_proba(frame).tolist()
            result['classes'] = model.named_steps['model'].classes_.tolist()
        return result
    except (ValueError, TypeError) as error:
        raise ValueError(str(error))


def explain(payload, files):
    row_index = payload['row_index']
    frame = clean_frame(pd.read_csv(io.BytesIO(files['dataset.csv'])))
    if row_index < 0 or row_index >= len(frame): raise ValueError('Row index is outside the dataset')
    model = pickle.loads(files['model.pkl'])
    row = frame.drop(columns=[payload['target']]).iloc[[row_index]]
    preprocessing = model.named_steps['preprocess']
    values = preprocessing.transform(row)
    names = preprocessing.get_feature_names_out().tolist()
    classification = payload['problem_type'] == 'classification'
    wrapped = model.named_steps['model']
    estimator = wrapped.estimator if classification else wrapped
    prediction = model.predict(row)[0]
    drivers = []
    method = 'Local SHAP unavailable for this model'
    try:
        import shap
        if hasattr(estimator, 'feature_importances_'):
            explanation = shap.TreeExplainer(estimator).shap_values(values)
            method = 'SHAP'
        else:
            if values.shape[1] > 128: raise ValueError('Too many transformed features for interactive permutation SHAP')
            background = preprocessing.transform(frame.drop(columns=[payload['target']]).head(20))
            explainer = shap.Explainer(estimator.predict_proba if classification else estimator.predict,
                                      background, algorithm='permutation', seed=42)
            explanation = explainer(values, max_evals=max(2 * values.shape[1] + 1, 20)).values
            method = 'Permutation SHAP'
        class_index = int(wrapped.encoder_.transform([prediction])[0]) if classification else 0
        if isinstance(explanation, list): explanation = explanation[class_index]
        explanation = np.asarray(explanation)
        if explanation.ndim == 3: explanation = explanation[:, :, class_index]
        for index in np.argsort(np.abs(explanation[0]))[::-1][:8]:
            drivers.append({'feature': names[index], 'value': str(round(float(values[0,index]), 4)), 'impact': f'{float(explanation[0,index]):+.4f} SHAP'})
    except Exception:
        pass
    return {'customerId': str(row_index), 'prediction': str(prediction), 'probability': float(model.predict_proba(row)[0].max()) if classification else None, 'risk': f'Predicted class: {prediction}' if classification else f'Predicted value: {float(prediction):.4f}', 'drivers': drivers, 'explanation_method': method}


def champion(payload, files):
    model = pickle.loads(files['model.pkl'])
    preprocessor = model.named_steps['preprocess']
    wrapped = model.named_steps['model']
    estimator = wrapped.estimator if payload['problem_type'] == 'classification' else wrapped
    names = preprocessor.get_feature_names_out()
    importance = getattr(estimator, 'feature_importances_', None)
    method = 'Native feature importance'
    if importance is None:
        from sklearn.inspection import permutation_importance
        frame = clean_frame(pd.read_csv(io.BytesIO(files['dataset.csv']))).dropna(subset=[payload['target']]).head(30)
        features = preprocessor.transform(frame.drop(columns=[payload['target']]))
        target = wrapped.encoder_.transform(frame[payload['target']]) if payload['problem_type'] == 'classification' else frame[payload['target']]
        importance = np.maximum(permutation_importance(estimator, features, target, n_repeats=2, random_state=42).importances_mean, 0)
        method = 'Permutation importance'
    global_importance = sorted([{'feature': name, 'shap': float(value), 'type': method} for name, value in zip(names, importance)], key=lambda item: item['shap'], reverse=True)
    return {'shap_global': global_importance, 'top_features': [item['feature'] for item in global_importance[:8]]}

def monitor(payload, files):
    current = clean_frame(pd.read_csv(io.BytesIO(files['current.csv'])))
    baseline = clean_frame(pd.read_csv(io.BytesIO(files['dataset.csv'])))
    if current.empty or len(current) > 100000:
        raise ValueError('Provide between 1 and 100000 rows')
    if not set(baseline.columns.drop(payload['target'])).issubset(current.columns):
        raise ValueError('Monitoring data must contain all predictor columns')
    columns = baseline.columns.drop(payload['target'])
    features = []
    for column in columns:
        before, after = baseline[column], current[column]
        if pd.api.types.is_numeric_dtype(before):
            edges = np.unique(np.quantile(before.dropna(), np.linspace(0, 1, 11))) if before.notna().any() else np.array([0])
            edges = np.concatenate(([-np.inf], edges[1:-1], [np.inf]))
            expected = np.append(np.histogram(before.dropna(), edges)[0], before.isna().sum()) / len(before)
            actual = np.append(np.histogram(pd.to_numeric(after, errors='coerce').dropna(), edges)[0], after.isna().sum()) / len(after)
        else:
            labels = list(set(before.fillna('__missing__')) | set(after.fillna('__missing__')))
            expected = before.fillna('__missing__').value_counts(normalize=True).reindex(labels, fill_value=0).to_numpy()
            actual = after.fillna('__missing__').value_counts(normalize=True).reindex(labels, fill_value=0).to_numpy()
        expected, actual = np.clip(expected, .0001, 1), np.clip(actual, .0001, 1)
        psi = float(np.sum((actual-expected)*np.log(actual/expected)))
        features.append({'feature': column, 'psi': round(psi, 4)})
    maximum = max((item['psi'] for item in features), default=0)
    result = {'driftPsi': maximum, 'driftStatus': 'DRIFT DETECTED' if maximum > .2 else 'HEALTHY', 'features': features, 'rows': len(current), 'driftAlerts': [{'feature': item['feature'], 'message': f"PSI {item['psi']:.4f} exceeds 0.20", 'severity': 'warning'} for item in features if item['psi'] > .2]}
    return result

def apply_imputation(df, method: str):
    import numpy as np
    from sklearn.impute import SimpleImputer, KNNImputer
    if method not in {'Median', 'Mean', 'Mode', 'KNN'}:
        raise ValueError('Unsupported imputation method')
    output = df.copy().replace([np.inf, -np.inf], np.nan)
    numeric = output.select_dtypes(include=np.number).columns.tolist()
    if numeric:
        imputer = KNNImputer(n_neighbors=5, keep_empty_features=True) if method == 'KNN' else SimpleImputer(strategy={'Median':'median', 'Mean':'mean', 'Mode':'most_frequent'}[method], keep_empty_features=True)
        output[numeric] = imputer.fit_transform(output[numeric])
    for column in output.columns.difference(numeric):
        mode = output[column].mode()
        output[column] = output[column].fillna(mode.iloc[0] if len(mode) else 'Missing')
    return output


class ArtifactSink:
    def __init__(self):
        self.artifacts = {}

    def upload_model(self, project_id, model_type, content):
        name = model_type + '.pkl'
        self.artifacts[name] = content
        return name


def execute(operation, payload, files):
    if operation == 'train':
        from sandbox.training import train
        sink = ArtifactSink()
        return train(files['dataset.csv'], payload, sink), sink.artifacts
    if operation in {'predict', 'explain', 'champion', 'monitor'}:
        function = {'predict': predict, 'explain': explain, 'champion': champion, 'monitor': monitor}[operation]
        return function(payload, files), {}
    if operation == 'profile':
        from services.dataset import DatasetService
        return DatasetService._profile_dataset(files['dataset.csv'], payload['target'], payload.get('problem_type', 'auto')), {}
    if operation == 'validate_csv':
        pd.read_csv(io.BytesIO(files['dataset.csv']), nrows=50)
        return {'valid': True}, {}
    if operation == 'impute':
        frame = pd.read_csv(io.BytesIO(files['dataset.csv']))
        target = frame[payload['target']].copy()
        output = apply_imputation(frame.drop(columns=[payload['target']]), payload['method'])
        output[payload['target']] = target
        return {}, {'dataset.csv': output.to_csv(index=False).encode()}
    if operation == 'transform':
        frame = pd.read_csv(io.BytesIO(files['dataset.csv']))
        feature, target_name = payload['feature'], payload['target']
        if feature == target_name or feature not in frame:
            raise ValueError('Choose a predictor column, not the target')
        preview = transformed_preview(frame, target_name, payload['choices'])
        def numeric(series):
            return pd.to_numeric(series, errors='coerce') if pd.api.types.is_numeric_dtype(series) else pd.Series(pd.factorize(series)[0], index=series.index)
        target = numeric(frame[target_name])
        before = numeric(frame[feature]).corr(target)
        after_columns = [column for column in preview if column == feature or column.startswith(feature + '_')]
        after_values = [abs(numeric(preview[column]).corr(target)) for column in after_columns]
        before = float(abs(before)) if pd.notna(before) else 0.0
        after = max((float(value) for value in after_values if pd.notna(value)), default=0.0)
        missing_before = int(frame[feature].isna().sum())
        missing_after = int(preview[after_columns].isna().sum().sum())
        comparison = {'before_corr': round(before, 4), 'after_corr': round(after, 4), 'improvement': round(after-before, 4), 'before_missing': missing_before, 'after_missing': missing_after, 'better': bool(after-before > .001 or missing_after < missing_before)}
        return comparison, {'dataset.csv': preview.to_csv(index=False).encode()}
    if operation == 'probe':
        # Fixed diagnostic actions used by security integration tests, never arbitrary code.
        from pathlib import Path
        import time
        time.sleep(min(float(payload.get('sleep_seconds', 0)), 10))
        marker = Path('/tmp/aidso-marker')
        prior_marker = marker.exists()
        marker.write_text('temporary')
        readonly = False
        try:
            Path('/opt/aidso/forbidden').write_text('test')
        except OSError:
            readonly = True
        network_blocked = False
        try:
            socket.create_connection(('1.1.1.1', 443), timeout=.2).close()
        except OSError:
            network_blocked = True
        return {'uid': os.getuid(), 'environment_keys': sorted(os.environ), 'prior_marker': prior_marker,
                'read_only_root': readonly, 'network_blocked': network_blocked,
                'working_directory': os.getcwd(), 'status': Path('/proc/self/status').read_text()}, {}
    raise ValueError('Unsupported sandbox operation')


