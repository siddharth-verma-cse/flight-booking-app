from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class FlightSlice(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    departure_date: date


class Passenger(BaseModel):
    type: Literal["adult", "child", "infant_without_seat"] | None = None
    age: int | None = Field(default=None, ge=0, le=17)

    @model_validator(mode="after")
    def require_type_or_age(self) -> "Passenger":
        if self.type is None and self.age is None:
            raise ValueError("Each passenger must include either type or age")
        return self


class OfferRequestData(BaseModel):
    slices: list[FlightSlice] = Field(..., min_length=1)
    passengers: list[Passenger] = Field(..., min_length=1)
    cabin_class: Literal["economy", "premium_economy", "business", "first"] = "economy"


class FlightSearchRequest(BaseModel):
    data: OfferRequestData


class AirportInfo(BaseModel):
    code: str
    city: str
    airport_name: str


class FlightSegment(BaseModel):
    flight_number: str
    airline_name: str
    airline_code: str
    departure_time: str
    arrival_time: str
    duration: str
    origin: AirportInfo
    destination: AirportInfo


class FlightOffer(BaseModel):
    offer_id: str
    total_price: float
    currency: str

    airline_name: str
    airline_code: str
    flight_number: str

    departure_time: str
    arrival_time: str
    duration: str

    origin: AirportInfo
    destination: AirportInfo


class SearchFlightResponse(BaseModel):
    flights: list[FlightOffer]


class FlightConfirmPriceRequest(BaseModel):
    offer_id: str
    total_price: float
