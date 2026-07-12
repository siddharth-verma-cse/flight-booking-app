import hashlib
import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from backend.schemas.flights import (
    FlightSearchRequest,
    FlightConfirmPriceRequest,
    FlightBookRequest,
    SeatMapResponse,
    OrderListParams,
)

from backend.services.duffel import (
    search_flights as fetch_flights,
    fetch_flight_price,
    book_flight,
    fetch_seat_map,
    get_order,
    list_orders,
    create_order_cancellation,
    confirm_order_cancellation,
    search_places,
)
from backend.utils.security import get_current_user

from backend.external_services.cache import redis_cache


router = APIRouter(
    prefix="/api", tags=["flights"], dependencies=[Depends(get_current_user)]
)

logger = logging.getLogger(__name__)


@router.post("/flights/search")
async def search_flights(search: FlightSearchRequest):
    try:
        request_body = search.model_dump(mode="json", exclude_none=True)
        # Hash the request VALUES so different searches get different keys.
        digest = hashlib.sha256(
            json.dumps(request_body, sort_keys=True).encode()
        ).hexdigest()
        cache_key = f"flights:{digest}"
        logger.info(f"cache_key :::::: {cache_key}")
        cached_value = redis_cache.get(cache_key)
        if cached_value:
            logger.info("Using cached results")
            return cached_value

        # Pass the model — fetch_flights calls .model_dump() on it internally.
        flights = await fetch_flights(search)

        # Serialize to a JSON-able dict; json.dumps() cannot handle a Pydantic model.
        redis_cache.set(cache_key, flights.model_dump(mode="json"), 300)

        return flights

    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flights/price")
async def confirm_flight_price(price: FlightConfirmPriceRequest):
    latest_offer = await fetch_flight_price(price)

    if latest_offer is None:
        raise HTTPException(status_code=404, detail="Offer not found or expired")

    latest_price = float(latest_offer["total_amount"])

    if latest_price != price.total_price:
        return {
            "success": False,
            "price_changed": True,
            "old_price": price.total_price,
            "new_price": latest_price,
            "message": "Flight price has changed",
        }

    return {
        "success": True,
        "price_changed": False,
        "price": latest_price,
        "message": "Price confirmed",
    }


@router.post("/flights/book")
async def book_flight_route(book: FlightBookRequest):

    try:
        return await book_flight(book)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flights/seat-map/{offer_id}", response_model=SeatMapResponse)
async def get_seat_map(offer_id: str):
    try:
        return await fetch_seat_map(offer_id)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flights/orders")
async def list_orders_route(params: OrderListParams = Depends()):
    try:
        return await list_orders(params)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flights/orders/{order_id}")
async def get_order_route(order_id: str):
    try:
        return await get_order(order_id)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flights/orders/{order_id}/cancellation")
async def create_order_cancellation_route(order_id: str):
    try:
        return await create_order_cancellation(order_id)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flights/cancellations/{cancellation_id}/confirm")
async def confirm_order_cancellation_route(cancellation_id: str):
    try:
        return await confirm_order_cancellation(cancellation_id)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/flights/search-cities")
async def search_cities(q: str, limit: int = 10):
    """Search for airports and cities by name or IATA code (e.g., 'London', 'LHR')."""
    if not q or len(q) < 1:
        raise HTTPException(
            status_code=400, detail="Query must be at least 1 character"
        )
    try:
        return await search_places(q, limit)
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flights/advanced-search")
async def advanced_flight_search(search: FlightSearchRequest):
    """Advanced flight search with caching and detailed results."""
    try:
        request_body = search.model_dump(mode="json", exclude_none=True)
        digest = hashlib.sha256(
            json.dumps(request_body, sort_keys=True).encode()
        ).hexdigest()
        cache_key = f"flights:advanced:{digest}"
        logger.info(f"Advanced search cache_key: {cache_key}")

        cached_value = redis_cache.get(cache_key)
        if cached_value:
            logger.info("Returning cached advanced search results")
            return cached_value

        flights = await fetch_flights(search)
        redis_cache.set(cache_key, flights.model_dump(mode="json"), 600)

        return flights
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
