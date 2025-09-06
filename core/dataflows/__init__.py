# 导入基础模块
from .finnhub_utils import get_data_in_range
from .googlenews_utils import getNewsData
from .reddit_utils import fetch_top_from_category

# 导入日志模块
from core.utils.logging_manager import get_logger
logger = get_logger('agents')

# 尝试导入yfinance相关模块，如果失败则跳过
try:
    from .yfin_utils import YFinanceUtils
    YFINANCE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ yfinance模块不可用: {e}")
    YFinanceUtils = None
    YFINANCE_AVAILABLE = False

try:
    from .stockstats_utils import StockstatsUtils
    STOCKSTATS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ stockstats模块不可用: {e}")
    StockstatsUtils = None
    STOCKSTATS_AVAILABLE = False

from .interface import (
    # News and sentiment functions
    get_finnhub_news,
    get_finnhub_company_insider_sentiment,
    get_finnhub_company_insider_transactions,
    get_google_news,
    get_reddit_global_news,
    get_reddit_company_news,
    # Financial statements functions
    get_simfin_balance_sheet,
    get_simfin_cashflow,
    get_simfin_income_statements,
)

__all__ = [
    # News and sentiment functions
    "get_finnhub_news",
    "get_finnhub_company_insider_sentiment",
    "get_finnhub_company_insider_transactions",
    "get_google_news",
    "get_reddit_global_news",
    "get_reddit_company_news",
    # Financial statements functions
    "get_simfin_balance_sheet",
    "get_simfin_cashflow",
    "get_simfin_income_statements",
]
