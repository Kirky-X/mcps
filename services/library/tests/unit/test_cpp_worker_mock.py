import pytest
import base64
import json
from unittest.mock import Mock, patch
from library.workers.cpp_worker import CppWorker, ConanProvider, VcpkgProvider
from library.exceptions import LibraryNotFoundError

@pytest.fixture
def cpp_worker():
    return CppWorker()

class TestCppWorker:
    def test_parse_library(self, cpp_worker):
        assert cpp_worker._parse_library("conan:pkg") == ("conan", "pkg")
        assert cpp_worker._parse_library("vcpkg:pkg") == ("vcpkg", "pkg")
        
        with pytest.raises(ValueError):
            cpp_worker._parse_library("pkg") # Missing ecosystem
            
        with pytest.raises(ValueError):
            cpp_worker._parse_library("unknown:pkg") # Unsupported ecosystem

    def test_routing(self, cpp_worker):
        with patch.object(cpp_worker._providers['conan'], 'get_latest_version') as mock_conan:
            mock_conan.return_value = {"version": "1.0"}
            res = cpp_worker.get_latest_version("conan:pkg")
            assert res["version"] == "1.0"
            mock_conan.assert_called_with("pkg")

class TestConanProvider:
    @pytest.fixture
    def conan(self):
        return ConanProvider()

    def test_get_latest_version(self, conan):
        with patch.object(conan.client, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"versions": [{"version": "2.0"}, {"version": "1.0"}]}
            mock_get.return_value = mock_response
            
            res = conan.get_latest_version("pkg")
            assert res["version"] == "2.0"

    def test_get_dependencies(self, conan):
        with patch.object(conan.client, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "requires": [{"name": "dep1", "version": "1.0"}]
            }
            mock_get.return_value = mock_response
            
            res = conan.get_dependencies("pkg", "1.0")
            assert len(res["dependencies"]) == 1
            assert res["dependencies"][0]["name"] == "dep1"

class TestVcpkgProvider:
    @pytest.fixture
    def vcpkg(self):
        return VcpkgProvider()

    def test_get_latest_version_from_vcpkg_json(self, vcpkg):
        with patch.object(vcpkg.client, 'get') as mock_get:
            # First call checks existence
            # Second call gets vcpkg.json
            mock_get.side_effect = [
                Mock(status_code=200),
                Mock(status_code=200, json=lambda: {
                    "content": base64.b64encode(json.dumps({"version": "1.2.3"}).encode()).decode()
                })
            ]
            
            res = vcpkg.get_latest_version("pkg")
            assert res["version"] == "1.2.3"

    def test_get_latest_version_from_portfile(self, vcpkg):
        with patch.object(vcpkg.client, 'get') as mock_get:
            # First call exists
            # Second call vcpkg.json 404
            # Third call portfile.cmake 200
            mock_get.side_effect = [
                Mock(status_code=200),
                Mock(status_code=404),
                Mock(status_code=200, json=lambda: {
                    "content": base64.b64encode(b"vcpkg_from_github(REF v1.0.0)").decode()
                })
            ]
            
            res = vcpkg.get_latest_version("pkg")
            assert res["version"] == "1.0.0"

    def test_get_dependencies(self, vcpkg):
        with patch.object(vcpkg.client, 'get') as mock_get:
            content = json.dumps({
                "dependencies": ["dep1", {"name": "dep2", "version": "2.0"}]
            })
            mock_get.return_value = Mock(status_code=200, json=lambda: {
                "content": base64.b64encode(content.encode()).decode()
            })
            
            res = vcpkg.get_dependencies("pkg", "1.0")
            assert len(res["dependencies"]) == 2
            assert res["dependencies"][0]["name"] == "dep1"
            assert res["dependencies"][1]["name"] == "dep2"
