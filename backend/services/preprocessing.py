"""Shared, train-fitted preprocessing for inference and transformation previews."""
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler, KBinsDiscretizer

CHOICES = {'Impute Median', 'Impute Mean', 'One-Hot Encoding', 'Standard Scaling', 'Keep Raw', 'Discretize Binning'}

def build_preprocessor(frame, decisions=None, method='Median'):
    decisions = decisions or {}
    transforms = []
    # KNN must see multiple numeric features to find meaningful neighbors.
    knn_columns = [column for column in frame.columns if pd.api.types.is_numeric_dtype(frame[column]) and decisions.get(column) not in {'Impute Mean', 'Impute Median'}] if method == 'KNN' else []
    if knn_columns:
        after_imputation = []
        for index, column in enumerate(knn_columns):
            choice = decisions.get(column, 'Standard Scaling')
            if choice not in CHOICES: raise ValueError(f'Unsupported transformation: {choice}')
            transform = StandardScaler() if choice == 'Standard Scaling' else KBinsDiscretizer(n_bins=4, encode='ordinal', strategy='quantile') if choice == 'Discretize Binning' else OneHotEncoder(handle_unknown='ignore', sparse_output=False, max_categories=32) if choice == 'One-Hot Encoding' else 'passthrough'
            after_imputation.append((f'column{index}', transform, [index]))
        transforms.append(('numeric_knn', Pipeline([('impute', KNNImputer(n_neighbors=5, keep_empty_features=True)), ('transform', ColumnTransformer(after_imputation, verbose_feature_names_out=False))]), knn_columns))
    for index, column in enumerate(frame.columns):
        if column in knn_columns: continue
        numeric = pd.api.types.is_numeric_dtype(frame[column])
        choice = decisions.get(column, 'Standard Scaling' if numeric else 'One-Hot Encoding')
        if choice not in CHOICES:
            raise ValueError(f'Unsupported transformation: {choice}')
        steps = []
        if numeric:
            if method == 'KNN' and choice not in {'Impute Mean', 'Impute Median'}:
                imputer = KNNImputer(n_neighbors=5, keep_empty_features=True)
            else:
                strategy = 'mean' if choice == 'Impute Mean' else 'median' if choice == 'Impute Median' else 'mean' if method == 'Mean' else 'most_frequent' if method == 'Mode' else 'median'
                imputer = SimpleImputer(strategy=strategy, keep_empty_features=True)
            steps.append(('impute', imputer))
            if choice == 'Standard Scaling': steps.append(('scale', StandardScaler()))
            if choice == 'Discretize Binning': steps.append(('bin', KBinsDiscretizer(n_bins=4, encode='ordinal', strategy='quantile')))
            if choice == 'One-Hot Encoding': steps.append(('encode', OneHotEncoder(handle_unknown='ignore', sparse_output=False, max_categories=32)))
        else:
            steps.append(('impute', SimpleImputer(strategy='most_frequent', keep_empty_features=True)))
            if choice == 'One-Hot Encoding':
                steps.append(('encode', OneHotEncoder(handle_unknown='ignore', sparse_output=False, max_categories=32)))
            else:
                steps.append(('encode', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)))
                if choice == 'Standard Scaling': steps.append(('scale', StandardScaler()))
        transforms.append((f'feature{index}', Pipeline(steps), [column]))
    return ColumnTransformer(transforms, verbose_feature_names_out=False)

def clean_frame(frame):
    frame = frame.copy().replace([np.inf, -np.inf], np.nan)
    for column in frame.select_dtypes(exclude=np.number):
        frame[column] = frame[column].map(lambda value: str(value) if pd.notna(value) else np.nan)
    return frame

def transformed_preview(frame, target, decisions):
    features = clean_frame(frame.drop(columns=[target]))
    preprocessor = build_preprocessor(features, decisions)
    values = preprocessor.fit_transform(features)
    output = pd.DataFrame(values, columns=preprocessor.get_feature_names_out(), index=frame.index)
    output[target] = frame[target]
    return output
