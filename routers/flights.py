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
)
from backend.utils.security import get_current_user


router = APIRouter(
    prefix="/api", tags=["flights"], dependencies=[Depends(get_current_user)]
)


@router.post("/flights/search")
async def search_flights(search: FlightSearchRequest):
    try:
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
