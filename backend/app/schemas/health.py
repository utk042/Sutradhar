from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    readonly_database: str
    version: str
