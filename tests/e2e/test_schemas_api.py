"""E2E — /schemas endpoints."""


class TestGetSchema:
    def test_returns_schema_for_e14_senado(self, client):
        resp = client.get("/schemas/E14_SENADO")
        assert resp.status_code == 200
        body = resp.json()
        assert body["document_kind"] == "E14_SENADO"
        label_names = [lb["name"] for lb in body["labels"]]
        assert "TotalSufragantes" in label_names

    def test_missing_kind_returns_404(self, client):
        resp = client.get("/schemas/TIPO_INEXISTENTE")
        assert resp.status_code == 422  # FastAPI rejects invalid enum

    def test_label_names_endpoint(self, client):
        resp = client.get("/schemas/E14_SENADO/names")
        assert resp.status_code == 200
        names = resp.json()
        assert isinstance(names, list)
        assert "TotalSufragantes" in names
