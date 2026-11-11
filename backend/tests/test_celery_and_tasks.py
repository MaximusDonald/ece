import pytest
from app.workers.celery_app import celery_app, debug_task

def test_celery_configuration():
    # Vérifie que la configuration Celery est valide et n'a pas de conflit Kombu/Redis
    assert celery_app.conf.broker_url is not None
    assert "redis://" in celery_app.conf.broker_url
    assert celery_app.conf.task_serializer == "json"

def test_debug_task_execution():
    # Exécution locale directe de la tâche pour valider son exécution sans erreur
    result = debug_task()
    assert result is None
