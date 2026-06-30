from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, model_validator


class FlightSlice(BaseModel):
    origin: str = Field(..., min_length=3, max_length=3)
    destination: str = Field(..., min_length=3, max_length=3)
    departure_date: str


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
    passengers: list["OfferPassenger"]


class SearchFlightResponse(BaseModel):
    flights: list[FlightOffer]


class FlightConfirmPriceRequest(BaseModel):
    offer_id: str
    total_price: float


class PassengerRequest(BaseModel):
    passenger_id: str
    given_name: str
    family_name: str
    born_on: str
    title: str
    gender: str
    email: EmailStr
    phone_number: str


class FlightBookRequest(BaseModel):
    offer_id: str
    total_amount: str
    currency: str
    passenger: PassengerRequest


class TicketDocument(BaseModel):
    passenger_ids: list[str]
    unique_identifier: str
    type: str


class PaymentStatus(BaseModel):
    paid_at: Optional[str] = None
    awaiting_payment: bool


class PassengerResponse(BaseModel):
    id: str
    given_name: str
    family_name: str
    email: str
    phone_number: str
    born_on: str
    gender: str
    title: str
    type: str


class OrderResponseData(BaseModel):
    id: str
    booking_reference: str
    offer_id: str
    total_amount: str
    total_currency: str
    created_at: str
    live_mode: bool

    payment_status: PaymentStatus
    passengers: list[PassengerResponse]
    documents: list[TicketDocument]


class FlightBookResponse(BaseModel):
    data: OrderResponseData


class Baggage(BaseModel):
    quantity: int
    type: str


class Seat(BaseModel):
    pitch: str
    legroom: str
    type: Optional[str] = None


class Wifi(BaseModel):
    cost: str
    available: bool


class Power(BaseModel):
    available: bool


class Amenities(BaseModel):
    seat: Seat
    wifi: Wifi
    power: Power


class Cabin(BaseModel):
    amenities: Amenities
    marketing_name: str
    name: str


class OfferPassenger(BaseModel):
    baggages: list[Baggage]
    cabin_class_marketing_name: str
    passenger_id: str
    cabin: Cabin
    cabin_class: str
    fare_basis_code: str
