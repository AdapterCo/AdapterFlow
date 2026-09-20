"""Read-only diagnostics by default; explicit encryption of legacy tokens is idempotent."""
import argparse
import asyncio
import json
from sqlalchemy import select, func
from app.core.database import async_session_maker
from app.core.tokens import cipher, encrypt_token
from app.models.marketplace import MarketplaceAccount
from app.models.pricing import PricingProfile
from app.models.product import Product, ProductSupplierData

async def run(encrypt_legacy=False):
    async with async_session_maker() as session:
        accounts = (await session.scalars(select(MarketplaceAccount).with_for_update() if encrypt_legacy else select(MarketplaceAccount))).all()
        legacy = []
        for account in accounts:
            fields = [name for name in ("access_token", "refresh_token") if getattr(account, name) and not getattr(account, name).startswith("fernet:")]
            if fields:
                legacy.append(str(account.id))
                if encrypt_legacy:
                    cipher()
                    for name in fields: setattr(account, name, encrypt_token(getattr(account, name)))
                    account.verified_at = None
                    account.settings = None
        ambiguous = (await session.execute(select(ProductSupplierData.product_id).group_by(ProductSupplierData.product_id).having(func.count(func.distinct(ProductSupplierData.supplier_id)) > 1))).scalars().all()
        defaults = (await session.execute(select(PricingProfile.channel).where(PricingProfile.is_default.is_(True)).group_by(PricingProfile.channel).having(func.count() > 1))).scalars().all()
        unknown = (await session.scalars(select(Product.id).where((Product.sku == "UNKNOWN") | (Product.name == "Unnamed")))).all()
        if encrypt_legacy: await session.commit()
        print(json.dumps({"legacy_token_account_ids": legacy, "encrypted": encrypt_legacy, "products_with_multiple_suppliers_review_identity": [str(v) for v in ambiguous], "legacy_placeholder_product_ids": [str(v) for v in unknown], "channels_with_multiple_defaults": defaults}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--encrypt-legacy", action="store_true", help="Encrypt existing plaintext tokens with configured Fernet key; never print credentials")
    asyncio.run(run(parser.parse_args().encrypt_legacy))
