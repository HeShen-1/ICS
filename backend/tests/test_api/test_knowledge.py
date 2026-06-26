"""Tests for /api/knowledge endpoints."""
import pytest
import io


class TestUploadDocument:
    def test_upload_document_txt(self, auth_headers, test_client):
        file_content = io.BytesIO(b"test document content for upload")
        response = test_client.post(
            "/api/knowledge/upload",
            files={"file": ("test.txt", file_content, "text/plain")},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test.txt"
        assert data["file_type"] in ("txt", "processing", "ready", "failed")
        assert data["id"] > 0

    def test_upload_invalid_format(self, auth_headers, test_client):
        file_content = io.BytesIO(b"fake image content")
        response = test_client.post(
            "/api/knowledge/upload",
            files={"file": ("test.jpg", file_content, "image/jpeg")},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "不支持" in response.json()["detail"]

    def test_upload_requires_auth(self, test_client):
        file_content = io.BytesIO(b"test")
        response = test_client.post(
            "/api/knowledge/upload",
            files={"file": ("test.txt", file_content, "text/plain")},
        )
        assert response.status_code == 403


class TestListDocuments:
    def test_list_documents_empty(self, auth_headers, test_client):
        response = test_client.get("/api/knowledge/list", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data

    def test_list_documents_with_data(self, auth_headers, test_client):
        # Upload a document first
        file_content = io.BytesIO(b"doc content")
        test_client.post(
            "/api/knowledge/upload",
            files={"file": ("doc1.txt", file_content, "text/plain")},
            headers=auth_headers,
        )

        response = test_client.get("/api/knowledge/list", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


class TestDeleteDocument:
    def test_delete_document(self, auth_headers, test_client):
        # Upload first
        file_content = io.BytesIO(b"content to be deleted")
        r = test_client.post(
            "/api/knowledge/upload",
            files={"file": ("to_delete.txt", file_content, "text/plain")},
            headers=auth_headers,
        )
        doc_id = r.json()["id"]

        # Delete
        response = test_client.delete(f"/api/knowledge/{doc_id}", headers=auth_headers)
        assert response.status_code == 200
        assert "删除成功" in response.json()["message"]

    def test_delete_nonexistent_document(self, auth_headers, test_client):
        response = test_client.delete("/api/knowledge/99999", headers=auth_headers)
        assert response.status_code == 404


class TestKnowledgeBaseCRUD:
    def test_create_knowledge_base(self, auth_headers, test_client):
        response = test_client.post(
            "/api/knowledge/bases",
            json={"name": "测试知识库", "description": "用于测试"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "测试知识库"
        assert data["id"] > 0

    def test_list_knowledge_bases(self, auth_headers, test_client):
        test_client.post(
            "/api/knowledge/bases",
            json={"name": "KB1"},
            headers=auth_headers,
        )
        response = test_client.get("/api/knowledge/bases", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_delete_knowledge_base(self, auth_headers, test_client):
        r = test_client.post(
            "/api/knowledge/bases",
            json={"name": "待删除知识库"},
            headers=auth_headers,
        )
        kb_id = r.json()["id"]
        response = test_client.delete(f"/api/knowledge/bases/{kb_id}", headers=auth_headers)
        assert response.status_code == 200
        assert "删除成功" in response.json()["message"]
