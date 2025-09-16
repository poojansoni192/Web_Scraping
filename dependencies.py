from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from .utils import verify_token
from .models import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Dependency to get the current user based on the token
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenData(**payload)

# Dependency to check if user has a specific role
def get_current_active_user(current_user: TokenData = Depends(get_current_user)):
    if current_user.role != "admin":  # Example check, you can customize the role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user
