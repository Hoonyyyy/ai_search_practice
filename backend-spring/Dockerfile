# ────────────────────────────────────────────────────────────
# Stage 1 : 빌드 단계
#   Maven + JDK 이미지로 소스코드를 컴파일해서 .jar 파일을 만든다.
#   이 단계는 최종 이미지에 포함되지 않아 용량을 줄인다.
# ────────────────────────────────────────────────────────────
FROM --platform=linux/amd64 maven:3.9-eclipse-temurin-20 AS builder

WORKDIR /app

# pom.xml 만 먼저 복사해서 의존성을 미리 받아둔다.
# 소스코드가 바뀌어도 pom.xml이 같으면 이 레이어는 캐시를 재사용한다. (빌드 속도 향상)
COPY pom.xml .
RUN mvn dependency:go-offline -q

# 소스코드 복사 후 빌드 (-DskipTests: 테스트 생략)
COPY src ./src
RUN mvn package -DskipTests -q

# ────────────────────────────────────────────────────────────
# Stage 2 : 실행 단계
#   JDK 전체가 아닌 JRE(실행만 가능한 경량 버전)만 포함한다.
# ────────────────────────────────────────────────────────────
FROM --platform=linux/amd64 eclipse-temurin:20-jre-alpine

WORKDIR /app

# 빌드 단계에서 만든 .jar 파일만 가져온다.
COPY --from=builder /app/target/*.jar app.jar

# DB 파일이 저장될 디렉토리 미리 생성
RUN mkdir -p /app/data

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
