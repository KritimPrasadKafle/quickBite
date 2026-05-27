from enum import Enum

class UserRole(str, Enum):
    customer = "CUSTOMER"
    restaurant_owner = "RESTAURANT_OWNER"
    rider = "RIDER"
    admin = "ADMIN"