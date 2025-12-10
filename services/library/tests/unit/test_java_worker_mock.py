import pytest
import xml.etree.ElementTree as ET
from unittest.mock import Mock, patch
from library.workers.java_worker import JavaWorker
from library.exceptions import LibraryNotFoundError

@pytest.fixture
def java_worker():
    return JavaWorker()

class TestJavaWorker:
    def test_parse_library_name(self, java_worker):
        # Colon format
        assert java_worker._parse_library_name("com.google.guava:guava") == ("com.google.guava", "guava")
        # Dot format inference
        assert java_worker._parse_library_name("com.google.guava") == ("com.google", "guava")
        # Fallback
        assert java_worker._parse_library_name("simple-lib") == ("simple-lib", "simple-lib")

    def test_get_pom_url(self, java_worker):
        url = java_worker._get_pom_url("com.test", "artifact", "1.0.0")
        assert url == "https://maven.aliyun.com/repository/public/com/test/artifact/1.0.0/artifact-1.0.0.pom"

    def test_extract_dependencies_from_pom(self, java_worker):
        pom_content = """
        <project xmlns="http://maven.apache.org/POM/4.0.0">
            <properties>
                <spring.version>5.3.20</spring.version>
            </properties>
            <dependencies>
                <dependency>
                    <groupId>org.springframework</groupId>
                    <artifactId>spring-core</artifactId>
                    <version>${spring.version}</version>
                </dependency>
                <dependency>
                    <groupId>junit</groupId>
                    <artifactId>junit</artifactId>
                    <version>4.13.2</version>
                    <scope>test</scope>
                </dependency>
            </dependencies>
        </project>
        """
        root = ET.fromstring(pom_content)
        deps = java_worker._extract_dependencies_from_pom(root)
        
        # Should only contain compile scope (spring-core), junit is test scope
        assert len(deps) == 1
        assert deps[0]["name"] == "org.springframework:spring-core"
        assert deps[0]["version"] == "5.3.20"

    def test_get_latest_version_exact_match(self, java_worker):
        with patch.object(java_worker.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "response": {
                    "docs": [{"v": "1.2.3", "timestamp": 1000}]
                }
            }
            mock_get.return_value = mock_response
            
            result = java_worker.get_latest_version("group:artifact")
            assert result["version"] == "1.2.3"

    def test_get_latest_version_fuzzy_match(self, java_worker):
        with patch.object(java_worker.session, 'get') as mock_get:
            mock_response = Mock()
            # Simulate fuzzy search returning multiple results
            mock_response.json.return_value = {
                "response": {
                    "docs": [
                        {"g": "com.unknown", "a": "lib", "v": "1.0", "usageCount": 10},
                        {"g": "org.apache", "a": "lib", "v": "2.0", "usageCount": 100}
                    ]
                }
            }
            mock_get.return_value = mock_response
            
            # Use simple name to trigger fuzzy search logic
            result = java_worker.get_latest_version("lib")
            # Should prefer org.apache due to priority score
            assert result["version"] == "2.0"

    def test_get_documentation_url(self, java_worker):
        res = java_worker.get_documentation_url("com.test:lib", "1.0")
        assert res["doc_url"] == "https://mvnrepository.com/artifact/com.test/lib/1.0"

    def test_check_version_exists(self, java_worker):
        with patch.object(java_worker.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {"response": {"docs": [{"v": "1.0"}]}}
            mock_get.return_value = mock_response
            
            result = java_worker.check_version_exists("lib", "1.0")
            assert result["exists"] is True

    def test_get_dependencies_not_found(self, java_worker):
        with patch.object(java_worker, 'get_latest_version') as mock_latest:
            mock_latest.return_value = {"version": "1.0"}
            with patch.object(java_worker, '_fetch_and_parse_pom', return_value=None):
                res = java_worker.get_dependencies("lib", None)
                assert res["dependencies"] == []
