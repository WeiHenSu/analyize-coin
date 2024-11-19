# config/config.py

from dotenv import load_dotenv
import os
from pathlib import Path

class Config:
    def __init__(self):
        # 載入環境變數
        load_dotenv()
        
        # === API Keys ===
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        
        # === 交易對設置 ===
        self.DEFAULT_SYMBOL = "BTCUSDT"
        self.SYMBOLS_TO_MONITOR = [
            "BTCUSDT",  # 比特幣
            "ETHUSDT",  # 以太坊
            "SOLUSDT",  # 索拉納
        ]
        
        # === 時間框架設置 ===
        self.TIMEFRAMES = {
            'default': '1d',    # 預設時間框架
            'available': [      # 可用的時間框架
                '1m', '3m', '5m', '15m', '30m',  # 分鐘
                '1h', '2h', '4h', '6h', '8h', '12h',  # 小時
                '1d', '3d',  # 天
                '1w', '1M'   # 週和月
            ]
        }
        
        # === 分析設置 ===
        self.ANALYSIS = {
            'default_days': 30,     # 預設分析天數
            'max_days': 365,        # 最大分析天數
            'update_interval': 3600  # 更新間隔（秒）
        }
        
        # === 技術指標參數 ===
        self.INDICATORS = {
            'MA': {
                'periods': [5, 10, 20, 50, 100, 200],  # MA週期
                'default_period': 20
            },
            'RSI': {
                'period': 14,
                'overbought': 70,
                'oversold': 30
            },
            'MACD': {
                'fast_period': 12,
                'slow_period': 26,
                'signal_period': 9
            },
            'Bollinger': {
                'period': 20,
                'std_dev': 2
            }
        }
        
        # === 趨勢分析參數 ===
        self.TREND = {
            'min_points': 5,        # 趨勢線最小點數
            'breakout_threshold': 0.02,  # 突破閾值 (2%)
            'confirmation_periods': 3     # 確認期數
        }
        
        # === OpenAI 設置 ===
        self.OPENAI = {
            'model': 'gpt-4',
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        # === 輸出設置 ===
        self.OUTPUT = {
            'save_analysis': True,
            'output_path': Path('./output'),
            'formats': ['txt', 'json']
        }
        
        # === 警報設置 ===
        self.ALERTS = {
            'enabled': True,
            'price_change_threshold': 0.05,  # 5%
            'volume_spike_threshold': 3,      # 3倍標準差
            'rsi_alerts': {
                'oversold': 30,
                'overbought': 70
            },
            'trend_break_alerts': True
        }
        
        # === 日誌設置 ===
        self.LOGGING = {
            'enabled': True,
            'level': 'INFO',
            'log_file': 'crypto_analysis.log',
            'max_file_size': 1024 * 1024 * 10,  # 10 MB
            'backup_count': 5
        }
        
    def get_timeframe(self, timeframe=None):
        """獲取有效的時間框架"""
        if timeframe and timeframe in self.TIMEFRAMES['available']:
            return timeframe
        return self.TIMEFRAMES['default']
    
    def is_valid_symbol(self, symbol):
        """檢查交易對是否有效"""
        return symbol in self.SYMBOLS_TO_MONITOR
    
    def get_ma_periods(self, period=None):
        """獲取MA週期"""
        if period and period in self.INDICATORS['MA']['periods']:
            return period
        return self.INDICATORS['MA']['default_period']
    
    def ensure_output_path(self):
        """確保輸出路徑存在"""
        self.OUTPUT['output_path'].mkdir(parents=True, exist_ok=True)
    
    def get_alert_settings(self, alert_type):
        """獲取警報設置"""
        return self.ALERTS.get(alert_type)