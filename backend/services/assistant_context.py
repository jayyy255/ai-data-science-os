"""Bounded, project-scoped evidence for assistant answers; no global server logs."""
import hashlib
import json
from database.models import DecisionMemory, KnowledgeCard, TimelineEvent, TrainingJob
from services.sandbox import redact


def safe_context(value, depth=0):
    if depth > 10:
        return '[depth limit]'
    if isinstance(value, dict):
        return {str(key)[:100]: safe_context(item, depth + 1) for key, item in list(value.items())[:40]
                if not any(word in str(key).lower() for word in ('password', 'credential', 'secret', 'token', 'artifact_path', 'model_path'))}
    if isinstance(value, (list, tuple)):
        return [safe_context(item, depth + 1) for item in value[:30]]
    if isinstance(value, str):
        return redact(value)[:2000]
    return value


def build_assistant_context(db, project):
    card = db.query(KnowledgeCard).filter_by(project_id=project.id).first()
    decisions = db.query(DecisionMemory).filter_by(project_id=project.id).all()
    events = db.query(TimelineEvent).filter_by(project_id=project.id).order_by(TimelineEvent.timestamp.desc(), TimelineEvent.id.desc()).limit(30).all()
    jobs = db.query(TrainingJob).filter_by(project_id=project.id).order_by(TrainingJob.id.desc()).limit(3).all()
    selection_event = db.query(TimelineEvent).filter(
        TimelineEvent.project_id == project.id,
        TimelineEvent.title.in_(['Champion Model Selected', 'Model Training Completed'])
    ).order_by(TimelineEvent.timestamp.desc(), TimelineEvent.id.desc()).first()
    knowledge = {
        'project_name': project.name, 'best_model': card.best_model if card else None,
        'best_f1': card.best_f1 if card else None, 'best_mse': card.best_mse if card else None,
        'problem_type': project.problem_type, 'target': project.target_variable,
        'top_features': card.top_features if card else [], 'rows_count': card.rows_count if card else 0,
        'columns_count': card.columns_count if card else 0, 'status': project.status,
        'models_comparison': card.models_comparison_json if card else {},
        'selection_evidence': {'title': selection_event.title, 'timestamp': selection_event.timestamp.isoformat(), 'description': selection_event.description} if selection_event else None,
        'decisions': [{'feature': item.feature_name, 'transformation': item.user_choice if item.override_active else item.decision, 'reason': item.reason} for item in decisions],
    }
    timeline = [{'id': event.id, 'timestamp': event.timestamp.isoformat(), 'title': event.title,
                 'description': event.description, 'type': event.event_type} for event in reversed(events)]
    logs = []
    for job in jobs:
        metrics = job.metrics_json or {}
        sandbox = metrics.get('sandbox') or {}
        logs.append({'job_id': job.id, 'status': job.status,
                     'started_at': job.started_at.isoformat() if job.started_at else None,
                     'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                     'imputation': job.imputation_method, 'error': metrics.get('error'),
                     'model_selection': metrics.get('model_selection'),
                     'hpo_trials': metrics.get('hpo_trials', [])[-20:],
                     'events': metrics.get('execution_log', [])[-12:],
                     'sandbox': {key: sandbox.get(key) for key in ('execution_id', 'operation', 'backend', 'duration_seconds', 'network', 'read_only_root', 'memory_mb', 'cpus')},
                     'log_tail': sandbox.get('log_tail', '')[-4000:]})
    context = safe_context({'knowledge_card': knowledge, 'timeline': timeline, 'execution_logs': logs})
    while len(json.dumps(context)) > 48000:
        if len(context['execution_logs']) > 1:
            context['execution_logs'].pop()
        elif len(context['timeline']) > 5:
            context['timeline'].pop(0)
        elif context['execution_logs'] and context['execution_logs'][0]['events']:
            context['execution_logs'][0]['events'].pop(0)
        elif context['execution_logs'] and context['execution_logs'][0]['hpo_trials']:
            context['execution_logs'][0]['hpo_trials'].pop(0)
        else:
            break
    if len(json.dumps(context)) > 48000:
        # Oversized user-provided feature names/reasons must not overrun the prompt budget.
        context['knowledge_card']['decisions'] = []
        context['knowledge_card']['models_comparison'] = {}
        context['knowledge_card']['top_features'] = context['knowledge_card']['top_features'][:3]
    revision = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()
    return context, revision
