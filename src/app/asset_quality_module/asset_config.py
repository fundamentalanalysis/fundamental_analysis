from .asset_models import IndustryAssetBenchmarks

def load_asset_config() -> IndustryAssetBenchmarks:
    # In a real app, this might load from a YAML file or DB based on industry
    return IndustryAssetBenchmarks()
