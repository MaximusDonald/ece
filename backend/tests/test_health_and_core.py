import pytest
import redis
from app.core.config import get_settings
from app.core.utils import ensure_uuid
import uuid

def test_ensure_uuid():
    u = uuid.uuid4()
    # Test avec UUID direct
    assert ensure_uuid(u) == u
    # Test avec str
    assert ensure_uuid(str(u)) == u
    # Test avec None
    assert ensure_uuid(None) is None

def test_redis_connection():
    settings = get_settings()
    # Test que redis-py 8.x est fonctionnel avec l'instance redis
    r = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    assert r.ping() is True
    test_key = "test:ping:key"
    r.set(test_key, "pong", ex=10)
    assert r.get(test_key) == "pong"
    r.delete(test_key)

def test_weasyprint_rendering():
    # Vérifie que WeasyPrint ne lève pas l'erreur AttributeError 'super' transform
    from weasyprint import HTML
    html_content = "<html><body><h1>ECE Test Document</h1><p>Vérification du moteur de rendu PDF.</p></body></html>"
    pdf_bytes = HTML(string=html_content).write_pdf()
    assert pdf_bytes is not None
    assert pdf_bytes.startswith(b"%PDF")
