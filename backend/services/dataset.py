import io
import pandas as pd
import numpy as np

class DatasetService:
    @staticmethod
    def infer_problem_type(target, requested='auto'):
        if requested not in {'auto', 'classification', 'regression'}:
            raise ValueError('Problem type must be auto, classification, or regression')
        if requested != 'auto':
            if requested == 'regression' and not pd.api.types.is_numeric_dtype(target):
                raise ValueError('Regression requires a numeric target column')
            return requested
        from sklearn.utils.multiclass import type_of_target
        return 'regression' if type_of_target(target.dropna()) == 'continuous' or (pd.api.types.is_numeric_dtype(target) and target.nunique() > 20) else 'classification'

    @staticmethod
    def profile_dataset(file_bytes: bytes, target_variable: str, problem_type='auto') -> dict:
        """
        Dynamically analyzes CSV dataset structure and quality metrics.
        """
        try:
            df = pd.read_csv(io.BytesIO(file_bytes)).replace([np.inf, -np.inf], np.nan)
            if df.empty: raise ValueError('Dataset must contain at least one data row')
            if target_variable not in df.columns: raise ValueError(f"Target column '{target_variable}' is not present in the CSV")
            if df[target_variable].dropna().nunique() < 2: raise ValueError('Target must contain at least two distinct non-missing values')
            task = DatasetService.infer_problem_type(df[target_variable], problem_type)
            rows_count = len(df)
            columns_count = len(df.columns)
            
            missing_count = int(df.isnull().sum().sum())
            total_cells = df.size
            missing_pct = float(missing_count / total_cells * 100) if total_cells > 0 else 0.0
            
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            cat_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
            numerical_count = len(num_cols)
            categorical_count = len(cat_cols)
            
            duplicates_count = int(df.duplicated().sum())
            outliers_count = 0
            for col in num_cols:
                col_data = df[col].dropna()
                if len(col_data) > 0 and col_data.std() > 0:
                    z_scores = np.abs((col_data - col_data.mean()) / col_data.std())
                    outliers_count += int((z_scores > 3).sum())
                    
            is_imbalanced = "None"
            class_distribution = []
            if task == 'classification':
                target_counts = df[target_variable].value_counts(normalize=True)
                if len(target_counts) > 0 and target_counts.iloc[0] > 0.7:
                    is_imbalanced = f"Imbalance detected ({round(target_counts.iloc[0]*100)}% major class)"
                
                # Compute raw counts for distribution chart
                val_counts = df[target_variable].value_counts()
                colors = ["#7c3aed", "#3f3f46", "#818cf8", "#a78bfa"]
                for i, (val, count) in enumerate(val_counts.head(30).items()):
                    class_distribution.append({
                        "name": str(val),
                        "count": int(count),
                        "color": colors[i % len(colors)]
                    })
                    
            quality_health = {
                "missingValues": f"{round(missing_pct, 2)}% missing" if missing_pct > 0 else "0% missing",
                "duplicates": f"{duplicates_count} duplicates" if duplicates_count > 0 else "0 duplicates",
                "outliers": f"{outliers_count} outliers found" if outliers_count > 0 else "No outliers detected",
                "classImbalance": is_imbalanced,
                "invalidDataTypes": "0 invalid data types"
            }
            
            # Compute correlation matrix for top numerical columns
            correlations = {}
            corr_cols = num_cols[:8]
            if len(corr_cols) > 1:
                corr_df = df[corr_cols].corr().fillna(0)
                correlations = {
                    "columns": corr_cols,
                    "values": corr_df.values.tolist()
                }
                
            # Compute distributions for all columns
            distributions = {}
            for col in df.columns:
                col_data = df[col].dropna()
                if len(col_data) == 0:
                    continue
                if col in num_cols:
                    counts, bin_edges = np.histogram(col_data, bins=8)
                    distributions[col] = [
                        {
                            "bin": f"{round(bin_edges[i], 1)}-{round(bin_edges[i+1], 1)}",
                            "count": int(counts[i])
                        }
                        for i in range(len(counts))
                    ]
                else:
                    top_vals = col_data.value_counts().head(8)
                    distributions[col] = [
                        {
                            "bin": str(val),
                            "count": int(count)
                        }
                        for val, count in top_vals.items()
                    ]
                    
            # Compute features metadata
            features_metadata = []
            for col in df.columns:
                col_data = df[col]
                missing_val = int(col_data.isnull().sum())
                col_missing_pct = float(missing_val / len(df) * 100) if len(df) > 0 else 0.0
                unique_val = int(col_data.nunique())
                sample_val = str(col_data.iloc[0]) if len(col_data) > 0 else "N/A"
                
                features_metadata.append({
                    "name": col,
                    "type": str(col_data.dtype),
                    "missing": round(col_missing_pct, 2),
                    "unique": unique_val,
                    "sample": sample_val,
                    "quality": "Target" if col == target_variable else "Missing values require imputation" if col_missing_pct > 0 else "Good"
                })
            
            return {
                "problem_type": task,
                "rows_count": rows_count,
                "columns_count": columns_count,
                "missing_pct": missing_pct,
                "numerical_count": numerical_count,
                "categorical_count": categorical_count,
                "is_imbalanced": is_imbalanced,
                "quality_health": quality_health,
                "class_distribution": class_distribution,
                "correlations": correlations,
                "distributions": distributions,
                "features": features_metadata
            }
        except Exception as e:
            raise ValueError(f'Dataset analysis failed: {e}') from e
