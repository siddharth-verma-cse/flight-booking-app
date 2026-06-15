from fastapi import APIRouter, HTTPException
from backend.schemas.flights import FlightSearchRequest, FlightConfirmPriceRequest
from backend.services.duffel import search_flights as fetch_flights, fetch_flight_price

router = APIRouter(prefix="/api", tags=["flights"])


@router.post("/flights/search")
async def search_flights(search: FlightSearchRequest):
    try:
        # TODO return cache if available Redis cache.
        flights = await fetch_flights(search)
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
