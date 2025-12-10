import pytest
import logging
from unittest.mock import Mock, patch
from library.workers.python_worker import PythonWorker
from library.workers.node_worker import NodeWorker
from library.exceptions import LibraryNotFoundError
from library.models import Task

@pytest.fixture
def python_worker():
    return PythonWorker()

@pytest.fixture
def node_worker():
    return NodeWorker()

class TestPythonWorker:
    def test_get_latest_version_success(self, python_worker):
        with patch.object(python_worker, '_make_request') as mock_req:
            mock_req.return_value.json.return_value = {"info": {"version": "2.31.0"}}
            result = python_worker.get_latest_version("requests")
            assert result["version"] == "2.31.0"

    def test_get_documentation_url(self, python_worker):
        result = python_worker.get_documentation_url("requests", "2.31.0")
        assert result["doc_url"] == "https://pypi.org/project/requests/2.31.0/"

    def test_check_version_exists_success(self, python_worker):
        with patch.object(python_worker, '_make_request') as mock_req:
            mock_req.return_value.status_code = 200
            result = python_worker.check_version_exists("requests", "2.31.0")
            assert result["exists"] is True

    def test_check_version_exists_failure(self, python_worker):
        with patch.object(python_worker, '_make_request') as mock_req:
            mock_req.side_effect = LibraryNotFoundError("Not found")
            result = python_worker.check_version_exists("requests", "999.9.9")
            assert result["exists"] is False

    def test_get_dependencies_success(self, python_worker):
        with patch.object(python_worker, '_make_request') as mock_req:
            mock_req.return_value.json.return_value = {
                "info": {
                    "version": "2.31.0",
                    "requires_dist": ["urllib3<3,>=1.21.1", "certifi>=2017.4.17"]
                }
            }
            result = python_worker.get_dependencies("requests", "2.31.0")
            assert len(result["dependencies"]) == 2
            assert result["dependencies"][0]["name"] == "urllib3"

    def test_parse_dependency_string_edge_cases(self, python_worker):
        # Test extras
        res = python_worker._parse_dependency_string("requests[security]>=2.0.0")
        assert res["name"] == "requests"
        assert res["version"] == ">=2.0.0"
        
        # Test environment markers
        res = python_worker._parse_dependency_string("enum34; python_version < '3.4'")
        assert res["name"] == "enum34"
        
        # Test simple
        res = python_worker._parse_dependency_string("simple-lib")
        assert res["name"] == "simple-lib"
        assert res["version"] == "*"

class TestNodeWorker:
    def test_get_latest_version_success(self, node_worker):
        with patch.object(node_worker, '_make_request') as mock_req:
            mock_req.return_value.json.return_value = {"dist-tags": {"latest": "1.0.0"}}
            result = node_worker.get_latest_version("lodash")
            assert result["version"] == "1.0.0"

    def test_get_documentation_url(self, node_worker):
        result = node_worker.get_documentation_url("lodash", "1.0.0")
        assert result["doc_url"] == "https://www.npmjs.com/package/lodash/v/1.0.0"

    def test_check_version_exists_success(self, node_worker):
        with patch.object(node_worker, '_make_request') as mock_req:
            mock_req.return_value.status_code = 200
            result = node_worker.check_version_exists("lodash", "1.0.0")
            assert result["exists"] is True

    def test_get_dependencies_success(self, node_worker):
        with patch.object(node_worker, '_make_request') as mock_req:
            mock_req.return_value.json.return_value = {
                "version": "1.0.0",
                "dependencies": {
                    "dep1": "^1.0.0",
                    "dep2": "~2.0.0"
                }
            }
            result = node_worker.get_dependencies("test-pkg", "1.0.0")
            assert len(result["dependencies"]) == 2
            assert result["dependencies"][0]["name"] == "dep1"
