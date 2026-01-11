# CLAUDE.md

## 프로젝트 규칙
- 모든 대화, 답변, 계획, 주석은 **반드시 한국어**로 작성.
- 깃 커밋/푸시는 사용자가 직접 수행.

## 기술 스택
- **Core**: Spring Boot 3.5.9 (Java 17), Gradle
- **DB**: MySQL 8.0(User), MongoDB 6(Paper/Log), Redis 7(Cache), Elasticsearch 7.17(Search)
- **Infra**: Docker Compose, Prometheus + Grafana, JWT Auth

## 코드 컨벤션

### 아키텍처 구조

```
Controller → Service → Repository → Entity
     ↓          ↓
    DTO        DTO
```

**원칙:**
- 각 계층은 바로 아래 계층만 참조
- 역계층 참조 금지 (Repository → Service 불가)
- Entity는 도메인 로직만 포함
- DTO 변환은 Service 계층에서 처리

### Java

- Wildcard import 금지
- `private` 메서드는 가장 마지막으로 사용하는 `public` 메서드의 하단에 배치
- 모든 파일의 마지막에는 개행 추가
- 클래스 정의 직후 개행 추가
- non-null은 primitive, nullable은 Wrapper
- 클래스명은 필요한 경우가 아니면 FQN 대신 simple name을 사용한다.

### Entity

- 무분별한 Getter/Setter/Builder/Data/NoArgsConstructor/AllArgsConstructor 지양
- Entity 속성에 따라 유연하게 `BaseEntity` 상속
- @Column의 name 옵션 반드시 사용(필드명은 camelCase, name 옵션은 snake_case)

### DTO

- `record` 사용
- `of`(다중)/`from`(단일) 메서드 패턴
- `XXXResponse`/`XXXRequest` 네이밍
- Entity를 DTO로 변환하는 경우 from 정적 팩토리 메서드 사용

### Controller

- RESTful
- `/api` prefix
- kebab-case URL
- 파라미터와 반환값은 반드시 DTO
- 예외처리 금지(전역 핸들러 사용)

### Service

- 예외는 CustomException으로 처리
- 조회 관련 메서드는 `readOnly = true`
- `@Transactional`은 클래스가 아니라 메서드에 선언

### Repository

- JpaRepository를 상속하는 경우 Repository 어노테이션 제외

### Test

- 한글 메서드명
- given/when/then 패턴 사용
- 기능 별로 테스트 그룹화(Nested)
- Nested 클래스는 한글명

## 주요 명령어
```bash
# 빌드 및 테스트
./gradlew clean build
./gradlew test

# 로컬 실행
./gradlew bootRun --args='--spring.profiles.active=local'

# Docker 환경 (MySQL, Mongo, Redis, ES, Monitoring)
docker compose -f docker-compose.local.yml up -d
docker compose -f docker-compose.local.yml down -v
```

## 아키텍처 요약
- **Polyglot Persistence**: 
  - MySQL: 사용자, 인증 (Transactional)
  - MongoDB: 논문, 북마크, 활동 로그 (Document)
  - Redis: 세션, 캐시
  - ES: 전문 검색
- **도메인 구조**: `com.inha.capstone` 하위에 `auth`, `user`, `paper`, `recommendation`(규칙 기반 엔진) 등으로 분리.