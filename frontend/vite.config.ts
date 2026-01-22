import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite 설정 - AI 챗봇 프론트엔드
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // 백엔드 API 프록시 설정
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 빌드 출력 디렉토리
    outDir: 'dist',
    // 소스맵 생성 (프로덕션에서는 비활성화)
    sourcemap: false,
  },
});
