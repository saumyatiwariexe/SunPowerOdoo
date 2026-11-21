from app.modules.inventory.router import router as inventory_router
from app.modules.deliveries.router import router as deliveries_router
from app.modules.warranty.router import router as warranty_router
from app.modules.billing.router import router as billing_router

api_v1.include_router(inventory_router)
api_v1.include_router(deliveries_router)
api_v1.include_router(warranty_router)
api_v1.include_router(billing_router)