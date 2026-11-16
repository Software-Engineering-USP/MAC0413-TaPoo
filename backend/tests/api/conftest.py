from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.api.dependencias import montar_container
from app.infra.fontes.fake import FonteFake
from app.main import create_app

AGORA = datetime(2026, 1, 10, 12, tzinfo=UTC)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(lambda: montar_container(FonteFake(AGORA), relogio=lambda: AGORA))
    with TestClient(app) as c:  # o "with" executa o lifespan (carga inicial)
        yield c
