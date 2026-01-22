# 빌드 단계 - Node.js 20 사용 (Vite 5 호환)
FROM node:20-alpine AS builder

# 작업 디렉토리 설정
WORKDIR /app

# package.json 복사
COPY package.json ./

# 종속성 설치
RUN npm install

# 애플리케이션 코드 복사
COPY . .

# Vite로 React 앱 빌드
RUN npm run build

# 프로덕션 단계
FROM nginx:1.25-alpine

# Vite 빌드 출력(dist)을 nginx로 복사
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx 구성 복사
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 포트 3000 노출
EXPOSE 3000

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

# nginx 시작
CMD ["nginx", "-g", "daemon off;"]
