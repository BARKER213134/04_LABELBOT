import logging
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MAX_TEMPLATES_PER_USER = 10


class TemplatesService:
    """Service for managing user templates"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.templates
    
    async def get_user_templates(self, telegram_id: str) -> List[Dict[str, Any]]:
        """Get all templates for a user"""
        cursor = self.collection.find(
            {"user_telegram_id": telegram_id},
            {"_id": 0}
        ).sort("use_count", -1)
        
        templates = await cursor.to_list(length=MAX_TEMPLATES_PER_USER)
        return templates
    
    async def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a template by ID"""
        template = await self.collection.find_one(
            {"template_id": template_id},
            {"_id": 0}
        )
        return template
    
    async def get_templates_count(self, telegram_id: str) -> int:
        """Get count of templates for a user"""
        count = await self.collection.count_documents({"user_telegram_id": telegram_id})
        return count
    
    async def create_template(
        self,
        telegram_id: str,
        name: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new template"""
        # Check limit
        count = await self.get_templates_count(telegram_id)
        if count >= MAX_TEMPLATES_PER_USER:
            logger.warning(f"User {telegram_id} reached template limit ({MAX_TEMPLATES_PER_USER})")
            return None
        
        template_id = str(uuid.uuid4())[:8]
        
        # Convert weight from oz to lbs for storage
        weight_oz = data.get("packageWeight", 0) or 0
        weight_lbs = weight_oz / 16 if weight_oz else data.get("packageWeightLbs", 0)
        
        template = {
            "template_id": template_id,
            "user_telegram_id": telegram_id,
            "name": name,
            "ship_from_name": data.get("shipFromName"),
            "ship_from_address": data.get("shipFromAddressLine1"),
            "ship_from_city": data.get("shipFromCity"),
            "ship_from_state": data.get("shipFromState"),
            "ship_from_zip": data.get("shipFromPostalCode"),
            "ship_from_phone": data.get("shipFromPhone"),
            "ship_to_name": data.get("shipToName"),
            "ship_to_address": data.get("shipToAddressLine1"),
            "ship_to_city": data.get("shipToCity"),
            "ship_to_state": data.get("shipToState"),
            "ship_to_zip": data.get("shipToPostalCode"),
            "ship_to_phone": data.get("shipToPhone"),
            "package_weight_lbs": weight_lbs,  # Store in lbs
            "package_weight": weight_oz,  # Keep oz for backwards compatibility
            "package_length": data.get("packageLength"),
            "package_width": data.get("packageWidth"),
            "package_height": data.get("packageHeight"),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "use_count": 0
        }
        
        await self.collection.insert_one(template)
        logger.info(f"Created template '{name}' for user {telegram_id}")
        
        template.pop("_id", None)
        return template
    
    async def update_template(
        self,
        template_id: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a template"""
        update_data = {
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Map data fields to template fields
        field_mapping = {
            "shipFromName": "ship_from_name",
            "shipFromAddressLine1": "ship_from_address",
            "shipFromCity": "ship_from_city",
            "shipFromState": "ship_from_state",
            "shipFromPostalCode": "ship_from_zip",
            "shipFromPhone": "ship_from_phone",
            "shipToName": "ship_to_name",
            "shipToAddressLine1": "ship_to_address",
            "shipToCity": "ship_to_city",
            "shipToState": "ship_to_state",
            "shipToPostalCode": "ship_to_zip",
            "shipToPhone": "ship_to_phone",
            "packageWeight": "package_weight",
            "packageLength": "package_length",
            "packageWidth": "package_width",
            "packageHeight": "package_height",
            "name": "name"
        }
        
        for data_key, template_key in field_mapping.items():
            if data_key in data:
                update_data[template_key] = data[data_key]
        
        await self.collection.update_one(
            {"template_id": template_id},
            {"$set": update_data}
        )
        
        return await self.get_template(template_id)
    
    async def delete_template(self, template_id: str) -> bool:
        """Delete a template"""
        result = await self.collection.delete_one({"template_id": template_id})
        return result.deleted_count > 0
    
    async def increment_use_count(self, template_id: str):
        """Increment template use count"""
        await self.collection.update_one(
            {"template_id": template_id},
            {
                "$inc": {"use_count": 1},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )
    
    def template_to_user_data(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Convert template to user_data format for conversation"""
        return {
            "shipFromName": template.get("ship_from_name"),
            "shipFromAddressLine1": template.get("ship_from_address"),
            "shipFromCity": template.get("ship_from_city"),
            "shipFromState": template.get("ship_from_state"),
            "shipFromPostalCode": template.get("ship_from_zip"),
            "shipFromPhone": template.get("ship_from_phone"),
            "shipToName": template.get("ship_to_name"),
            "shipToAddressLine1": template.get("ship_to_address"),
            "shipToCity": template.get("ship_to_city"),
            "shipToState": template.get("ship_to_state"),
            "shipToPostalCode": template.get("ship_to_zip"),
            "shipToPhone": template.get("ship_to_phone"),
            "packageWeight": template.get("package_weight"),
            "packageLength": template.get("package_length"),
            "packageWidth": template.get("package_width"),
            "packageHeight": template.get("package_height"),
        }
