"""
구성 파싱 단위 테스트 (Task 3.4)

이 모듈은 구성 파싱 및 로딩에 대한 단위 테스트를 포함합니다.
- 유효한 구성 로딩 테스트
- 누락된 필수 변수 테스트
- 잘못된 자격 증명 형식 테스트

요구사항: 8.1, 8.2, 8.3, 8.5
"""

import pytest
from pydantic import ValidationError
from backend.config import (
    BedrockConfig,
    GrafanaConfig,
    CloudWatchConfig,
    DatabaseConfig,
    AppConfig,
    ConfigLoader,
    ConfigurationError,
    load_config_from_env,
    get_required_env_variables,
    validate_env_variables,
)


# =============================================================================
# 유효한 구성 로딩 테스트 (요구사항 8.1, 8.2, 8.3)
# =============================================================================

class TestValidConfigurationLoading:
    """유효한 구성 로딩 테스트 클래스"""
    
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

    def _set_all_required_env_vars(self, monkeypatch):
        """모든 필수 환경 변수를 설정하는 헬퍼 메서드"""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key-12345")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")
    
    def test_load_complete_valid_config_from_env(self, monkeypatch):
        """
        .env 파일에서 완전한 유효 구성 로딩 테스트
        
        검증: 요구사항 8.1 - THE System SHALL .env 파일에서 구성을 읽어야 한다
        """
        self._set_all_required_env_vars(monkeypatch)
        
        config = load_config_from_env()
        
        # Bedrock 구성 검증
        assert config.bedrock is not None
        assert config.bedrock.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.bedrock.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert config.bedrock.region == "us-east-1"
        
        # Grafana 구성 검증
        assert config.grafana is not None
        assert config.grafana.url == "https://grafana.example.com"
        assert config.grafana.api_key == "test-api-key-12345"
        
        # CloudWatch 구성 검증
        assert config.cloudwatch is not None
        assert config.cloudwatch.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.cloudwatch.region == "us-west-2"
        
        # Database 기본값 검증
        assert config.database is not None
        assert config.database.path == "chatbot.db"

    def test_load_aws_credentials_from_env(self, monkeypatch):
        """
        환경 변수를 통한 AWS 자격 증명 로딩 테스트
        
        검증: 요구사항 8.2 - THE Backend SHALL 환경 변수를 통해 AWS 자격 증명을 수락해야 한다
        """
        self._set_all_required_env_vars(monkeypatch)
        
        config = load_config_from_env()
        
        # Bedrock AWS 자격 증명 검증
        assert config.bedrock.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.bedrock.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        
        # CloudWatch AWS 자격 증명 검증
        assert config.cloudwatch.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.cloudwatch.aws_secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    
    def test_load_bedrock_endpoint_and_model_params_from_env(self, monkeypatch):
        """
        환경 변수를 통한 Bedrock 엔드포인트 및 모델 매개변수 로딩 테스트
        
        검증: 요구사항 8.3 - THE Backend SHALL 환경 변수를 통해 Bedrock 엔드포인트 및 모델 매개변수를 수락해야 한다
        """
        self._set_all_required_env_vars(monkeypatch)
        
        # 선택적 Bedrock 매개변수 설정
        monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-opus")
        monkeypatch.setenv("BEDROCK_TEMPERATURE", "0.5")
        monkeypatch.setenv("BEDROCK_MAX_TOKENS", "8192")
        
        config = load_config_from_env()
        
        # Bedrock 모델 매개변수 검증
        assert config.bedrock.region == "us-east-1"  # 엔드포인트 리전
        assert config.bedrock.model_id == "anthropic.claude-3-opus"
        assert config.bedrock.temperature == 0.5
        assert config.bedrock.max_tokens == 8192

    def test_load_config_with_default_optional_values(self, monkeypatch):
        """
        선택적 값이 기본값으로 설정되는지 테스트
        
        검증: 요구사항 8.1, 8.3
        """
        self._set_all_required_env_vars(monkeypatch)
        
        config = load_config_from_env()
        
        # Bedrock 기본값 검증
        assert config.bedrock.model_id == "anthropic.claude-sonnet-4-5"
        assert config.bedrock.temperature == 0.7
        assert config.bedrock.max_tokens == 4096
        
        # Database 기본값 검증
        assert config.database.path == "chatbot.db"
    
    def test_load_config_with_custom_database_path(self, monkeypatch):
        """
        사용자 정의 데이터베이스 경로 로딩 테스트
        
        검증: 요구사항 8.1
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("DATABASE_PATH", "/app/data/custom.db")
        
        config = load_config_from_env()
        
        assert config.database.path == "/app/data/custom.db"
    
    def test_load_config_with_different_regions(self, monkeypatch):
        """
        다양한 AWS 리전 로딩 테스트
        
        검증: 요구사항 8.2, 8.3
        """
        self._set_all_required_env_vars(monkeypatch)
        
        # 다른 리전 설정
        monkeypatch.setenv("AWS_REGION", "ap-northeast-2")  # 서울
        monkeypatch.setenv("CLOUDWATCH_REGION", "eu-west-1")  # 아일랜드
        
        config = load_config_from_env()
        
        assert config.bedrock.region == "ap-northeast-2"
        assert config.cloudwatch.region == "eu-west-1"


# =============================================================================
# 누락된 필수 변수 테스트 (요구사항 8.5)
# =============================================================================

class TestMissingRequiredVariables:
    """누락된 필수 변수 테스트 클래스"""
    
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
    
    def test_missing_all_required_variables_fails_with_descriptive_error(self, monkeypatch):
        """
        모든 필수 변수 누락 시 설명적인 오류 메시지와 함께 시작 실패 테스트
        
        검증: 요구사항 8.5 - WHEN 필수 환경 변수가 누락되면, 
              THE Backend SHALL 설명적인 오류 메시지와 함께 시작 실패해야 한다
        """
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        error_str = str(error)
        
        # 오류 메시지에 누락된 변수 정보가 포함되어야 함
        assert "필수 환경 변수가 누락" in error.message
        assert len(error.missing_variables) > 0
        
        # 해결 방법이 포함되어야 함
        assert "해결 방법" in error_str
        assert ".env.example" in error_str

    def test_missing_bedrock_credentials_fails(self, monkeypatch):
        """
        Bedrock AWS 자격 증명 누락 시 실패 테스트
        
        검증: 요구사항 8.2, 8.5
        """
        # Grafana와 CloudWatch만 설정
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        missing_env_names = [v["env_name"] for v in error.missing_variables]
        
        # Bedrock 관련 변수가 누락 목록에 있어야 함
        assert "AWS_ACCESS_KEY_ID" in missing_env_names
        assert "AWS_SECRET_ACCESS_KEY" in missing_env_names
        assert "AWS_REGION" in missing_env_names
    
    def test_missing_grafana_config_fails(self, monkeypatch):
        """
        Grafana 구성 누락 시 실패 테스트
        
        검증: 요구사항 8.5
        """
        # Bedrock과 CloudWatch만 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        missing_env_names = [v["env_name"] for v in error.missing_variables]
        
        # Grafana 관련 변수가 누락 목록에 있어야 함
        assert "GRAFANA_URL" in missing_env_names
        assert "GRAFANA_API_KEY" in missing_env_names

    def test_missing_cloudwatch_config_fails(self, monkeypatch):
        """
        CloudWatch 구성 누락 시 실패 테스트
        
        검증: 요구사항 8.5
        """
        # Bedrock과 Grafana만 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key")
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        missing_env_names = [v["env_name"] for v in error.missing_variables]
        
        # CloudWatch 관련 변수가 누락 목록에 있어야 함
        assert "CLOUDWATCH_AWS_ACCESS_KEY_ID" in missing_env_names
        assert "CLOUDWATCH_AWS_SECRET_ACCESS_KEY" in missing_env_names
        assert "CLOUDWATCH_REGION" in missing_env_names
    
    def test_missing_single_required_variable_fails(self, monkeypatch):
        """
        단일 필수 변수 누락 시 실패 테스트
        
        검증: 요구사항 8.5
        """
        # AWS_SECRET_ACCESS_KEY만 누락
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        # AWS_SECRET_ACCESS_KEY 누락
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        missing_env_names = [v["env_name"] for v in error.missing_variables]
        
        assert "AWS_SECRET_ACCESS_KEY" in missing_env_names
        assert len(error.missing_variables) == 1

    def test_empty_string_treated_as_missing(self, monkeypatch):
        """
        빈 문자열이 누락으로 처리되는지 테스트
        
        검증: 요구사항 8.5
        """
        # 빈 문자열로 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "")
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
        missing_env_names = [v["env_name"] for v in error.missing_variables]
        
        assert "AWS_ACCESS_KEY_ID" in missing_env_names
    
    def test_whitespace_only_treated_as_missing(self, monkeypatch):
        """
        공백만 있는 값이 누락으로 처리되는지 테스트
        
        검증: 요구사항 8.5
        """
        # 공백만 있는 값으로 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "   ")
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
        missing_env_names = [v["env_name"] for v in error.missing_variables]
        
        assert "AWS_ACCESS_KEY_ID" in missing_env_names

    def test_error_message_lists_all_missing_variables(self, monkeypatch):
        """
        오류 메시지에 모든 누락된 변수가 나열되는지 테스트
        
        검증: 요구사항 8.5
        """
        # 여러 변수 누락
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        # AWS_SECRET_ACCESS_KEY, AWS_REGION 누락
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        # GRAFANA_API_KEY 누락
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        # CLOUDWATCH_REGION 누락
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        error_str = str(error)
        
        # 모든 누락된 변수가 오류 메시지에 포함되어야 함
        assert "AWS_SECRET_ACCESS_KEY" in error_str
        assert "AWS_REGION" in error_str
        assert "GRAFANA_API_KEY" in error_str
        assert "CLOUDWATCH_REGION" in error_str


# =============================================================================
# 잘못된 자격 증명 형식 테스트 (요구사항 8.2, 8.5)
# =============================================================================

class TestInvalidCredentialsFormat:
    """잘못된 자격 증명 형식 테스트 클래스"""
    
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

    def _set_all_required_env_vars(self, monkeypatch):
        """모든 필수 환경 변수를 설정하는 헬퍼 메서드"""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key-12345")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")
    
    def test_aws_access_key_too_short_fails(self, monkeypatch):
        """
        AWS 액세스 키가 너무 짧을 때 실패 테스트 (16자 미만)
        
        검증: 요구사항 8.2, 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "SHORT")  # 5자 - 너무 짧음
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        # 검증 오류가 발생해야 함
        assert "구성 검증에 실패" in error.message or len(error.validation_errors) > 0
    
    def test_aws_access_key_too_long_fails(self, monkeypatch):
        """
        AWS 액세스 키가 너무 길 때 실패 테스트 (128자 초과)
        
        검증: 요구사항 8.2, 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "A" * 129)  # 129자 - 너무 김
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        assert "구성 검증에 실패" in error.message or len(error.validation_errors) > 0

    def test_aws_secret_key_too_short_fails(self, monkeypatch):
        """
        AWS 시크릿 키가 너무 짧을 때 실패 테스트 (16자 미만)
        
        검증: 요구사항 8.2, 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "SHORT")  # 5자 - 너무 짧음
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        assert "구성 검증에 실패" in error.message or len(error.validation_errors) > 0
    
    def test_cloudwatch_access_key_too_short_fails(self, monkeypatch):
        """
        CloudWatch AWS 액세스 키가 너무 짧을 때 실패 테스트
        
        검증: 요구사항 8.2, 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "SHORT")  # 너무 짧음
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        assert "구성 검증에 실패" in error.message or len(error.validation_errors) > 0
    
    def test_grafana_url_invalid_format_fails(self, monkeypatch):
        """
        Grafana URL이 잘못된 형식일 때 실패 테스트 (http:// 또는 https:// 없음)
        
        검증: 요구사항 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("GRAFANA_URL", "grafana.example.com")  # 프로토콜 없음
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        assert "구성 검증에 실패" in error.message or len(error.validation_errors) > 0

    def test_invalid_temperature_format_fails(self, monkeypatch):
        """
        temperature가 숫자가 아닐 때 실패 테스트
        
        검증: 요구사항 8.3, 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("BEDROCK_TEMPERATURE", "not_a_number")
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        assert any("temperature" in e["field"] for e in error.validation_errors)
    
    def test_temperature_out_of_range_fails(self, monkeypatch):
        """
        temperature가 범위를 벗어날 때 실패 테스트 (0.0-1.0)
        
        검증: 요구사항 8.3, 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("BEDROCK_TEMPERATURE", "1.5")  # 1.0 초과
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        assert "구성 검증에 실패" in error.message or len(error.validation_errors) > 0
    
    def test_invalid_max_tokens_format_fails(self, monkeypatch):
        """
        max_tokens가 정수가 아닐 때 실패 테스트
        
        검증: 요구사항 8.3, 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("BEDROCK_MAX_TOKENS", "invalid")
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        assert any("max_tokens" in e["field"] for e in error.validation_errors)

    def test_max_tokens_out_of_range_fails(self, monkeypatch):
        """
        max_tokens가 범위를 벗어날 때 실패 테스트 (1-200000)
        
        검증: 요구사항 8.3, 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("BEDROCK_MAX_TOKENS", "0")  # 0 이하
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        assert "구성 검증에 실패" in error.message or len(error.validation_errors) > 0
    
    def test_negative_temperature_fails(self, monkeypatch):
        """
        음수 temperature 실패 테스트
        
        검증: 요구사항 8.3, 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("BEDROCK_TEMPERATURE", "-0.5")
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        assert "구성 검증에 실패" in error.message or len(error.validation_errors) > 0
    
    def test_empty_grafana_api_key_fails(self, monkeypatch):
        """
        빈 Grafana API 키 실패 테스트
        
        검증: 요구사항 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("GRAFANA_API_KEY", "")
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        missing_env_names = [v["env_name"] for v in error.missing_variables]
        assert "GRAFANA_API_KEY" in missing_env_names

    def test_empty_aws_region_fails(self, monkeypatch):
        """
        빈 AWS 리전 실패 테스트
        
        검증: 요구사항 8.2, 8.5
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("AWS_REGION", "")
        
        with pytest.raises(ConfigurationError) as exc_info:
            load_config_from_env()
        
        error = exc_info.value
        missing_env_names = [v["env_name"] for v in error.missing_variables]
        assert "AWS_REGION" in missing_env_names


# =============================================================================
# 추가 엣지 케이스 테스트
# =============================================================================

class TestConfigParsingEdgeCases:
    """구성 파싱 엣지 케이스 테스트"""
    
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
    
    def _set_all_required_env_vars(self, monkeypatch):
        """모든 필수 환경 변수를 설정하는 헬퍼 메서드"""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com")
        monkeypatch.setenv("GRAFANA_API_KEY", "test-api-key-12345")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
        monkeypatch.setenv("CLOUDWATCH_REGION", "us-west-2")

    def test_whitespace_trimmed_from_values(self, monkeypatch):
        """
        환경 변수 값에서 공백이 제거되는지 테스트
        
        검증: 요구사항 8.1
        """
        # 공백이 포함된 값 설정
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "  AKIAIOSFODNN7EXAMPLE  ")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "  wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  ")
        monkeypatch.setenv("AWS_REGION", "  us-east-1  ")
        monkeypatch.setenv("GRAFANA_URL", "  https://grafana.example.com  ")
        monkeypatch.setenv("GRAFANA_API_KEY", "  test-api-key  ")
        monkeypatch.setenv("CLOUDWATCH_AWS_ACCESS_KEY_ID", "  AKIAIOSFODNN7EXAMPLE  ")
        monkeypatch.setenv("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "  wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY  ")
        monkeypatch.setenv("CLOUDWATCH_REGION", "  us-west-2  ")
        
        config = load_config_from_env()
        
        # 공백이 제거되었는지 확인
        assert config.bedrock.aws_access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert config.bedrock.region == "us-east-1"
        assert config.grafana.url == "https://grafana.example.com"
        assert config.grafana.api_key == "test-api-key"
        assert config.cloudwatch.region == "us-west-2"
    
    def test_grafana_url_trailing_slash_removed(self, monkeypatch):
        """
        Grafana URL의 후행 슬래시가 제거되는지 테스트
        
        검증: 요구사항 8.1
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com/")
        
        config = load_config_from_env()
        
        assert config.grafana.url == "https://grafana.example.com"

    def test_boundary_temperature_values_accepted(self, monkeypatch):
        """
        경계값 temperature가 허용되는지 테스트 (0.0, 1.0)
        
        검증: 요구사항 8.3
        """
        self._set_all_required_env_vars(monkeypatch)
        
        # 최소값 테스트
        monkeypatch.setenv("BEDROCK_TEMPERATURE", "0.0")
        config = load_config_from_env()
        assert config.bedrock.temperature == 0.0
        
        # 최대값 테스트
        monkeypatch.setenv("BEDROCK_TEMPERATURE", "1.0")
        config = load_config_from_env()
        assert config.bedrock.temperature == 1.0
    
    def test_boundary_max_tokens_values_accepted(self, monkeypatch):
        """
        경계값 max_tokens가 허용되는지 테스트 (1, 200000)
        
        검증: 요구사항 8.3
        """
        self._set_all_required_env_vars(monkeypatch)
        
        # 최소값 테스트
        monkeypatch.setenv("BEDROCK_MAX_TOKENS", "1")
        config = load_config_from_env()
        assert config.bedrock.max_tokens == 1
        
        # 최대값 테스트
        monkeypatch.setenv("BEDROCK_MAX_TOKENS", "200000")
        config = load_config_from_env()
        assert config.bedrock.max_tokens == 200000
    
    def test_special_characters_in_api_key_accepted(self, monkeypatch):
        """
        API 키에 특수 문자가 포함되어도 허용되는지 테스트
        
        검증: 요구사항 8.1
        """
        self._set_all_required_env_vars(monkeypatch)
        special_key = "eyJrIjoiVGVzdCJ9!@#$%^&*()_+-=[]{}|;:',.<>?/"
        monkeypatch.setenv("GRAFANA_API_KEY", special_key)
        
        config = load_config_from_env()
        
        assert config.grafana.api_key == special_key

    def test_grafana_url_with_port_accepted(self, monkeypatch):
        """
        포트 번호가 포함된 Grafana URL이 허용되는지 테스트
        
        검증: 요구사항 8.1
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("GRAFANA_URL", "https://grafana.example.com:8443")
        
        config = load_config_from_env()
        
        assert config.grafana.url == "https://grafana.example.com:8443"
    
    def test_grafana_url_with_path_accepted(self, monkeypatch):
        """
        경로가 포함된 Grafana URL이 허용되는지 테스트
        
        검증: 요구사항 8.1
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("GRAFANA_URL", "https://example.com/grafana")
        
        config = load_config_from_env()
        
        assert config.grafana.url == "https://example.com/grafana"
    
    def test_http_grafana_url_accepted(self, monkeypatch):
        """
        HTTP Grafana URL이 허용되는지 테스트
        
        검증: 요구사항 8.1
        """
        self._set_all_required_env_vars(monkeypatch)
        monkeypatch.setenv("GRAFANA_URL", "http://grafana.local:3000")
        
        config = load_config_from_env()
        
        assert config.grafana.url == "http://grafana.local:3000"
    
    def test_config_loader_can_be_reused(self, monkeypatch):
        """
        ConfigLoader가 재사용 가능한지 테스트
        
        검증: 요구사항 8.1
        """
        self._set_all_required_env_vars(monkeypatch)
        
        loader = ConfigLoader()
        
        # 첫 번째 로드
        config1 = loader.load()
        assert config1.bedrock.region == "us-east-1"
        
        # 환경 변수 변경
        monkeypatch.setenv("AWS_REGION", "ap-northeast-2")
        
        # 두 번째 로드 (새 값 반영)
        config2 = loader.load()
        assert config2.bedrock.region == "ap-northeast-2"
