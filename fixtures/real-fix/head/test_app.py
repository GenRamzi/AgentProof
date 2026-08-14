from app import ready

def test_pending_is_ready():
    assert ready('pending') is True
