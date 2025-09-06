# Asset Type Detection and Analysis Utils
# Linus: Single source of truth for asset type detection

from typing import Dict, Any

class AssetUtils:
    """统一的资产类型检测和分析框架"""
    
    # 加密货币列表
    CRYPTO_SYMBOLS = [
        'BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'XRP', 'ADA', 'DOGE', 'SOL', 
        'DOT', 'MATIC', 'SHIB', 'DAI', 'TRX', 'AVAX', 'WBTC', 'UNI', 'ATOM',
        'LTC', 'LINK', 'ETC', 'XLM', 'ALGO', 'NEAR', 'BCH', 'VET', 'FLOW',
        'ICP', 'FIL', 'APE', 'SAND', 'MANA', 'AXS', 'THETA', 'EGLD', 'XTZ'
    ]
    
    @classmethod
    def detect_asset_type(cls, symbol: str) -> str:
        """检测资产类型
        
        Args:
            symbol: 资产符号（如 BTC/USDT, AAPL, 600519.SH）
            
        Returns:
            'crypto' | 'stock' | 'forex' | 'commodity' | 'unknown'
        """
        if not symbol:
            return 'unknown'
            
        # 清理符号
        clean_symbol = symbol.upper().replace('/', '').replace('-', '')
        
        # 检查是否为加密货币交易对
        for crypto in cls.CRYPTO_SYMBOLS:
            if crypto in clean_symbol:
                return 'crypto'
        
        # 检查是否为中国A股
        if '.SH' in symbol or '.SZ' in symbol or '.BJ' in symbol:
            return 'stock'
            
        # 检查是否为港股
        if symbol.startswith('0') and len(symbol) == 5:
            return 'stock'
            
        # 检查是否为美股（通常是1-5个字母）
        if symbol.isalpha() and 1 <= len(symbol) <= 5:
            return 'stock'
            
        # 检查是否为外汇对
        forex_pairs = ['EUR', 'USD', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF', 'CNY']
        if any(curr in symbol for curr in forex_pairs):
            return 'forex'
            
        # 检查是否为商品
        commodities = ['GOLD', 'SILVER', 'OIL', 'GAS', 'COPPER', 'WHEAT', 'CORN']
        if any(comm in symbol.upper() for comm in commodities):
            return 'commodity'
            
        return 'unknown'
    
    @classmethod
    def get_analysis_framework(cls, asset_type: str) -> Dict[str, Any]:
        """获取资产类型对应的分析框架
        
        Returns:
            包含分析要点的字典
        """
        frameworks = {
            'crypto': {
                'growth_factors': '采用率增长、机构投资者入场、技术发展、DeFi应用增长',
                'competitive_advantages': '网络效应、安全性、去中心化特性、共识机制优势',
                'positive_indicators': '链上数据、哈希率、DeFi锁仓量、钱包活跃度、交易量',
                'risk_factors': '监管风险、技术漏洞、市场操纵、泡沫风险、极端波动性',
                'valuation_methods': ['NVT比率', '梅特卡夫定律', 'Stock-to-Flow', '链上活动分析'],
                'key_metrics': ['市值', '24h交易量', '流通供应量', '最大供应量', '挖矿难度']
            },
            'stock': {
                'growth_factors': '公司市场机会、收入预测、可扩展性、新产品发布',
                'competitive_advantages': '独特产品、强势品牌、主导市场地位、护城河',
                'positive_indicators': '财务健康状况、行业趋势、积极新闻、管理团队',
                'risk_factors': '市场饱和、财务不稳定、宏观经济威胁、竞争加剧',
                'valuation_methods': ['DCF估值', 'PE倍数法', 'PB估值法', 'EV/EBITDA'],
                'key_metrics': ['营收', '净利润', 'EPS', 'ROE', '负债率']
            },
            'forex': {
                'growth_factors': '经济增长、利率差异、贸易顺差',
                'competitive_advantages': '储备货币地位、经济稳定性',
                'positive_indicators': 'GDP增长、就业数据、通胀水平',
                'risk_factors': '政治不稳定、经济衰退、央行政策',
                'valuation_methods': ['购买力平价', '利率平价', '技术分析'],
                'key_metrics': ['利率', '通胀率', 'GDP', '失业率']
            },
            'commodity': {
                'growth_factors': '供需关系、季节性需求、经济周期',
                'competitive_advantages': '资源稀缺性、生产成本优势',
                'positive_indicators': '库存水平、产量数据、需求增长',
                'risk_factors': '供应中断、需求下降、替代品威胁',
                'valuation_methods': ['成本加成法', '供需模型', '期货曲线分析'],
                'key_metrics': ['库存', '产量', '消费量', '期货价格']
            }
        }
        
        return frameworks.get(asset_type, frameworks['stock'])
    
    @classmethod
    def is_crypto(cls, symbol: str) -> bool:
        """快速判断是否为加密货币"""
        return cls.detect_asset_type(symbol) == 'crypto'
    
    @classmethod
    def is_stock(cls, symbol: str) -> bool:
        """快速判断是否为股票"""
        return cls.detect_asset_type(symbol) == 'stock'