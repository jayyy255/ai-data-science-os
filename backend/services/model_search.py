"""Validation-only hyperparameter search for every available candidate model."""
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TRIALS_PER_MODEL = 5


def model_factories(classification):
    forest = RandomForestClassifier if classification else RandomForestRegressor

    def random_forest(trial):
        return forest(n_estimators=trial.suggest_int('n_estimators', 40, 100),
                      max_depth=trial.suggest_int('max_depth', 3, 12),
                      min_samples_leaf=trial.suggest_int('min_samples_leaf', 1, 4),
                      random_state=42, n_jobs=2)

    factories = {'Random Forest': random_forest}
    try:
        import xgboost as xgb
        boosted = xgb.XGBClassifier if classification else xgb.XGBRegressor

        def xgboost(trial):
            return boosted(n_estimators=trial.suggest_int('n_estimators', 40, 120),
                           max_depth=trial.suggest_int('max_depth', 2, 6),
                           learning_rate=trial.suggest_float('learning_rate', .03, .3, log=True),
                           subsample=trial.suggest_float('subsample', .7, 1),
                           colsample_bytree=trial.suggest_float('colsample_bytree', .7, 1),
                           random_state=42, n_jobs=2)
        factories['XGBoost'] = xgboost
    except ImportError:
        pass
    try:
        import lightgbm as lgb
        light = lgb.LGBMClassifier if classification else lgb.LGBMRegressor

        def lightgbm(trial):
            return light(n_estimators=trial.suggest_int('n_estimators', 40, 120),
                         num_leaves=trial.suggest_int('num_leaves', 7, 31),
                         min_child_samples=trial.suggest_int('min_child_samples', 5, 25),
                         learning_rate=trial.suggest_float('learning_rate', .03, .3, log=True),
                         random_state=42, n_jobs=2, verbosity=-1)
        factories['LightGBM'] = lightgbm
    except ImportError:
        pass
    neural = MLPClassifier if classification else MLPRegressor

    def neural_network(trial):
        architectures = {'32': (32,), '32_16': (32, 16), '64_32': (64, 32)}
        layer = trial.suggest_categorical('architecture', list(architectures))
        estimator = neural(hidden_layer_sizes=architectures[layer], max_iter=400,
                           alpha=trial.suggest_float('alpha', 1e-5, .01, log=True),
                           learning_rate_init=trial.suggest_float('learning_rate_init', .001, .03, log=True),
                           random_state=42)
        # Model-internal scaling keeps the neural optimizer stable even with raw feature overrides.
        return Pipeline([('scale', StandardScaler()), ('network', estimator)])
    factories['Neural Network'] = neural_network
    return factories
