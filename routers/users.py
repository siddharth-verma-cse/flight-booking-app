from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from backend.schemas.users import UserRegister, UserRead
from backend.crud.users import get_user_by_email, create_user
from backend.utils.email import send_email_async
from backend.crud.database import get_session
from sqlmodel import Session


router = APIRouter(prefix="/api", tags=["users"])


@router.post("/register/", response_model=UserRead)
async def register(
    background_tasks: BackgroundTasks,
    user_in: UserRegister,
    session: Session = Depends(get_session),
):
    # verify that user does not exist

    user = get_user_by_email(session, user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    # then save user in db
    user = create_user(session, user_in.email, user_in.password)

    subject = "Welcome to Aero Bound Ventures"
    recipient = [user_in.email]
    body_text = f"Hello {user_in.email},\n\nThank you for registering with Aero Bound Ventures. Your account has been created successfully. You can now login to your account and start using our platform."
    background_tasks.add_task(send_email_async, subject, recipient, body_text)
    # send email to user
    return user
