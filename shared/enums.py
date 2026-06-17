from enum import Enum

class UserRole(str, Enum):
    customer = "CUSTOMER"
    restaurant_owner = "RESTAURANT_OWNER"
    rider = "RIDER"
    admin = "ADMIN"


# ── Approval flow status ───────────────────────────────────────────────────────
# Decision 3: enum for the PENDING → ACTIVE → SUSPENDED lifecycle.
# Lowercase member names to match your UserRole convention.
class RestaurantStatus(str, Enum):
    pending = "PENDING"      # just created, awaiting admin approval
    active = "ACTIVE"        # approved — shows in public listings
    suspended = "SUSPENDED"  # taken down by admin

# ── Cuisine ────────────────────────────────────────────────────────────────────
# Decision 1: an enum of allowed values, stored as a Postgres ARRAY on Restaurant.
# A restaurant can be multi-cuisine ("Nepali + Indian"). Array keeps it simple;
# we can still filter with `.any()`. If you later need heavy cuisine querying
# (counts, joins), migrate to a separate cuisines table.
class CuisineType(str, Enum):
    nepali = "NEPALI"
    indian = "INDIAN"
    chinese = "CHINESE"
    continental = "CONTINENTAL"
    fast_food = "FAST_FOOD"
    italian = "ITALIAN"
    tibetan = "TIBETAN"
    bakery = "BAKERY"
    beverages = "BEVERAGES"
    other = "OTHER"


class RestaurantSortBy(str, Enum):
    rating = "rating"               # highest rated first
    delivery_time = "delivery_time" # fastest delivery first
    delivery_fee = "delivery_fee"   # cheapest delivery first
    newest = "newest"               # most recently added first