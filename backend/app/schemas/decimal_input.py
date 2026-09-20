from pydantic import BaseModel, field_validator

class DecimalInputModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def reject_floating_point(cls, value):
        if isinstance(value, float):
            raise ValueError("Envie valores decimais como texto, sem ponto flutuante JSON.")
        return value
