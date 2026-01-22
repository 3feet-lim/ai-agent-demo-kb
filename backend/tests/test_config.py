"""
구성 모델 단위 테스트

이 모듈은 Pydantic 구성 모델의 검증 로직을 테스트합니다.

요구사항: 4.4, 8.2, 8.3
"""

import pytest
from pydantic import ValidationError
from backend.config import (
    BedrockConfig,
    GrafanaConfig,
    CloudWatchConfig,
    DatabaseConfig,
    AppConfig
)


class TestBedrockConfig:
    """BedrockConfig 모델 테스트"""
    
    def test_valid_bedrock_config(self):
        """유효한 Bedrock 구성 생성 테스트"""
        config = BedrockConfig(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1"
        )
        
        assert config.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert config.region == "us-east-1"
        assert config.model_id == "anthropic.claude-sonnet-4-5"  # 기본값
        assert config.temperature == 0.7  # 기본값
        assert config.max_tokens == 4096  # 기본값
    
    def test_bedrock_config_with_custom_values(self):
        """사용자 정의 값으로 Bedrock 구성 생성 테스트"""
        config = BedrockConfig(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="ap-northeast-2",
            model_id="anthropic.claude-3-opus",
            temperature=0.5,
            max_tokens=2048
        )
        
        assert config.region == "ap-northeast-2"
        assert config.model_id == "anthropic.claude-3-opus"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
    
    def test_bedrock_config_missing_required_fields(self):
        """필수 필드 누락 시 오류 발생 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            BedrockConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE"
                # aws_secret_access_key와 region 누락
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 2
        assert any(e['loc'] == ('aws_secret_access_key',) for e in errors)
        assert any(e['loc'] == ('region',) for e in errors)
    
    def test_bedrock_config_invalid_temperature(self):
        """잘못된 temperature 값 테스트"""
        # temperature > 1.0
        with pytest.raises(ValidationError) as exc_info:
            BedrockConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-east-1",
                temperature=1.5
            )
        
        errors = exc_info.value.errors()
        assert any('temperature' in str(e['loc']) for e in errors)
        
        # temperature < 0.0
        with pytest.raises(ValidationError) as exc_info:
            BedrockConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-east-1",
                temperature=-0.1
            )
        
        errors = exc_info.value.errors()
        assert any('temperature' in str(e['loc']) for e in errors)
    
    def test_bedrock_config_invalid_max_tokens(self):
        """잘못된 max_tokens 값 테스트"""
        # max_tokens <= 0
        with pytest.raises(ValidationError) as exc_info:
            BedrockConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-east-1",
                max_tokens=0
            )
        
        errors = exc_info.value.errors()
        assert any('max_tokens' in str(e['loc']) for e in errors)
        
        # max_tokens > 200000
        with pytest.raises(ValidationError) as exc_info:
            BedrockConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-east-1",
                max_tokens=300000
            )
        
        errors = exc_info.value.errors()
        assert any('max_tokens' in str(e['loc']) for e in errors)
    
    def test_bedrock_config_empty_region(self):
        """빈 리전 값 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            BedrockConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region=""
            )
        
        errors = exc_info.value.errors()
        assert any('region' in str(e['loc']) for e in errors)
    
    def test_bedrock_config_whitespace_trimming(self):
        """공백 제거 테스트"""
        config = BedrockConfig(
            aws_access_key_id="  AKIAIOSFODNN7EXAMPLE  ",
            aws_secret_access_key="  wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  ",
            region="  us-east-1  "
        )
        
        assert config.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert config.region == "us-east-1"


class TestGrafanaConfig:
    """GrafanaConfig 모델 테스트"""
    
    def test_valid_grafana_config(self):
        """유효한 Grafana 구성 생성 테스트"""
        config = GrafanaConfig(
            url="https://grafana.example.com",
            api_key="eyJrIjoiVGVzdEFQSUtleSJ9"
        )
        
        assert config.url == "https://grafana.example.com"
        assert config.api_key == "eyJrIjoiVGVzdEFQSUtleSJ9"
    
    def test_grafana_config_http_url(self):
        """HTTP URL 테스트"""
        config = GrafanaConfig(
            url="http://grafana.local:3000",
            api_key="test-api-key"
        )
        
        assert config.url == "http://grafana.local:3000"
    
    def test_grafana_config_trailing_slash_removal(self):
        """후행 슬래시 제거 테스트"""
        config = GrafanaConfig(
            url="https://grafana.example.com/",
            api_key="test-api-key"
        )
        
        assert config.url == "https://grafana.example.com"
    
    def test_grafana_config_missing_required_fields(self):
        """필수 필드 누락 시 오류 발생 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            GrafanaConfig(url="https://grafana.example.com")
            # api_key 누락
        
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('api_key',) for e in errors)
    
    def test_grafana_config_invalid_url_format(self):
        """잘못된 URL 형식 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            GrafanaConfig(
                url="grafana.example.com",  # http:// 또는 https:// 없음
                api_key="test-api-key"
            )
        
        errors = exc_info.value.errors()
        assert any('url' in str(e['loc']) for e in errors)
    
    def test_grafana_config_empty_url(self):
        """빈 URL 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            GrafanaConfig(
                url="",
                api_key="test-api-key"
            )
        
        errors = exc_info.value.errors()
        assert any('url' in str(e['loc']) for e in errors)
    
    def test_grafana_config_empty_api_key(self):
        """빈 API 키 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            GrafanaConfig(
                url="https://grafana.example.com",
                api_key=""
            )
        
        errors = exc_info.value.errors()
        assert any('api_key' in str(e['loc']) for e in errors)
    
    def test_grafana_config_whitespace_trimming(self):
        """공백 제거 테스트"""
        config = GrafanaConfig(
            url="  https://grafana.example.com  ",
            api_key="  test-api-key  "
        )
        
        assert config.url == "https://grafana.example.com"
        assert config.api_key == "test-api-key"


class TestCloudWatchConfig:
    """CloudWatchConfig 모델 테스트"""
    
    def test_valid_cloudwatch_config(self):
        """유효한 CloudWatch 구성 생성 테스트"""
        config = CloudWatchConfig(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-west-2"
        )
        
        assert config.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert config.region == "us-west-2"
    
    def test_cloudwatch_config_missing_required_fields(self):
        """필수 필드 누락 시 오류 발생 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            CloudWatchConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE"
                # aws_secret_access_key와 region 누락
            )
        
        errors = exc_info.value.errors()
        assert len(errors) == 2
        assert any(e['loc'] == ('aws_secret_access_key',) for e in errors)
        assert any(e['loc'] == ('region',) for e in errors)
    
    def test_cloudwatch_config_empty_region(self):
        """빈 리전 값 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            CloudWatchConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region=""
            )
        
        errors = exc_info.value.errors()
        assert any('region' in str(e['loc']) for e in errors)
    
    def test_cloudwatch_config_whitespace_trimming(self):
        """공백 제거 테스트"""
        config = CloudWatchConfig(
            aws_access_key_id="  AKIAIOSFODNN7EXAMPLE  ",
            aws_secret_access_key="  wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  ",
            region="  eu-west-1  "
        )
        
        assert config.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert config.region == "eu-west-1"


class TestDatabaseConfig:
    """DatabaseConfig 모델 테스트"""
    
    def test_valid_database_config(self):
        """유효한 데이터베이스 구성 생성 테스트"""
        config = DatabaseConfig(path="/app/data/chatbot.db")
        
        assert config.path == "/app/data/chatbot.db"
    
    def test_database_config_default_path(self):
        """기본 경로 테스트"""
        config = DatabaseConfig()
        
        assert config.path == "chatbot.db"
    
    def test_database_config_empty_path(self):
        """빈 경로 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            DatabaseConfig(path="")
        
        errors = exc_info.value.errors()
        assert any('path' in str(e['loc']) for e in errors)
    
    def test_database_config_whitespace_trimming(self):
        """공백 제거 테스트"""
        config = DatabaseConfig(path="  /app/data/chatbot.db  ")
        
        assert config.path == "/app/data/chatbot.db"


class TestAppConfig:
    """AppConfig 모델 테스트"""
    
    def test_valid_app_config(self):
        """유효한 전체 애플리케이션 구성 생성 테스트"""
        config = AppConfig(
            bedrock=BedrockConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-east-1"
            ),
            grafana=GrafanaConfig(
                url="https://grafana.example.com",
                api_key="test-api-key"
            ),
            cloudwatch=CloudWatchConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-west-2"
            )
        )
        
        assert config.bedrock.region == "us-east-1"
        assert config.grafana.url == "https://grafana.example.com"
        assert config.cloudwatch.region == "us-west-2"
        assert config.database.path == "chatbot.db"  # 기본값
    
    def test_app_config_with_custom_database(self):
        """사용자 정의 데이터베이스 구성 테스트"""
        config = AppConfig(
            bedrock=BedrockConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-east-1"
            ),
            grafana=GrafanaConfig(
                url="https://grafana.example.com",
                api_key="test-api-key"
            ),
            cloudwatch=CloudWatchConfig(
                aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-west-2"
            ),
            database=DatabaseConfig(path="/custom/path/db.sqlite")
        )
        
        assert config.database.path == "/custom/path/db.sqlite"
    
    def test_app_config_missing_required_sections(self):
        """필수 섹션 누락 시 오류 발생 테스트"""
        with pytest.raises(ValidationError) as exc_info:
            AppConfig(
                bedrock=BedrockConfig(
                    aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
                    aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                    region="us-east-1"
                )
                # grafana와 cloudwatch 누락
            )
        
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('grafana',) for e in errors)
        assert any(e['loc'] == ('cloudwatch',) for e in errors)


class TestConfigEdgeCases:
    """구성 모델 엣지 케이스 테스트"""
    
    def test_very_long_access_key(self):
        """매우 긴 액세스 키 테스트"""
        # AWS 액세스 키는 일반적으로 20자이지만, 최대 128자까지 허용
        long_key = "A" * 128
        
        config = BedrockConfig(
            aws_access_key_id=long_key,
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1"
        )
        
        assert config.aws_access_key_id == long_key
    
    def test_access_key_too_long(self):
        """너무 긴 액세스 키 테스트 (128자 초과)"""
        too_long_key = "A" * 129
        
        with pytest.raises(ValidationError) as exc_info:
            BedrockConfig(
                aws_access_key_id=too_long_key,
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-east-1"
            )
        
        errors = exc_info.value.errors()
        assert any('aws_access_key_id' in str(e['loc']) for e in errors)
    
    def test_access_key_too_short(self):
        """너무 짧은 액세스 키 테스트 (16자 미만)"""
        short_key = "SHORT"
        
        with pytest.raises(ValidationError) as exc_info:
            BedrockConfig(
                aws_access_key_id=short_key,
                aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-east-1"
            )
        
        errors = exc_info.value.errors()
        assert any('aws_access_key_id' in str(e['loc']) for e in errors)
    
    def test_special_characters_in_api_key(self):
        """API 키에 특수 문자 포함 테스트"""
        special_key = "eyJrIjoiVGVzdCJ9!@#$%^&*()_+-=[]{}|;:',.<>?/"
        
        config = GrafanaConfig(
            url="https://grafana.example.com",
            api_key=special_key
        )
        
        assert config.api_key == special_key
    
    def test_url_with_port(self):
        """포트 번호가 포함된 URL 테스트"""
        config = GrafanaConfig(
            url="https://grafana.example.com:8443",
            api_key="test-api-key"
        )
        
        assert config.url == "https://grafana.example.com:8443"
    
    def test_url_with_path(self):
        """경로가 포함된 URL 테스트"""
        config = GrafanaConfig(
            url="https://example.com/grafana",
            api_key="test-api-key"
        )
        
        assert config.url == "https://example.com/grafana"
    
    def test_boundary_temperature_values(self):
        """경계값 temperature 테스트"""
        # temperature = 0.0 (최소값)
        config1 = BedrockConfig(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            temperature=0.0
        )
        assert config1.temperature == 0.0
        
        # temperature = 1.0 (최대값)
        config2 = BedrockConfig(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            temperature=1.0
        )
        assert config2.temperature == 1.0
    
    def test_boundary_max_tokens_values(self):
        """경계값 max_tokens 테스트"""
        # max_tokens = 1 (최소값)
        config1 = BedrockConfig(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            max_tokens=1
        )
        assert config1.max_tokens == 1
        
        # max_tokens = 200000 (최대값)
        config2 = BedrockConfig(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            max_tokens=200000
        )
        assert config2.max_tokens == 200000


# =============================================================================
# 구성 로더 테스트 (Task 3.2, 3.4)
# =============================================================================

import os
from backend.config import (
    ConfigLoader,
    ConfigurationError,
    load_config_from_env,
    get_required_env_variables,
    validate_env_variables,
    BEDROCK_ENV_MAPPING,
    GRAFANA_ENV_MAPPING,
    CLOUDWATCH_ENV_MAPPING
)


class TestConfigurationError:
    """ConfigurationError 예외 클래스 테스트"""
    
    def test_configuration_error_with_missing_variables(self):
        """누락된 변수 목록이 포함된 오류 메시지 테스트"""
        missing_vars = [
            {"env_name": "AWS_ACCESS_KEY_ID", "description": "AWS 액세스 키", "section": "Bedrock"},
            {"env_name": "GRAFANA_URL", "description": "Grafana URL", "section": "Grafana"}
        ]
        
        error = ConfigurationError(
            message="테스트 오류",
            missing_variables=missing_vars
        )
        
        error_str = str(error)
        assert "테스트 오류" in error_str
        assert "AWS_ACCESS_KEY_ID" in error_str
        assert "GRAFANA_URL" in error_str
        assert "누락된 필수 환경 변수" in error_str
        assert "해결 방법" in error_str
    
    def test_configuration_error_with_validation_errors(self):
        """검증 오류 목록이 포함된 오류 메시지 테스트"""
        validation_errors = [
            {"field": "Bedrock.temperature", "message": "유효한 실수가 아닙니다"},
            {"field": "Bedrock.max_tokens", "message": "유효한 정수가 아닙니다"}
        ]
        
        error = ConfigurationError(
            message="검증 실패",
            validation_errors=validation_errors
        )
        
        error_str = str(error)
        assert "검증 실패" in error_str
        assert "Bedrock.temperature" in error_str
        assert "Bedrock.max_tokens" in error_str
        assert "검증 오류" in error_str
    
    def test_configuration_error_attributes(self):
        """ConfigurationError 속성 테스트"""
        missing_vars = [{"env_name": "TEST_VAR", "description": "테스트", "section": "Test"}]
        validation_errors = [{"field": "test", "message": "오류"}]
        
        error = ConfigurationError(
            message="테스트",
            missing_variables=missing_vars,
            validation_errors=validation_errors
        )
        
        assert error.message == "테스트"
        assert len(error.missing_variables) == 1
        assert len(error.validation_errors) == 1


class TestConfigLoader:
    """ConfigLoader 클래스 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """테스트 전 환경 변수 초기화"""
        # 모든 관련 환경 변수 제거
        env_vars_to_clear = [
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION",
            "BEDROCK_MODEL_ID", "BEDROCK_TEMPERATURE", "BEDROCK_MAX_TOKENS",
            "GRAFANA_URL", "GRAFANA_API_KEY",
            "CLOUDWATCH_AWS_ACCESS_KEY_ID", "CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "CLOUDWATCH_REGION",
            "DATABASE_PATH"
        ]
        for var in env_vars_to_clear:
            monkeypatch.delenv(var, raising=False)
    
    def test_load_valid_config(self, monkeypatch):
        """유효한 구성 로드 테스트"""
        # 모든 필수 환경 변수 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")
        
        loader = ConfigLoader()
        config = loader.load()
        
        assert config.bedrock.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.bedrock.region == "us-east-1"
        assert config.grafana.url == "https://grafana.example.com"
        assert config.cloudwatch.region == "us-west-2"
        assert config.database.path == "chatbot.db"  # 기본값
    
    def test_load_config_with_optional_values(self, monkeypatch):
        """선택적 값이 포함된 구성 로드 테스트"""
        # 필수 환경 변수 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")
        
        # 선택적 환경 변수 설정
        monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-opus")
        monkeypatch.setenv("BEDROCK_TEMPERATURE", "0.5")
        monkeypatch.setenv("BEDROCK_MAX_TOKENS", "8192")
        monkeypatch.setenv("DATABASE_PATH", "/custom/path/db.sqlite")
        
        loader = ConfigLoader()
        config = loader.load()
        
        assert config.bedrock.model_id == "anthropic.claude-3-opus"
        assert config.bedrock.temperature == 0.5
        assert config.bedrock.max_tokens == 8192
        assert config.database.path == "/custom/path/db.sqlite"
    
    def test_load_config_missing_required_variables(self, monkeypatch):
        """필수 환경 변수 누락 시 오류 테스트"""
        # 일부 필수 변수만 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        # AWS_SECRET_ACCESS_KEY, AWS_REGION 누락
        
        loader = ConfigLoader()
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load()
        
        error = exc_info.value
        assert "필수 환경 변수가 누락" in error.message
        assert len(error.missing_variables) > 0
        
        # 누락된 변수 확인
        missing_env_names = [v["env_name"] for v in error.missing_variables]
        assert "AWS_SECRET_ACCESS_KEY" in missing_env_names
        assert "AWS_REGION" in missing_env_names
    
    def test_load_config_invalid_temperature(self, monkeypatch):
        """잘못된 temperature 값 테스트"""
        # 모든 필수 환경 변수 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")
        
        # 잘못된 temperature 값
        monkeypatch.setenv("BEDROCK_TEMPERATURE", "not_a_number")
        
        loader = ConfigLoader()
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load()
        
        error = exc_info.value
        assert "환경 변수 값이 올바르지 않습니다" in error.message
        assert any("temperature" in e["field"] for e in error.validation_errors)
    
    def test_load_config_invalid_max_tokens(self, monkeypatch):
        """잘못된 max_tokens 값 테스트"""
        # 모든 필수 환경 변수 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")
        
        # 잘못된 max_tokens 값
        monkeypatch.setenv("BEDROCK_MAX_TOKENS", "invalid")
        
        loader = ConfigLoader()
        
        with pytest.raises(ConfigurationError) as exc_info:
            loader.load()
        
        error = exc_info.value
        assert any("max_tokens" in e["field"] for e in error.validation_errors)
    
    def test_load_config_whitespace_handling(self, monkeypatch):
        """환경 변수 공백 처리 테스트"""
        # 공백이 포함된 환경 변수 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "  AKIAIOSFODNN7EXAMPLE  ")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "  wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  ")
        monkeypatch.setenv("AWS_REGION", "  us-east-1  ")
        monkeypatch.setenv("GRAFANA_URL", "  https://grafana.example.com  ")
        monkeypatch.setenv("GRAFANA_API_KEY", "  test-api-key  ")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "  AKIAIOSFODNN7EXAMPLE  ")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "  wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  ")
        monkeypatch.setenv("CLOUDWATCH_REGION", "  us-west-2  ")
        
        loader = ConfigLoader()
        config = loader.load()
        
        # 공백이 제거되었는지 확인
        assert config.bedrock.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.bedrock.region == "us-east-1"
        assert config.grafana.url == "https://grafana.example.com"


class TestLoadConfigFromEnv:
    """load_config_from_env 함수 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """테스트 전 환경 변수 초기화"""
        env_vars_to_clear = [
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION",
            "BEDROCK_MODEL_ID", "BEDROCK_TEMPERATURE", "BEDROCK_MAX_TOKENS",
            "GRAFANA_URL", "GRAFANA_API_KEY",
            "CLOUDWATCH_AWS_ACCESS_KEY_ID", "CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "CLOUDWATCH_REGION",
            "DATABASE_PATH"
        ]
        for var in env_vars_to_clear:
            monkeypatch.delenv(var, raising=False)
    
    def test_load_config_from_env_success(self, monkeypatch):
        """load_config_from_env 성공 테스트"""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")
        
        config = load_config_from_env()
        
        assert config.bedrock.region == "us-east-1"
        assert config.grafana.url == "https://grafana.example.com"
    
    def test_load_config_from_env_failure(self, monkeypatch):
        """load_config_from_env 실패 테스트"""
        # 환경 변수 없이 호출
        with pytest.raises(ConfigurationError):
            load_config_from_env()


class TestGetRequiredEnvVariables:
    """get_required_env_variables 함수 테스트"""
    
    def test_returns_all_required_variables(self):
        """모든 필수 환경 변수 반환 테스트"""
        required_vars = get_required_env_variables()
        
        # 필수 변수 개수 확인 (Bedrock 3개 + Grafana 2개 + CloudWatch 3개 = 8개)
        assert len(required_vars) == 8
        
        # 각 섹션의 필수 변수 확인
        env_names = [v["env_name"] for v in required_vars]
        
        # Bedrock 필수 변수
        assert "AWS_ACCESS_KEY_ID" in env_names
        assert "AWS_SECRET_ACCESS_KEY" in env_names
        assert "AWS_REGION" in env_names
        
        # Grafana 필수 변수
        assert "GRAFANA_URL" in env_names
        assert "GRAFANA_API_KEY" in env_names
        
        # CloudWatch 필수 변수
        assert "CLOUDWATCH_AWS_ACCESS_KEY_ID" in env_names
        assert "CLOUDWATCH_AWS_SECRET_ACCESS_KEY" in env_names
        assert "CLOUDWATCH_REGION" in env_names
    
    def test_variable_info_structure(self):
        """변수 정보 구조 테스트"""
        required_vars = get_required_env_variables()
        
        for var_info in required_vars:
            assert "env_name" in var_info
            assert "description" in var_info
            assert "section" in var_info
            assert var_info["section"] in ["Bedrock", "Grafana", "CloudWatch"]


class TestValidateEnvVariables:
    """validate_env_variables 함수 테스트"""
    
    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """테스트 전 환경 변수 초기화"""
        env_vars_to_clear = [
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION",
            "GRAFANA_URL", "GRAFANA_API_KEY",
            "CLOUDWATCH_AWS_ACCESS_KEY_ID", "CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "CLOUDWATCH_REGION"
        ]
        for var in env_vars_to_clear:
            monkeypatch.delenv(var, raising=False)
    
    def test_all_variables_present(self, monkeypatch):
        """모든 변수가 있을 때 테스트"""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
        monkeypatch.setenv("AWS_REGION", "test")
        monkeypatch.setenv("GRAFANA_URL", "test")
        monkeypatch.setenv("GRAFANA_API_KEY", "test")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "test")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "test")
        monkeypatch.setenv("CLOUDWATCH_REGION", "test")
        
        is_valid, missing = validate_env_variables()
        
        assert is_valid is True
        assert len(missing) == 0
    
    def test_some_variables_missing(self, monkeypatch):
        """일부 변수가 누락되었을 때 테스트"""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
        # 나머지 변수 누락
        
        is_valid, missing = validate_env_variables()
        
        assert is_valid is False
        assert len(missing) == 7  # 8개 중 1개만 설정됨
        
        missing_env_names = [v["env_name"] for v in missing]
        assert "AWS_SECRET_ACCESS_KEY" in missing_env_names
        assert "AWS_REGION" in missing_env_names
    
    def test_empty_string_treated_as_missing(self, monkeypatch):
        """빈 문자열이 누락으로 처리되는지 테스트"""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "   ")  # 공백만
        
        is_valid, missing = validate_env_variables()
        
        assert is_valid is False
        missing_env_names = [v["env_name"] for v in missing]
        assert "AWS_ACCESS_KEY_ID" in missing_env_names
        assert "AWS_SECRET_ACCESS_KEY" in missing_env_names


class TestConfigLoaderDescriptiveErrors:
    """설명적인 오류 메시지 테스트 (요구사항 8.5)"""
    
    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """테스트 전 환경 변수 초기화"""
        env_vars_to_clear = [
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION",
            "BEDROCK_MODEL_ID", "BEDROCK_TEMPERATURE", "BEDROCK_MAX_TOKENS",
            "GRAFANA_URL", "GRAFANA_API_KEY",
            "CLOUDWATCH_AWS_ACCESS_KEY_ID", "CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "CLOUDWATCH_REGION",
            "DATABASE_PATH"
        ]
        for var in env_vars_to_clear:
            monkeypatch.delenv(var, raising=False)
    
    def test_error_message_includes_variable_name(self, monkeypatch):
        """오류 메시지에 변수 이름이 포함되는지 테스트"""
        # 일부 변수만 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error_str = str(exc_info.value)
        assert "AWS_SECRET_ACCESS_KEY" in error_str
        assert "AWS_REGION" in error_str
    
    def test_error_message_includes_description(self, monkeypatch):
        """오류 메시지에 변수 설명이 포함되는지 테스트"""
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error_str = str(exc_info.value)
        # 설명이 포함되어 있는지 확인
        assert "Bedrock" in error_str or "Grafana" in error_str or "CloudWatch" in error_str
    
    def test_error_message_includes_resolution_steps(self, monkeypatch):
        """오류 메시지에 해결 방법이 포함되는지 테스트"""
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error_str = str(exc_info.value)
        assert "해결 방법" in error_str
        assert ".env.example" in error_str
    
    def test_pydantic_validation_error_converted(self, monkeypatch):
        """Pydantic 검증 오류가 설명적인 메시지로 변환되는지 테스트"""
        # 모든 필수 환경 변수 설정 (하지만 잘못된 형식)
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "short")  # 너무 짧음
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        # Pydantic 검증 오류가 ConfigurationError로 변환됨
        assert "구성 검증에 실패" in error.message or len(error.validation_errors) > 0
