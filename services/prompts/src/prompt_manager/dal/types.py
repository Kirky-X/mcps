from sqlalchemy.types import UserDefinedType
from sqlalchemy.types import TypeDecorator


class PGVector(UserDefinedType):
    def __init__(self, dimension: int):
        self.dimension = dimension

    def get_col_spec(self, **kw):
        return "vector"

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            return str(list(value))
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

