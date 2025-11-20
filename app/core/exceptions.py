"""
커스텀 예외 클래스 정의.

이 모듈은 애플리케이션 전체에서 사용할 예외 클래스들을 정의합니다.
예외 계층 구조를 통해 타입별 에러 처리가 가능합니다.
"""


class AppException(Exception):
    """
    애플리케이션 기본 예외.
    
    모든 커스텀 예외의 기본 클래스입니다.
    일반적인 애플리케이션 에러에 사용됩니다.
    """
    pass


class DatabaseException(AppException):
    """
    데이터베이스 관련 예외.
    
    PostgreSQL, MongoDB 등 모든 데이터베이스 작업 중 발생하는
    일반적인 에러에 사용됩니다.
    """
    pass


class MongoDBException(DatabaseException):
    """
    MongoDB 관련 예외.
    
    MongoDB 연결 실패, 쿼리 실패 등에 사용됩니다.
    """
    pass


class PostgreSQLException(DatabaseException):
    """
    PostgreSQL 관련 예외.
    
    PostgreSQL 연결 실패, 쿼리 실패 등에 사용됩니다.
    """
    pass


class BusinessLogicException(AppException):
    """
    비즈니스 로직 예외.
    
    비즈니스 규칙 위반, 잘못된 상태 전환 등
    도메인 로직과 관련된 에러에 사용됩니다.
    """
    pass


class ResourceNotFoundException(AppException):
    """
    리소스를 찾을 수 없음.
    
    요청한 리소스(논문, 북마크 등)가 존재하지 않을 때 사용됩니다.
    """
    pass


class ValidationException(AppException):
    """
    입력값 검증 실패.
    
    요청 데이터의 형식이나 값이 유효하지 않을 때 사용됩니다.
    """
    pass
