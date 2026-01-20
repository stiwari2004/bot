"""
Unit tests for runbook generator service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy.orm import Session
from datetime import datetime

from app.services.runbook.generation.runbook_generator_core import RunbookGeneratorService
from app.services.runbook.generation.yaml_generation_pipeline import YamlGenerationPipeline
from app.services.runbook.generation.validation_pipeline import ValidationPipeline
from app.models.runbook import Runbook


@pytest.fixture
def mock_db():
    """Create a mock database session"""
    db = Mock(spec=Session)
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    return db


@pytest.fixture
def generator_service():
    """Create a RunbookGeneratorService instance"""
    return RunbookGeneratorService()


@pytest.fixture
def sample_issue_description():
    """Sample issue description for testing"""
    return "CPU usage is high on Windows server. Need to identify and kill the process."


class TestGenerateRunbook:
    """Test generate_runbook method (RAG-based)"""
    
    @pytest.mark.asyncio
    async def test_generate_runbook_with_valid_description(
        self, generator_service, mock_db, sample_issue_description
    ):
        """Test generating a runbook with valid description"""
        # Mock vector service
        from app.schemas.search import SearchResult
        mock_search_results = [
            SearchResult(
                chunk_id=1,
                document_id=1,
                text="Similar runbook content",
                document_title="Similar Runbook",
                score=0.85,
                document_source="test",
                meta_data={}
            )
        ]
        
        # Mock settings
        mock_settings = Mock()
        mock_settings.ENVIRONMENT = "development"
        
        # Mock Runbook object for database operations
        mock_runbook = Mock(spec=Runbook)
        mock_runbook.id = 1
        mock_runbook.title = "Runbook: CPU usage is high on Windows server. Need to identify and kill the process...."
        mock_runbook.body_md = "# Generated Runbook\nTest content"
        mock_runbook.confidence = 0.85
        mock_runbook.meta_data = '{"issue_description": "test", "sources_used": 1}'
        mock_runbook.created_at = datetime.now()
        mock_runbook.updated_at = datetime.now()
        
        # Mock db operations
        def db_add_side_effect(obj):
            # Set id on the object when added
            if isinstance(obj, Runbook):
                obj.id = 1
        
        mock_db.add.side_effect = db_add_side_effect
        mock_db.refresh.side_effect = lambda obj: setattr(obj, 'id', 1) if hasattr(obj, 'id') else None
        
        with patch.object(
            generator_service.vector_service,
            'hybrid_search',
            new_callable=AsyncMock
        ) as mock_search:
            mock_search.return_value = mock_search_results
            
            with patch.object(
                generator_service.content_builder,
                'generate_content',
                new_callable=AsyncMock
            ) as mock_generate:
                mock_generate.return_value = "# Generated Runbook\nTest content"
                
                    with patch.object(
                        generator_service.content_builder,
                        'calculate_confidence',
                        return_value=0.85
                    ):
                        with patch('app.core.config.get_settings', return_value=mock_settings):
                            with patch('app.services.runbook.generation.runbook_generator_core.Runbook', return_value=mock_runbook):
                            result = await generator_service.generate_runbook(
                                issue_description=sample_issue_description,
                                tenant_id=1,
                                db=mock_db,
                                top_k=5
                            )
                            
                            assert result is not None
                            assert result.confidence == 0.85
                            assert result.id == 1
                            mock_search.assert_called_once()
                            mock_generate.assert_called_once()
                            mock_db.add.assert_called_once()
                            mock_db.commit.assert_called_once()


class TestGenerateAgentRunbook:
    """Test generate_agent_runbook method (YAML-based)"""
    
    @pytest.mark.asyncio
    async def test_generate_agent_runbook_creates_yaml(
        self, generator_service, mock_db, sample_issue_description
    ):
        """Test that agent runbook generation creates YAML"""
        # Mock Runbook object
        mock_runbook = Mock(spec=Runbook)
        mock_runbook.id = 1
        mock_runbook.title = "Runbook: Test"
        mock_runbook.body_md = "```yaml\nrunbook_id: test\nsteps: []\n```"
        mock_runbook.confidence = 0.75
        mock_runbook.meta_data = '{"issue_description": "test"}'
        mock_runbook.created_at = datetime.now()
        mock_runbook.updated_at = datetime.now()
        
        # Mock db operations
        def db_add_side_effect(obj):
            if isinstance(obj, Runbook):
                obj.id = 1
        
        mock_db.add.side_effect = db_add_side_effect
        mock_db.refresh.side_effect = lambda obj: setattr(obj, 'id', 1) if hasattr(obj, 'id') else None
        
        # Mock settings
        mock_settings = Mock()
        mock_settings.ENVIRONMENT = "development"
        
        # Mock all dependencies
        with patch.object(
            generator_service.service_classifier,
            'detect_service_type',
            new_callable=AsyncMock
        ) as mock_detect:
            mock_detect.return_value = "server"
            
            with patch.object(
                generator_service.service_classifier,
                'detect_os_type',
                new_callable=AsyncMock
            ) as mock_detect_os:
                mock_detect_os.return_value = "Windows"
                
                with patch.object(
                    generator_service.vector_service,
                    'hybrid_search',
                    new_callable=AsyncMock
                ) as mock_search:
                    mock_search.return_value = []
                    
                    with patch.object(
                        generator_service.yaml_pipeline,
                        'generate_yaml_from_llm',
                        new_callable=AsyncMock
                    ) as mock_generate_yaml:
                        mock_generate_yaml.return_value = "runbook_id: test\nsteps: []"
                        
                        with patch.object(
                            generator_service.yaml_pipeline,
                            'extract_and_clean_yaml',
                            return_value="runbook_id: test\nsteps: []"
                        ):
                            with patch.object(
                                generator_service.yaml_pipeline,
                                'preprocess_yaml_structure',
                                return_value="runbook_id: test\nsteps: []"
                            ):
                                with patch.object(
                                    generator_service.yaml_parser,
                                    'parse_yaml',
                                    return_value={"runbook_id": "test", "steps": []}
                                ):
                                    with patch.object(
                                        generator_service.spec_post_processor,
                                        'post_process',
                                        return_value={"runbook_id": "test", "steps": [], "title": "Test"}
                                    ):
                                        with patch.object(
                                            generator_service.validation_pipeline,
                                            'validate_structure',
                                            return_value=(True, [])
                                        ):
                                            with patch.object(
                                                generator_service.validation_pipeline,
                                                'validate_commands',
                                                new_callable=AsyncMock
                                            ) as mock_validate_cmds:
                                                mock_validate_cmds.return_value = {"is_valid": True}
                                                with patch.object(
                                                    generator_service.validation_pipeline,
                                                    'critique_runbook',
                                                    new_callable=AsyncMock
                                                ) as mock_critique:
                                                    mock_critique.return_value = {"is_valid": True}
                                                    
                                                    # Mock RunbookValidator.validate_runbook to avoid actual validation
                                                    # Patch at the module level where it's imported inside the function
                                                    with patch('app.schemas.runbook_yaml.RunbookValidator') as mock_validator_class:
                                                        mock_validated_spec = Mock()
                                                        mock_validated_spec.model_dump.return_value = {"runbook_id": "test", "steps": [], "title": "Test"}
                                                        mock_validator_class.validate_runbook.return_value = (mock_validated_spec, [])
                                                        
                                                        # Mock get_settings (imported from app.core.config inside the function)
                                                        with patch('app.core.config.get_settings', return_value=mock_settings):
                                                            # Mock Runbook creation
                                                            with patch('app.services.runbook.generation.runbook_generator_core.Runbook', return_value=mock_runbook):
                                                                # Mock citation_manager
                                                                with patch.object(
                                                                    generator_service.citation_manager,
                                                                    'store_citations',
                                                                    return_value=None
                                                                ):
                                                                    result = await generator_service.generate_agent_runbook(
                                                                        issue_description=sample_issue_description,
                                                                        tenant_id=1,
                                                                        db=mock_db,
                                                                        service="auto",
                                                                        env="prod",
                                                                        risk="low"
                                                                    )
                                                                    
                                                                    assert result is not None
                                                                    assert result.id == 1


class TestYamlGenerationPipeline:
    """Test YAML generation pipeline"""
    
    @pytest.fixture
    def yaml_pipeline(self):
        """Create a YamlGenerationPipeline instance"""
        return YamlGenerationPipeline()
    
    @pytest.mark.asyncio
    async def test_generate_yaml_from_llm_returns_yaml(
        self, yaml_pipeline
    ):
        """Test that YAML is generated from LLM"""
        with patch('app.services.runbook.generation.yaml_generation_pipeline.get_llm_service') as mock_llm:
            mock_llm_service = Mock()
            mock_llm_service.generate_yaml_runbook = AsyncMock(
                return_value="runbook_id: test\nsteps: []"
            )
            mock_llm.return_value = mock_llm_service
            
            result = await yaml_pipeline.generate_yaml_from_llm(
                issue_description="Test issue",
                tenant_id=1,
                service="server",
                env="prod",
                risk="low",
                context="",
                os_type="Windows"
            )
            
            assert result is not None
            assert "runbook_id" in result or "steps" in result
    
    def test_extract_and_clean_yaml_cleans_yaml(self, yaml_pipeline):
        """Test that YAML extraction and cleaning works"""
        raw_yaml = """
        ```yaml
        runbook_id: test
        steps: []
        ```
        """
        
        with patch.object(
            yaml_pipeline.yaml_extractor,
            'extract_yaml',
            return_value="runbook_id: test\nsteps: []"
        ):
            with patch.object(
                yaml_pipeline.yaml_processor,
                'sanitize_description_field',
                return_value="runbook_id: test\nsteps: []"
            ):
                with patch.object(
                    yaml_pipeline.yaml_extractor,
                    'fix_newlines_in_yaml',
                    return_value="runbook_id: test\nsteps: []"
                ):
                    result = yaml_pipeline.extract_and_clean_yaml(raw_yaml)
                    
                    assert result is not None
                    assert "runbook_id" in result


class TestValidationPipeline:
    """Test validation pipeline"""
    
    @pytest.fixture
    def validation_pipeline(self):
        """Create a ValidationPipeline instance"""
        return ValidationPipeline()
    
    def test_validate_structure_with_valid_spec(
        self, validation_pipeline
    ):
        """Test structure validation with valid spec"""
        spec = {
            "runbook_id": "test",
            "prechecks": [{"command": "test"}],
            "steps": [
                {"purpose": "remediate", "command": "fix"},
                {"purpose": "remediate", "command": "restart"},
                {"purpose": "remediate", "command": "stop"}
            ],
            "postchecks": [{"command": "verify"}]
        }
        
        with patch.object(
            validation_pipeline.quality_validator,
            'validate',
            return_value=(True, [])
        ):
            is_valid, errors = validation_pipeline.validate_structure(
                spec, "Test issue"
            )
            
            assert is_valid is True
            assert len(errors) == 0
    
    def test_validate_structure_with_missing_remediation(
        self, validation_pipeline
    ):
        """Test structure validation detects missing remediation"""
        spec = {
            "runbook_id": "test",
            "prechecks": [{"command": "test"}],
            "steps": [
                {"purpose": "diagnose", "command": "check"}
            ],
            "postchecks": [{"command": "verify"}]
        }
        
        with patch.object(
            validation_pipeline.quality_validator,
            'validate',
            return_value=(False, ["CRITICAL: Missing remediation steps"])
        ):
            with pytest.raises(Exception):  # Should raise HTTPException
                validation_pipeline.validate_structure(spec, "Test issue")
    
    @pytest.mark.asyncio
    async def test_validate_commands_with_valid_commands(
        self, validation_pipeline
    ):
        """Test command validation with valid commands"""
        spec = {
            "steps": [
                {"purpose": "remediate", "command": "Stop-Process -Id 123"}
            ]
        }
        
        with patch.object(
            validation_pipeline.command_validator,
            'validate_runbook_commands',
            new_callable=AsyncMock,
            return_value={"is_valid": True, "remediation_commands_found": [1, 2, 3, 4]}
        ):
            result = await validation_pipeline.validate_commands(
                spec, "Test issue", "prod", "Windows"
            )
            
            assert result["is_valid"] is True

