import os

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from backend.schemas.flights import SearchFlightResponse, FlightOffer, AirportInfo
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

    except httpx.HTTPStatusError:
        ...


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
