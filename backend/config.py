"""
구성 관리 - Pydantic 모델 및 환경 변수 로더

이 모듈은 환경 변수에서 로드되는 애플리케이션 구성을 위한 Pydantic 모델을 정의합니다.
모든 구성은 타입 검증 및 필수 필드 확인을 거칩니다.

주요 기능:
- Pydantic 모델을 사용한 구성 정의 및 검증
- 환경 변수에서 구성 로드
- 누락된 필수 변수에 대한 설명적인 오류 메시지

요구사항: 4.4, 8.1, 8.2, 8.3, 8.5
"""

from pydantic import BaseModel, Field, field_validator, ValidationError
from typing import Optional, List, Dict, Any
import logging
import os

# 로거 설정
logger = logging.getLogger(__name__)


class BedrockConfig(BaseModel):
    """
    AWS Bedrock 구성 모델
    
    Claude Sonnet 4.5 모델에 액세스하기 위한 AWS Bedrock 설정을 포함합니다.
    
    Attributes:
        aws_access_key_id: AWS 액세스 키 ID
        aws_secret_access_key: AWS 시크릿 액세스 키
        region: AWS 리전 (예: us-east-1)
        model_id: Bedrock 모델 식별자 (기본값: anthropic.claude-sonnet-4-5)
        temperature: 모델 온도 파라미터 (0.0-1.0, 기본값: 0.7)
        max_tokens: 최대 생성 토큰 수 (기본값: 4096)
    
    요구사항: 4.4, 8.2, 8.3
    """
    
    aws_access_key_id: str = Field(
        ...,
        description="AWS 액세스 키 ID",
        min_length=16,
        max_length=128
    )
    
    aws_secret_access_key: str = Field(
        ...,
        description="AWS 시크릿 액세스 키",
        min_length=16
    )
    
    region: str = Field(
        ...,
        description="AWS 리전",
        min_length=1
    )
    
    model_id: str = Field(
        default="anthropic.claude-sonnet-4-5",
        description="Bedrock 모델 식별자"
    )
    
    temperature: float = Field(
        default=0.7,
        description="모델 온도 파라미터 (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    max_tokens: int = Field(
        default=4096,
        description="최대 생성 토큰 수",
        gt=0,
        le=200000
    )
    
    @field_validator('region')
    @classmethod
    def validate_region(cls, v: str) -> str:
        """
        AWS 리전 형식 검증
        
        Args:
            v: 리전 문자열
        
        Returns:
            str: 검증된 리전 문자열
        
        Raises:
            ValueError: 잘못된 리전 형식
        """
        if not v or len(v.strip()) == 0:
            raise ValueError("리전은 비어있을 수 없습니다")
        
        valid_prefixes = ['us-', 'eu-', 'ap-', 'sa-', 'ca-', 'me-', 'af-']
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            logger.warning(f"비표준 AWS 리전 형식: {v}")
        
        return v.strip()
    
    @field_validator('model_id')
    @classmethod
    def validate_model_id(cls, v: str) -> str:
        """
        모델 ID 형식 검증
        
        Args:
            v: 모델 ID 문자열
        
        Returns:
            str: 검증된 모델 ID 문자열
        
        Raises:
            ValueError: 잘못된 모델 ID 형식
        """
        if not v or len(v.strip()) == 0:
            raise ValueError("모델 ID는 비어있을 수 없습니다")
        
        return v.strip()
    
    class Config:
        """Pydantic 모델 구성"""
        str_strip_whitespace = True
        validate_assignment = True


class GrafanaConfig(BaseModel):
    """
    Grafana MCP 서버 구성 모델
    
    Grafana 인스턴스에 연결하기 위한 설정을 포함합니다.
    
    Attributes:
        url: Grafana 인스턴스 URL (예: https://grafana.example.com)
        api_key: Grafana API 키
    
    요구사항: 8.2, 8.3
    """
    
    url: str = Field(
        ...,
        description="Grafana 인스턴스 URL",
        min_length=1
    )
    
    api_key: str = Field(
        ...,
        description="Grafana API 키",
        min_length=1
    )
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """
        Grafana URL 형식 검증
        
        Args:
            v: URL 문자열
        
        Returns:
            str: 검증된 URL 문자열
        
        Raises:
            ValueError: 잘못된 URL 형식
        """
        v = v.strip()
        
        if not v:
            raise ValueError("Grafana URL은 비어있을 수 없습니다")
        
        if not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError("Grafana URL은 http:// 또는 https://로 시작해야 합니다")
        
        return v.rstrip('/')
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """
        API 키 형식 검증
        
        Args:
            v: API 키 문자열
        
        Returns:
            str: 검증된 API 키 문자열
        
        Raises:
            ValueError: 잘못된 API 키 형식
        """
        v = v.strip()
        
        if not v:
            raise ValueError("Grafana API 키는 비어있을 수 없습니다")
        
        return v
    
    class Config:
        """Pydantic 모델 구성"""
        str_strip_whitespace = True
        validate_assignment = True


class CloudWatchConfig(BaseModel):
    """
    CloudWatch MCP 서버 구성 모델
    
    AWS CloudWatch에 연결하기 위한 설정을 포함합니다.
    
    Attributes:
        aws_access_key_id: AWS 액세스 키 ID
        aws_secret_access_key: AWS 시크릿 액세스 키
        region: AWS 리전 (예: us-east-1)
    
    요구사항: 8.2, 8.3
    """
    
    aws_access_key_id: str = Field(
        ...,
        description="AWS 액세스 키 ID",
        min_length=16,
        max_length=128
    )
    
    aws_secret_access_key: str = Field(
        ...,
        description="AWS 시크릿 액세스 키",
        min_length=16
    )
    
    region: str = Field(
        ...,
        description="AWS 리전",
        min_length=1
    )
    
    @field_validator('region')
    @classmethod
    def validate_region(cls, v: str) -> str:
        """
        AWS 리전 형식 검증
        
        Args:
            v: 리전 문자열
        
        Returns:
            str: 검증된 리전 문자열
        
        Raises:
            ValueError: 잘못된 리전 형식
        """
        if not v or len(v.strip()) == 0:
            raise ValueError("리전은 비어있을 수 없습니다")
        
        valid_prefixes = ['us-', 'eu-', 'ap-', 'sa-', 'ca-', 'me-', 'af-']
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            logger.warning(f"비표준 AWS 리전 형식: {v}")
        
        return v.strip()
    
    class Config:
        """Pydantic 모델 구성"""
        str_strip_whitespace = True
        validate_assignment = True


class DatabaseConfig(BaseModel):
    """
    데이터베이스 구성 모델
    
    SQLite 데이터베이스 연결을 위한 설정을 포함합니다.
    
    Attributes:
        path: SQLite 데이터베이스 파일 경로 (기본값: chatbot.db)
    """
    
    path: str = Field(
        default="chatbot.db",
        description="SQLite 데이터베이스 파일 경로"
    )
    
    @field_validator('path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        """
        데이터베이스 경로 검증
        
        Args:
            v: 경로 문자열
        
        Returns:
            str: 검증된 경로 문자열
        
        Raises:
            ValueError: 잘못된 경로 형식
        """
        v = v.strip()
        
        if not v:
            raise ValueError("데이터베이스 경로는 비어있을 수 없습니다")
        
        return v
    
    class Config:
        """Pydantic 모델 구성"""
        str_strip_whitespace = True
        validate_assignment = True


class AppConfig(BaseModel):
    """
    전체 애플리케이션 구성 모델
    
    모든 하위 구성 모델을 통합합니다.
    
    Attributes:
        bedrock: AWS Bedrock 구성
        grafana: Grafana MCP 서버 구성
        cloudwatch: CloudWatch MCP 서버 구성
        database: 데이터베이스 구성
    """
    
    bedrock: BedrockConfig
    grafana: GrafanaConfig
    cloudwatch: CloudWatchConfig
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    class Config:
        """Pydantic 모델 구성"""
        validate_assignment = True


# =============================================================================
# 환경 변수 매핑 정의
# =============================================================================

# 환경 변수 이름과 구성 필드 간의 매핑
# 형식: (환경 변수 이름, 설명, 필수 여부)
BEDROCK_ENV_MAPPING: Dict[str, tuple] = {
    "aws_access_key_id": ("AWS_ACCESS_KEY_ID", "AWS 액세스 키 ID (Bedrock 인증용)", True),
    "aws_secret_access_key": ("AWS_SECRET_ACCESS_KEY", "AWS 시크릿 액세스 키 (Bedrock 인증용)", True),
    "region": ("AWS_REGION", "AWS 리전 (예: us-east-1)", True),
    "model_id": ("BEDROCK_MODEL_ID", "Bedrock 모델 식별자 (기본값: anthropic.claude-sonnet-4-5)", False),
    "temperature": ("BEDROCK_TEMPERATURE", "모델 온도 파라미터 (0.0-1.0, 기본값: 0.7)", False),
    "max_tokens": ("BEDROCK_MAX_TOKENS", "최대 생성 토큰 수 (기본값: 4096)", False),
}

GRAFANA_ENV_MAPPING: Dict[str, tuple] = {
    "url": ("GRAFANA_URL", "Grafana 인스턴스 URL (예: https://grafana.example.com)", True),
    "api_key": ("GRAFANA_API_KEY", "Grafana API 키", True),
}

CLOUDWATCH_ENV_MAPPING: Dict[str, tuple] = {
    "aws_access_key_id": ("CLOUDWATCH_AWS_ACCESS_KEY_ID", "CloudWatch용 AWS 액세스 키 ID", True),
    "aws_secret_access_key": ("CLOUDWATCH_AWS_SECRET_ACCESS_KEY", "CloudWatch용 AWS 시크릿 액세스 키", True),
    "region": ("CLOUDWATCH_REGION", "CloudWatch AWS 리전 (예: us-east-1)", True),
}

DATABASE_ENV_MAPPING: Dict[str, tuple] = {
    "path": ("DATABASE_PATH", "SQLite 데이터베이스 파일 경로 (기본값: chatbot.db)", False),
}


class ConfigurationError(Exception):
    """
    구성 오류 예외 클래스
    
    환경 변수 로드 또는 검증 중 발생하는 오류를 나타냅니다.
    누락된 변수 목록과 설명적인 오류 메시지를 포함합니다.
    
    Attributes:
        message: 오류 메시지
        missing_variables: 누락된 환경 변수 목록
        validation_errors: Pydantic 검증 오류 목록
    
    요구사항: 8.5
    """
    
    def __init__(
        self,
        message: str,
        missing_variables: Optional[List[Dict[str, str]]] = None,
        validation_errors: Optional[List[Dict[str, Any]]] = None
    ):
        """
        ConfigurationError 초기화
        
        Args:
            message: 오류 메시지
            missing_variables: 누락된 환경 변수 정보 목록
            validation_errors: Pydantic 검증 오류 목록
        """
        self.message = message
        self.missing_variables = missing_variables or []
        self.validation_errors = validation_errors or []
        super().__init__(self._format_error_message())
    
    def _format_error_message(self) -> str:
        """
        설명적인 오류 메시지 생성
        
        Returns:
            str: 포맷된 오류 메시지
        """
        lines = [self.message]
        
        if self.missing_variables:
            lines.append("\n누락된 필수 환경 변수:")
            for var_info in self.missing_variables:
                env_name = var_info.get("env_name", "알 수 없음")
                description = var_info.get("description", "")
                section = var_info.get("section", "")
                lines.append(f"  - {env_name}: {description} [{section}]")
        
        if self.validation_errors:
            lines.append("\n검증 오류:")
            for error in self.validation_errors:
                field = error.get("field", "알 수 없음")
                message = error.get("message", "")
                lines.append(f"  - {field}: {message}")
        
        lines.append("\n해결 방법:")
        lines.append("  1. .env.example 파일을 .env로 복사하세요")
        lines.append("  2. 모든 필수 환경 변수를 실제 값으로 설정하세요")
        lines.append("  3. 환경 변수 형식이 올바른지 확인하세요")
        
        return "\n".join(lines)


class ConfigLoader:
    """
    환경 변수에서 구성을 로드하는 클래스
    
    환경 변수를 읽어 Pydantic 모델로 변환하고 검증합니다.
    누락된 필수 변수에 대해 설명적인 오류 메시지를 제공합니다.
    
    요구사항: 8.1, 8.2, 8.3, 8.5
    """
    
    def __init__(self):
        """ConfigLoader 초기화"""
        self._missing_variables: List[Dict[str, str]] = []
        self._validation_errors: List[Dict[str, Any]] = []
    
    def _get_env_value(
        self,
        env_name: str,
        description: str,
        required: bool,
        section: str,
        default: Optional[str] = None
    ) -> Optional[str]:
        """
        환경 변수 값을 가져옵니다.
        
        Args:
            env_name: 환경 변수 이름
            description: 변수 설명
            required: 필수 여부
            section: 구성 섹션 이름
            default: 기본값
        
        Returns:
            Optional[str]: 환경 변수 값 또는 None
        """
        value = os.environ.get(env_name)
        
        if value is None or value.strip() == "":
            if required:
                self._missing_variables.append({
                    "env_name": env_name,
                    "description": description,
                    "section": section
                })
                return None
            return default
        
        return value.strip()
    
    def _load_bedrock_config(self) -> Optional[Dict[str, Any]]:
        """
        Bedrock 구성을 환경 변수에서 로드합니다.
        
        Returns:
            Optional[Dict[str, Any]]: Bedrock 구성 딕셔너리 또는 None
        """
        config_data = {}
        
        for field_name, (env_name, description, required) in BEDROCK_ENV_MAPPING.items():
            value = self._get_env_value(
                env_name=env_name,
                description=description,
                required=required,
                section="Bedrock"
            )
            
            if value is not None:
                # 숫자 타입 변환
                if field_name == "temperature":
                    try:
                        config_data[field_name] = float(value)
                    except ValueError:
                        self._validation_errors.append({
                            "field": f"Bedrock.{field_name}",
                            "message": f"'{value}'은(는) 유효한 실수가 아닙니다"
                        })
                elif field_name == "max_tokens":
                    try:
                        config_data[field_name] = int(value)
                    except ValueError:
                        self._validation_errors.append({
                            "field": f"Bedrock.{field_name}",
                            "message": f"'{value}'은(는) 유효한 정수가 아닙니다"
                        })
                else:
                    config_data[field_name] = value
        
        return config_data if config_data else None
    
    def _load_grafana_config(self) -> Optional[Dict[str, Any]]:
        """
        Grafana 구성을 환경 변수에서 로드합니다.
        
        Returns:
            Optional[Dict[str, Any]]: Grafana 구성 딕셔너리 또는 None
        """
        config_data = {}
        
        for field_name, (env_name, description, required) in GRAFANA_ENV_MAPPING.items():
            value = self._get_env_value(
                env_name=env_name,
                description=description,
                required=required,
                section="Grafana"
            )
            
            if value is not None:
                config_data[field_name] = value
        
        return config_data if config_data else None
    
    def _load_cloudwatch_config(self) -> Optional[Dict[str, Any]]:
        """
        CloudWatch 구성을 환경 변수에서 로드합니다.
        
        Returns:
            Optional[Dict[str, Any]]: CloudWatch 구성 딕셔너리 또는 None
        """
        config_data = {}
        
        for field_name, (env_name, description, required) in CLOUDWATCH_ENV_MAPPING.items():
            value = self._get_env_value(
                env_name=env_name,
                description=description,
                required=required,
                section="CloudWatch"
            )
            
            if value is not None:
                config_data[field_name] = value
        
        return config_data if config_data else None
    
    def _load_database_config(self) -> Optional[Dict[str, Any]]:
        """
        데이터베이스 구성을 환경 변수에서 로드합니다.
        
        Returns:
            Optional[Dict[str, Any]]: 데이터베이스 구성 딕셔너리 또는 None
        """
        config_data = {}
        
        for field_name, (env_name, description, required) in DATABASE_ENV_MAPPING.items():
            value = self._get_env_value(
                env_name=env_name,
                description=description,
                required=required,
                section="Database"
            )
            
            if value is not None:
                config_data[field_name] = value
        
        return config_data if config_data else None

    
    def load(self) -> AppConfig:
        """
        환경 변수에서 전체 애플리케이션 구성을 로드하고 검증합니다.
        
        Returns:
            AppConfig: 검증된 애플리케이션 구성
        
        Raises:
            ConfigurationError: 필수 환경 변수가 누락되었거나 검증 실패 시
        
        요구사항: 8.1, 8.2, 8.3, 8.5
        """
        # 상태 초기화
        self._missing_variables = []
        self._validation_errors = []
        
        # 각 섹션 로드
        bedrock_data = self._load_bedrock_config()
        grafana_data = self._load_grafana_config()
        cloudwatch_data = self._load_cloudwatch_config()
        database_data = self._load_database_config()
        
        # 누락된 필수 변수 확인
        if self._missing_variables:
            raise ConfigurationError(
                message="애플리케이션 시작 실패: 필수 환경 변수가 누락되었습니다.",
                missing_variables=self._missing_variables,
                validation_errors=self._validation_errors
            )
        
        # 타입 변환 오류 확인
        if self._validation_errors:
            raise ConfigurationError(
                message="애플리케이션 시작 실패: 환경 변수 값이 올바르지 않습니다.",
                validation_errors=self._validation_errors
            )
        
        # Pydantic 모델 생성 및 검증
        try:
            bedrock_config = BedrockConfig(**bedrock_data) if bedrock_data else None
            grafana_config = GrafanaConfig(**grafana_data) if grafana_data else None
            cloudwatch_config = CloudWatchConfig(**cloudwatch_data) if cloudwatch_data else None
            database_config = DatabaseConfig(**database_data) if database_data else DatabaseConfig()
            
            # 필수 구성이 None인 경우 오류
            if bedrock_config is None:
                raise ConfigurationError(
                    message="애플리케이션 시작 실패: Bedrock 구성을 로드할 수 없습니다.",
                    missing_variables=[{
                        "env_name": "AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION",
                        "description": "Bedrock 필수 환경 변수",
                        "section": "Bedrock"
                    }]
                )
            
            if grafana_config is None:
                raise ConfigurationError(
                    message="애플리케이션 시작 실패: Grafana 구성을 로드할 수 없습니다.",
                    missing_variables=[{
                        "env_name": "GRAFANA_URL, GRAFANA_API_KEY",
                        "description": "Grafana 필수 환경 변수",
                        "section": "Grafana"
                    }]
                )
            
            if cloudwatch_config is None:
                raise ConfigurationError(
                    message="애플리케이션 시작 실패: CloudWatch 구성을 로드할 수 없습니다.",
                    missing_variables=[{
                        "env_name": "CLOUDWATCH_AWS_ACCESS_KEY_ID, CLOUDWATCH_AWS_SECRET_ACCESS_KEY, CLOUDWATCH_REGION",
                        "description": "CloudWatch 필수 환경 변수",
                        "section": "CloudWatch"
                    }]
                )
            
            app_config = AppConfig(
                bedrock=bedrock_config,
                grafana=grafana_config,
                cloudwatch=cloudwatch_config,
                database=database_config
            )
            
            logger.info("구성이 성공적으로 로드되었습니다.")
            return app_config
            
        except ValidationError as e:
            # Pydantic 검증 오류를 설명적인 메시지로 변환
            validation_errors = []
            for error in e.errors():
                field_path = ".".join(str(loc) for loc in error["loc"])
                validation_errors.append({
                    "field": field_path,
                    "message": error["msg"]
                })
            
            raise ConfigurationError(
                message="애플리케이션 시작 실패: 구성 검증에 실패했습니다.",
                validation_errors=validation_errors
            )



def load_config_from_env() -> AppConfig:
    """
    환경 변수에서 애플리케이션 구성을 로드하는 편의 함수
    
    이 함수는 ConfigLoader를 사용하여 환경 변수에서 구성을 로드하고 검증합니다.
    누락된 필수 변수가 있으면 설명적인 오류 메시지와 함께 ConfigurationError를 발생시킵니다.
    
    Returns:
        AppConfig: 검증된 애플리케이션 구성
    
    Raises:
        ConfigurationError: 필수 환경 변수가 누락되었거나 검증 실패 시
    
    Example:
        >>> try:
        ...     config = load_config_from_env()
        ...     print(f"Bedrock 리전: {config.bedrock.region}")
        ... except ConfigurationError as e:
        ...     print(f"구성 오류: {e}")
        ...     sys.exit(1)
    
    요구사항: 8.1, 8.2, 8.3, 8.5
    """
    loader = ConfigLoader()
    return loader.load()


def get_required_env_variables() -> List[Dict[str, str]]:
    """
    모든 필수 환경 변수 목록을 반환합니다.
    
    이 함수는 애플리케이션 시작에 필요한 모든 필수 환경 변수의 목록을 반환합니다.
    각 변수에 대해 이름, 설명, 섹션 정보를 포함합니다.
    
    Returns:
        List[Dict[str, str]]: 필수 환경 변수 정보 목록
    
    Example:
        >>> required_vars = get_required_env_variables()
        >>> for var in required_vars:
        ...     print(f"{var['env_name']}: {var['description']}")
    """
    required_vars = []
    
    # Bedrock 필수 변수
    for field_name, (env_name, description, required) in BEDROCK_ENV_MAPPING.items():
        if required:
            required_vars.append({
                "env_name": env_name,
                "description": description,
                "section": "Bedrock"
            })
    
    # Grafana 필수 변수
    for field_name, (env_name, description, required) in GRAFANA_ENV_MAPPING.items():
        if required:
            required_vars.append({
                "env_name": env_name,
                "description": description,
                "section": "Grafana"
            })
    
    # CloudWatch 필수 변수
    for field_name, (env_name, description, required) in CLOUDWATCH_ENV_MAPPING.items():
        if required:
            required_vars.append({
                "env_name": env_name,
                "description": description,
                "section": "CloudWatch"
            })
    
    return required_vars


def validate_env_variables() -> tuple[bool, List[Dict[str, str]]]:
    """
    환경 변수의 존재 여부를 검증합니다.
    
    이 함수는 모든 필수 환경 변수가 설정되어 있는지 확인합니다.
    실제 값의 유효성은 검증하지 않고, 변수의 존재 여부만 확인합니다.
    
    Returns:
        tuple[bool, List[Dict[str, str]]]: (모든 변수 존재 여부, 누락된 변수 목록)
    
    Example:
        >>> is_valid, missing = validate_env_variables()
        >>> if not is_valid:
        ...     print("누락된 환경 변수:")
        ...     for var in missing:
        ...         print(f"  - {var['env_name']}")
    """
    missing_vars = []
    
    required_vars = get_required_env_variables()
    
    for var_info in required_vars:
        env_name = var_info["env_name"]
        value = os.environ.get(env_name)
        
        if value is None or value.strip() == "":
            missing_vars.append(var_info)
    
    return len(missing_vars) == 0, missing_vars
