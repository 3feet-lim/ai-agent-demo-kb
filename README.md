# AI 챗봇 인프라 모니터링

폐쇄망 환경에서 인프라 모니터링 및 분석을 위해 설계된 AI 기반 챗봇 시스템입니다. React 기반 채팅 인터페이스와 Python/LangChain 백엔드를 통합하며, AWS Bedrock Claude Sonnet 4.5와 MCP(Model Context Protocol) 서버를 활용하여 Grafana 및 CloudWatch로부터 인프라 데이터를 가져오고 분석하여 제공합니다.

## 주요 기능

- 🤖 **AI 기반 대화**: AWS Bedrock Claude Sonnet 4.5를 활용한 자연어 인터페이스
- 📊 **인프라 모니터링**: Grafana 및 CloudWatch 데이터 실시간 조회 및 분석
- 🔒 **폐쇄망 배포**: 인터넷 연결 없이 작동하는 자체 포함 Docker 이미지
- 💬 **세션 관리**: 여러 대화 세션을 통한 체계적인 모니터링 주제 관리
- 💾 **대화 지속성**: SQLite 기반 대화 기록 저장

## 시스템 아키텍처

```
┌─────────────────┐
│   사용자 브라우저   │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│  Chat UI (React) │
│   포트: 3000     │
└────────┬────────┘
         │ HTTP/WebSocket
         ▼
┌─────────────────────────────────┐
│  백엔드 (Python + LangChain)     │
│  포트: 8000                      │
│  ┌──────────────────────────┐  │
│  │ AWS Bedrock              │  │
│  │ (Claude Sonnet 4.5)      │  │
│  └──────────────────────────┘  │
│  ┌──────────────────────────┐  │
│  │ MCP 서버                  │  │
│  │ - Grafana                │  │
│  │ - CloudWatch             │  │
│  └──────────────────────────┘  │
│  ┌──────────────────────────┐  │
│  │ SQLite 데이터베이스        │  │
│  └──────────────────────────┘  │
└─────────────────────────────────┘
```

## 프로젝트 구조

```
.
├── backend/                    # Python 백엔드
│   ├── Dockerfile             # 백엔드 Docker 이미지
│   ├── requirements.txt       # Python 종속성
│   ├── main.py               # FastAPI 애플리케이션 진입점
│   └── tests/                # 백엔드 테스트
│
├── frontend/                  # React 프론트엔드
│   ├── Dockerfile            # 프론트엔드 Docker 이미지
│   ├── package.json          # Node.js 종속성
│   ├── nginx.conf            # Nginx 구성
│   ├── public/               # 정적 파일
│   ├── src/                  # React 소스 코드
│   └── tests/                # 프론트엔드 테스트
│
├── docker-compose.yml         # Docker Compose 오케스트레이션
├── .env.example              # 환경 변수 템플릿
└── README.md                 # 이 파일
```

## 시작하기

### 사전 요구사항

- Docker 20.10 이상
- Docker Compose 2.0 이상
- AWS 계정 및 Bedrock 액세스 권한
- Grafana 인스턴스 (선택 사항)
- AWS CloudWatch 액세스 권한 (선택 사항)

### 설치 및 실행

1. **환경 변수 설정**

   ```bash
   # .env.example을 .env로 복사
   cp .env.example .env
   
   # .env 파일을 편집하여 실제 값으로 업데이트
   # - AWS 자격 증명
   # - Bedrock 구성
   # - Grafana URL 및 API 키
   # - CloudWatch 자격 증명
   ```

2. **Docker 이미지 빌드**

   ```bash
   docker-compose build
   ```

3. **서비스 시작**

   ```bash
   docker-compose up -d
   ```

4. **애플리케이션 액세스**

   - 프론트엔드: http://localhost:3000
   - 백엔드 API: http://localhost:8000
   - API 문서: http://localhost:8000/docs

5. **서비스 중지**

   ```bash
   docker-compose down
   ```

### 개발 모드

백엔드 개발:
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

프론트엔드 개발:
```bash
cd frontend
npm install
npm start
```

## 테스트

### 백엔드 테스트

```bash
cd backend
pytest
```

### 프론트엔드 테스트

```bash
cd frontend
npm test
```

## 환경 변수

필수 환경 변수는 `.env.example` 파일을 참조하세요. 주요 변수:

- `AWS_ACCESS_KEY_ID`: AWS 액세스 키
- `AWS_SECRET_ACCESS_KEY`: AWS 시크릿 키
- `AWS_REGION`: AWS 리전
- `BEDROCK_MODEL_ID`: Bedrock 모델 ID
- `GRAFANA_URL`: Grafana 인스턴스 URL
- `GRAFANA_API_KEY`: Grafana API 키
- `CLOUDWATCH_REGION`: CloudWatch 리전

## 폐쇄망 배포

이 시스템은 폐쇄망 환경에서 작동하도록 설계되었습니다:

1. 모든 종속성이 Docker 이미지에 포함됨
2. 초기 배포 후 인터넷 연결 불필요
3. 프라이빗 네트워크 내의 AWS Bedrock 엔드포인트 사용
4. 로컬 SQLite 데이터베이스로 데이터 지속성 보장

## 문제 해결

### 백엔드가 시작되지 않음

- `.env` 파일의 모든 필수 환경 변수가 설정되었는지 확인
- Docker 로그 확인: `docker-compose logs backend`
- 헬스 체크 확인: `curl http://localhost:8000/health`

### 프론트엔드가 백엔드에 연결되지 않음

- 백엔드가 실행 중인지 확인: `docker-compose ps`
- 네트워크 구성 확인: `docker network ls`
- nginx 로그 확인: `docker-compose logs frontend`

### MCP 서버 오류

- Grafana/CloudWatch 자격 증명이 올바른지 확인
- 프라이빗 네트워크에서 서비스에 액세스할 수 있는지 확인
- MCP 서버 로그 확인

## 라이선스

이 프로젝트는 내부 사용을 위한 것입니다.

## 기여

자세한 내용은 `.kiro/specs/ai-chatbot-infrastructure-monitoring/` 디렉토리의 사양 문서를 참조하세요.
