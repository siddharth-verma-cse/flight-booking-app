import os
from decimal import Decimal

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
    SeatMapResponse,
    SeatMapSegment,
    SeatMapRow,
    SelectableSeat,
    SeatSelectionService,
    OrderListParams,
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


def _build_airport_info(place: dict[str, Any]) -> AirportInfo:
    # Duffel returns `city` as a nullable object; `city_name` is a flat fallback.
    city = place.get("city") or {}
    city_name = place.get("city_name") or city.get("name") or ""
    return AirportInfo(
        code=place.get("iata_code") or "",
        city=city_name,
        airport_name=place.get("name") or "",
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
                    origin=_build_airport_info(segment["origin"]),
                    destination=_build_airport_info(segment["destination"]),
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

    data: dict[str, Any] = {
        "type": "instant",
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

    if book.service_ids:
        data["services"] = [
            {"id": service_id, "quantity": 1} for service_id in book.service_ids
        ]

    return {"data": data}


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
        try:
            offer_response = await duffel_client.get(f"/air/offers/{book.offer_id}")
            offer_response.raise_for_status()
            offer = offer_response.json()["data"]
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise HTTPException(
                    status_code=404, detail="Offer not found or expired"
                )
            raise

        # Expected charge is the offer base plus any selected seat services.
        # Seat services come from the seat map, NOT the offer's available_services
        # (which only ever contains baggage), so validate/price them from there.
        expected_total = Decimal(offer["total_amount"])
        if book.service_ids:
            seat_prices = {
                service.service_id: Decimal(service.amount)
                for segment in (await fetch_seat_map(book.offer_id)).segments
                for row in segment.rows
                for seat in row.seats
                for service in seat.services
            }
            for service_id in book.service_ids:
                amount = seat_prices.get(service_id)
                if amount is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Seat service {service_id} is not available on this offer",
                    )
                expected_total += amount

        if Decimal(book.total_amount) != expected_total:
            raise HTTPException(
                status_code=400,
                detail="Price has changed",
            )

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


def _build_seat_map_response(body: dict[str, Any]) -> SeatMapResponse:
    segments: list[SeatMapSegment] = []

    for seat_map in body.get("data", []):
        segment_id = seat_map["segment_id"]

        for cabin in seat_map.get("cabins", []):
            rows: list[SeatMapRow] = []

            for row in cabin.get("rows", []):
                seats: list[SelectableSeat] = []

                for section in row.get("sections", []):
                    for element in section.get("elements", []):
                        if element.get("type") != "seat":
                            continue

                        services = [
                            SeatSelectionService(
                                service_id=service["id"],
                                passenger_id=service["passenger_id"],
                                amount=service["total_amount"],
                                currency=service["total_currency"],
                            )
                            for service in element.get("available_services", [])
                        ]

                        seats.append(
                            SelectableSeat(
                                designator=element.get("designator"),
                                available=bool(services),
                                services=services,
                            )
                        )

                if seats:
                    rows.append(SeatMapRow(seats=seats))

            if rows:
                segments.append(
                    SeatMapSegment(
                        segment_id=segment_id,
                        cabin_class=cabin["cabin_class"],
                        aisles=cabin.get("aisles", 0),
                        rows=rows,
                    )
                )

    return SeatMapResponse(segments=segments)


async def fetch_seat_map(offer_id: str) -> SeatMapResponse:
    try:
        response = await duffel_client.get(
            "/air/seat_maps",
            params={"offer_id": offer_id},
        )
        response.raise_for_status()
        return _build_seat_map_response(response.json())
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


async def get_order(order_id: str) -> dict[str, Any]:
    try:
        response = await duffel_client.get(f"/air/orders/{order_id}")
        response.raise_for_status()
        return response.json()["data"]
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach flight booking provider",
        ) from exc


async def list_orders(params: OrderListParams) -> dict[str, Any]:
    try:
        response = await duffel_client.get(
            "/air/orders",
            params=params.model_dump(mode="json", exclude_none=True),
        )
        response.raise_for_status()
        body = response.json()
        return {"data": body["data"], "meta": body.get("meta", {})}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach flight booking provider",
        ) from exc


async def create_order_cancellation(order_id: str) -> dict[str, Any]:
    """Request a cancellation quote. Nothing is cancelled until it is confirmed."""
    try:
        response = await duffel_client.post(
            "/air/order_cancellations",
            json={"data": {"order_id": order_id}},
        )
        response.raise_for_status()
        return response.json()["data"]
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach flight booking provider",
        ) from exc


async def confirm_order_cancellation(cancellation_id: str) -> dict[str, Any]:
    """Confirm a cancellation quote. This actually cancels the order and refunds."""
    try:
        response = await duffel_client.post(
            f"/air/order_cancellations/{cancellation_id}/actions/confirm",
        )
        response.raise_for_status()
        return response.json()["data"]
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=exc.response.text,
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to reach flight booking provider",
        ) from exc


async def search_places(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search for airports and cities by name or IATA code. Returns cached common airports."""
    # Common airports database (fallback since Duffel's place search has limited availability)
    AIRPORTS = [
        {
            "iata_code": "LHR",
            "name": "London Heathrow",
            "city": "London",
            "country": "United Kingdom",
        },
        {
            "iata_code": "JFK",
            "name": "John F. Kennedy International",
            "city": "New York",
            "country": "United States",
        },
        {
            "iata_code": "CDG",
            "name": "Charles de Gaulle",
            "city": "Paris",
            "country": "France",
        },
        {
            "iata_code": "AMS",
            "name": "Amsterdam Airport Schiphol",
            "city": "Amsterdam",
            "country": "Netherlands",
        },
        {
            "iata_code": "DXB",
            "name": "Dubai International",
            "city": "Dubai",
            "country": "United Arab Emirates",
        },
        {"iata_code": "HND", "name": "Haneda", "city": "Tokyo", "country": "Japan"},
        {
            "iata_code": "LAX",
            "name": "Los Angeles International",
            "city": "Los Angeles",
            "country": "United States",
        },
        {
            "iata_code": "ORD",
            "name": "Chicago O'Hare",
            "city": "Chicago",
            "country": "United States",
        },
        {
            "iata_code": "LAS",
            "name": "Harry Reid International",
            "city": "Las Vegas",
            "country": "United States",
        },
        {
            "iata_code": "DEL",
            "name": "Indira Gandhi International",
            "city": "Delhi",
            "country": "India",
        },
        {
            "iata_code": "BOM",
            "name": "Bombay Aerodrome",
            "city": "Mumbai",
            "country": "India",
        },
        {
            "iata_code": "CCU",
            "name": "Netaji Subhas Chandra Bose",
            "city": "Kolkata",
            "country": "India",
        },
        {
            "iata_code": "BLR",
            "name": "Kempegowda International",
            "city": "Bangalore",
            "country": "India",
        },
        {
            "iata_code": "MAA",
            "name": "Chennai International",
            "city": "Chennai",
            "country": "India",
        },
        {
            "iata_code": "SFO",
            "name": "San Francisco International",
            "city": "San Francisco",
            "country": "United States",
        },
        {
            "iata_code": "LGW",
            "name": "London Gatwick",
            "city": "London",
            "country": "United Kingdom",
        },
        {"iata_code": "FCO", "name": "Fiumicino", "city": "Rome", "country": "Italy"},
        {
            "iata_code": "MAD",
            "name": "Adolfo Suárez Madrid",
            "city": "Madrid",
            "country": "Spain",
        },
    ]

    query_lower = query.lower()
    results = [
        airport
        for airport in AIRPORTS
        if query_lower in airport["iata_code"].lower()
        or query_lower in airport["name"].lower()
        or query_lower in airport["city"].lower()
    ]

    return results[:limit]
