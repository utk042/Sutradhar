"""Request and response schemas for authentication.

Note what is absent: no endpoint ever returns a token in its body. Tokens are
set as httpOnly cookies so that JavaScript — including any script injected into
the page — cannot read them.
"""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    mobile_number: str = Field(min_length=10, max_length=15, pattern=r"^[0-9]{10,15}$")
    password: str = Field(min_length=8, max_length=256)


class CurrentUser(BaseModel):
    """The signed-in user as the interface needs them. No password hash, ever."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    role: str


class MessageResponse(BaseModel):
    """A machine-readable outcome code.

    Deliberately a code, not a sentence: the interface looks the code up in its
    own locale files, so no user-facing English is produced by the backend and
    Hindi needs no server change.
    """

    code: str
