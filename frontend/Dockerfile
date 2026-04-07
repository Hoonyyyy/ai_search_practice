# ────────────────────────────────────────────────────────────
# Stage 1 : 빌드 단계
#   Node.js 환경에서 React 앱을 빌드한다.
#   결과물은 /app/build 폴더에 HTML/JS/CSS 정적 파일로 생성된다.
# ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# package.json 먼저 복사해서 패키지 캐시를 활용한다.
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

# ────────────────────────────────────────────────────────────
# Stage 2 : 서빙 단계
#   Node.js 없이 Nginx만으로 정적 파일을 서빙한다. (용량 절감)
# ────────────────────────────────────────────────────────────
FROM nginx:alpine

# 빌드 결과물을 Nginx가 서빙하는 경로로 복사
COPY --from=builder /app/build /usr/share/nginx/html

# SSE 프록시 설정이 담긴 Nginx 설정 파일 교체
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
