"""
Tests for infrastructure setup script.
These tests verify the helper functions without actually deploying resources.
"""
import subprocess
from unittest.mock import MagicMock, patch

import pytest

# ============================================================================
# Infrastructure Script Tests
# ============================================================================

class TestInfraHelpers:
    """Tests for infrastructure helper functions."""
    
    @pytest.mark.unit
    def test_get_os_info_returns_dict(self):
        """get_os_info should return OS information dict."""
        import sys
        sys.path.insert(0, 'scripts')
        from setup_infra import get_os_info
        
        result = get_os_info()
        assert isinstance(result, dict)
        assert 'system' in result
        assert 'is_windows' in result
        assert 'is_mac' in result
        assert 'is_linux' in result
    
    @pytest.mark.unit
    def test_get_os_info_has_boolean_flags(self):
        """OS flags should be boolean."""
        import sys
        sys.path.insert(0, 'scripts')
        from setup_infra import get_os_info
        
        result = get_os_info()
        assert isinstance(result['is_windows'], bool)
        assert isinstance(result['is_mac'], bool)
        assert isinstance(result['is_linux'], bool)
    
    @pytest.mark.unit
    def test_colors_class_has_codes(self):
        """Colors class should have ANSI codes."""
        import sys
        sys.path.insert(0, 'scripts')
        from setup_infra import Colors
        
        assert hasattr(Colors, 'GREEN')
        assert hasattr(Colors, 'RED')
        assert hasattr(Colors, 'YELLOW')
        assert hasattr(Colors, 'RESET')
    
    @pytest.mark.unit
    def test_colors_disable(self):
        """Colors.disable() should clear all codes."""
        import sys
        sys.path.insert(0, 'scripts')
        from setup_infra import Colors
        
        # Store originals
        original_green = Colors.GREEN
        
        Colors.disable()
        
        assert Colors.GREEN == ''
        assert Colors.RED == ''
        assert Colors.RESET == ''
        
        # Restore (for other tests)
        Colors.GREEN = original_green or '\033[92m'


class TestDockerCheck:
    """Tests for Docker availability check."""
    
    @pytest.mark.unit
    @patch('setup_infra.run_cmd')
    def test_check_docker_success(self, mock_run):
        """check_docker returns True when Docker is running."""
        import sys
        sys.path.insert(0, 'scripts')
        from setup_infra import check_docker
        
        mock_run.return_value = MagicMock(returncode=0)
        result = check_docker()
        assert result is True
    
    @pytest.mark.unit
    @patch('setup_infra.run_cmd')
    def test_check_docker_failure(self, mock_run):
        """check_docker returns False when Docker is not running."""
        import sys
        sys.path.insert(0, 'scripts')
        from setup_infra import check_docker
        
        mock_run.side_effect = subprocess.CalledProcessError(1, 'docker')
        result = check_docker()
        assert result is False


class TestKubernetesCheck:
    """Tests for Kubernetes availability check."""
    
    @pytest.mark.unit
    @patch('setup_infra.run_cmd')
    def test_check_kubernetes_not_enabled(self, mock_run):
        """check_kubernetes returns False when K8s is not enabled."""
        import sys
        sys.path.insert(0, 'scripts')
        from setup_infra import check_kubernetes
        
        # Mock kubectl returning no docker-desktop context
        mock_result = MagicMock()
        mock_result.stdout = "minikube  active"
        mock_run.return_value = mock_result
        
        result = check_kubernetes()
        assert result is False


# ============================================================================
# Kubernetes Manifest Validation Tests
# ============================================================================

class TestKubernetesManifests:
    """Tests for Kubernetes manifest structure."""
    
    @pytest.mark.unit
    def test_namespace_yaml_exists(self):
        """namespace.yaml should exist."""
        from pathlib import Path
        ns_file = Path("infra/k8s/namespace.yaml")
        assert ns_file.exists(), "namespace.yaml not found"
    
    @pytest.mark.unit
    def test_deployment_yaml_exists(self):
        """ChromaDB deployment.yaml should exist."""
        from pathlib import Path
        deploy_file = Path("infra/k8s/chromadb/deployment.yaml")
        assert deploy_file.exists(), "deployment.yaml not found"
    
    @pytest.mark.unit
    def test_namespace_yaml_valid(self):
        """namespace.yaml should be valid YAML with correct structure."""
        from pathlib import Path

        import yaml
        
        content = Path("infra/k8s/namespace.yaml").read_text()
        data = yaml.safe_load(content)
        
        assert data['apiVersion'] == 'v1'
        assert data['kind'] == 'Namespace'
        assert data['metadata']['name'] == 'f1-agent'
    
    @pytest.mark.unit
    def test_deployment_has_required_resources(self):
        """ChromaDB deployment should have resource limits."""
        from pathlib import Path

        import yaml
        
        content = Path("infra/k8s/chromadb/deployment.yaml").read_text()
        docs = list(yaml.safe_load_all(content))
        
        # Find the Deployment document
        deployment = None
        for doc in docs:
            if doc and doc.get('kind') == 'Deployment':
                deployment = doc
                break
        
        assert deployment is not None, "No Deployment found"
        
        container = deployment['spec']['template']['spec']['containers'][0]
        assert 'resources' in container
        assert 'requests' in container['resources']
        assert 'limits' in container['resources']
    
    @pytest.mark.unit
    def test_deployment_has_health_probes(self):
        """ChromaDB deployment should have liveness and readiness probes."""
        from pathlib import Path

        import yaml
        
        content = Path("infra/k8s/chromadb/deployment.yaml").read_text()
        docs = list(yaml.safe_load_all(content))
        
        deployment = None
        for doc in docs:
            if doc and doc.get('kind') == 'Deployment':
                deployment = doc
                break
        
        container = deployment['spec']['template']['spec']['containers'][0]
        assert 'livenessProbe' in container
        assert 'readinessProbe' in container
    
    @pytest.mark.unit
    def test_service_has_correct_port(self):
        """ChromaDB service should expose port 8000."""
        from pathlib import Path

        import yaml
        
        content = Path("infra/k8s/chromadb/deployment.yaml").read_text()
        docs = list(yaml.safe_load_all(content))
        
        service = None
        for doc in docs:
            if doc and doc.get('kind') == 'Service':
                service = doc
                break
        
        assert service is not None, "No Service found"
        assert service['spec']['ports'][0]['port'] == 8000
