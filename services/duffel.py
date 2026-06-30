import os

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from backend.schemas.flights import (
    OfferPassenger,
    SearchFlightResponse,
    FlightOffer,
    AirportInfo,
    FlightBookRequest,
    FlightBookResponse,
)
from typing import Any


from backend.schemas.flights import FlightSearchRequest, FlightConfirmPriceRequest

load_dotenv()

DUFFEL_API_KEY = os.getenv("DUFFEL_API_KEY")
DUFFEL_BASE_URL = os.getenv("DUFFEL_BASE_URL", "https://api.duffel.com/").rstrip("/")
DUFFEL_API_VERSION = "v2"


duffel_client = httpx.AsyncClient(
    base_url=DUFFEL_BASE_URL,
    timeout=httpx.Timeout(30.0),
    headers={
        "Authorization": f"Bearer {DUFFEL_API_KEY}",
        "Duffel-Version": DUFFEL_API_VERSION,
        "Accept": "application/json",
        "Content-Type": "application/json",
    },
)


async def search_flights(
    search: FlightSearchRequest,
) -> SearchFlightResponse:

    if not DUFFEL_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Duffel API key is not configured",
        )

    try:
        response = await duffel_client.post(
            "/air/offer_requests",
            json=search.model_dump(mode="json", exclude_none=True),
        )

        response.raise_for_status()

        data = response.json()

        flights = []

        for offer in data["data"]["offers"]:
            segment = offer["slices"][0]["segments"][0]
            # passenger = segment["passengers"][0]

            flights.append(
                FlightOffer(
                    offer_id=offer["id"],
                    total_price=float(offer["total_amount"]),
                    currency=offer["total_currency"],
                    airline_name=segment["marketing_carrier"]["name"],
                    airline_code=segment["marketing_carrier"]["iata_code"],
                    flight_number=segment["marketing_carrier_flight_number"],
                    departure_time=segment["departing_at"],
                    arrival_time=segment["arriving_at"],
                    duration=segment["duration"],
                    passengers=[
                        OfferPassenger.model_validate(passenger)
                        for passenger in segment["passengers"]
                    ],
                    origin=AirportInfo(
                        code=segment["origin"]["iata_code"],
                        city=segment["origin"]["city"]["name"],
                        airport_name=segment["origin"]["name"],
                    ),
                    destination=AirportInfo(
                        code=segment["destination"]["iata_code"],
                        city=segment["destination"]["city"]["name"],
                        airport_name=segment["destination"]["name"],
                    ),
                )
            )

        return SearchFlightResponse(flights=flights)

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach flight search provider",
        ) from exc


def _build_order_payload(book: FlightBookRequest) -> dict[str, Any]:
    passenger = book.passenger
    gender = passenger.gender.lower()
    if gender in {"male", "m"}:
        gender = "m"
    elif gender in {"female", "f"}:
        gender = "f"

    return {
        "data": {
            "selected_offers": [book.offer_id],
            "payments": [
                {
                    "type": "balance",
                    "amount": book.total_amount,
                    "currency": book.currency,
                }
            ],
            "passengers": [
                {
                    "id": passenger.passenger_id,
                    "given_name": passenger.given_name,
                    "family_name": passenger.family_name,
                    "born_on": passenger.born_on,
                    "title": passenger.title.lower(),
                    "gender": gender,
                    "email": passenger.email,
                    "phone_number": passenger.phone_number,
                }
            ],
        }
    }


async def fetch_flight_price(price: FlightConfirmPriceRequest) -> dict[str, Any] | None:
    try:
        response = await duffel_client.get(f"/air/offers/{price.offer_id}")

        response.raise_for_status()

        return response.json()["data"]

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return None

        raise HTTPException(
            status_code=exc.response.status_code, detail=exc.response.text
        )


async def book_flight(book: FlightBookRequest) -> FlightBookResponse:
    try:
        price_confirmation = await fetch_flight_price(
            FlightConfirmPriceRequest(
                offer_id=book.offer_id,
                total_price=float(book.total_amount),
            )
        )
        if price_confirmation is None:
            raise HTTPException(status_code=404, detail="Offer not found or expired")

        if price_confirmation["total_amount"] != book.total_amount:
            raise HTTPException(status_code=400, detail="Price has changed")

        response = await duffel_client.post(
            "/air/orders",
            json=_build_order_payload(book),
        )

        response.raise_for_status()

        return response.json()["data"]
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code, detail=exc.response.text
        )
