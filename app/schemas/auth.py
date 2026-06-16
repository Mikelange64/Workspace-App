from pydantic import BaseModel, EmailStr, Field


# =================================== JWT TOKEN SCHEMA ===================================

class Token(BaseModel):
    access_token : str
    token_type   : str


# ================================= PASSWORD RESET TOKENS ================================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(max_length=120)


# When the user clicks the link and submits their new password
class ResetPasswordRequest(BaseModel):  
    token: str
    new_password: str = Field(min_length=8)


# For logged in users who wants to change their passwords
class ChangePasswordRequest(BaseModel): 
    current_password: str
    new_password: str = Field(min_length=8)



