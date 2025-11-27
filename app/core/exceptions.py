"""
커스텀 예외 클래스.

애플리케이션 전반에서 사용되는 예외 클래스를 정의합니다.
"""


class AppException(Exception):
    """애플리케이션 기본 예외 클래스."""

    def __init__(self, message: str = "Application error occurred"):
        self.message = message
        super().__init__(self.message)


class DatabaseException(AppException):
    """데이터베이스 관련 예외."""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message)


class MongoDBException(DatabaseException):
    """MongoDB 관련 예외."""

    def __init__(self, message: str = "MongoDB operation failed"):
        super().__init__(message)


class PostgreSQLException(DatabaseException):
    """PostgreSQL 관련 예외."""

    def __init__(self, message: str = "PostgreSQL operation failed"):
        super().__init__(message)


class ResourceNotFoundException(AppException):
    """리소스를 찾을 수 없음."""

    def __init__(self, resource: str = "Resource", identifier: str = ""):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message)


class ValidationException(AppException):
    """입력값 검증 실패."""

    def __init__(self, message: str = "Validation failed", field: str | None = None):
        if field:
            message = f"Validation failed for field '{field}': {message}"
        super().__init__(message)


class BusinessLogicException(AppException):
    """비즈니스 로직 위반."""

    def __init__(self, message: str = "Business logic error"):
        super().__init__(message)


class DuplicateResourceException(BusinessLogicException):
    """중복된 리소스."""

    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} already exists")


class UnauthorizedException(AppException):
    """인증 실패."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message)


class ForbiddenException(AppException):
    """권한 없음."""

    def __init__(self, message: str = "Forbidden"):
        super().__init__(message)
