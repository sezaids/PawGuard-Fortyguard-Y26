from typing import Literal
from pydantic import BaseModel, Field, model_validator


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1200)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    dog_id: str | None = None
    surface: Literal["asphalt", "concrete", "grass", "sand", "soil_dirt"] | None = None
    available_minutes: Literal[15, 30, 45, 60] = 30

    @model_validator(mode="after")
    def location_pair(self) -> "AssistantChatRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Provide both latitude and longitude, or neither.")
        return self


class AssistantChatResponse(BaseModel):
    answer: str
    used_current_conditions: bool
    context_note: str
    disclaimer: str
    timings_ms: dict[str, int]
