from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Auction Scout API"
    database_url: str = "sqlite+aiosqlite:///./auction_scout.db"
    allowed_origins: str = "http://localhost:5173"

    default_currency: str = "CAD"
    default_tax_rate: float = 0.12
    default_shipping_estimate: float = 40.0
    target_margin_pct: float = 0.30

    enable_llm_query_builder: bool = True
    enable_ebay_sold_prices: bool = False
    ebay_browse_base_url: str = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    ebay_access_token: str | None = None
    ebay_marketplace_id: str = "EBAY_CA"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
