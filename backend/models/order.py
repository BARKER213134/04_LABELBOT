from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class AddressInfo(BaseModel):
    """Address information model"""
    name: str
    addressLine1: str
    addressLine2: Optional[str] = None
    city: str
    state: str
    postalCode: str
    countryCode: str = "US"
    phone: Optional[str] = None
    email: Optional[str] = None

class PackageInfo(BaseModel):
    """Package dimension and weight information"""
    weight: float  # in ounces
    length: float  # in inches
    width: float   # in inches
    height: float  # in inches

class CarrierEnum(str, Enum):
    USPS = "usps"
    FEDEX = "fedex"
    FEDEX_WALLETED = "fedex_walleted"
    UPS = "ups"
    UPS_WALLETED = "ups_walleted"
    STAMPS_COM = "stampscom"
    STAMPS_COM_ALT = "stamps_com"
    DHL = "dhl"

class OrderStatus(str, Enum):
    PENDING = "pending"
    LABEL_CREATED = "label_created"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class Order(BaseModel):
    """Order document stored in MongoDB"""
    id: str = Field(default="")
    telegram_user_id: Optional[str] = None
    telegram_username: Optional[str] = None
    shipFromAddress: AddressInfo
    shipToAddress: AddressInfo
    package: PackageInfo
    carrier: CarrierEnum
    carrier_id: Optional[str] = None
    rate_id: Optional[str] = None  # ShipEngine rate_id for fixed pricing
    serviceCode: str
    validateAddress: str = "validate_and_clean"
    status: OrderStatus = OrderStatus.PENDING
    labelId: Optional[str] = None
    trackingNumber: Optional[str] = None
    labelCost: Optional[float] = None
    labelDownloadUrl: Optional[str] = None
    shipDate: Optional[datetime] = None
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)
    environment: str = "sandbox"

class CreateOrderRequest(BaseModel):
    shipFromName: str
    shipFromAddressLine1: str
    shipFromAddressLine2: Optional[str] = None
    shipFromCity: str
    shipFromState: str
    shipFromPostalCode: str
    shipFromCountryCode: str = "US"
    shipFromPhone: Optional[str] = None
    shipFromEmail: Optional[str] = None
    
    shipToName: str
    shipToAddressLine1: str
    shipToAddressLine2: Optional[str] = None
    shipToCity: str
    shipToState: str
    shipToPostalCode: str
    shipToCountryCode: str = "US"
    shipToPhone: Optional[str] = None
    shipToEmail: Optional[str] = None
    
    packageWeight: float
    packageLength: float
    packageWidth: float
    packageHeight: float
    
    carrier: str
    serviceCode: str
    validateAddress: str = "validate_and_clean"
    telegram_user_id: Optional[str] = None
    telegram_username: Optional[str] = None