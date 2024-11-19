from unicorn_binance_rest_api import BinanceRestApiManager
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import openai
import logging

class CryptoTrendAnalyzer:
    def __init__(self, config):
        self.config = config
        self.binance_client = BinanceRestApiManager()
        openai.api_key = self.config.OPENAI_API_KEY
        
    def get_historical_data(self, symbol, interval=None, days=None):
        """獲取歷史價格數據"""
        try:
            # 使用配置中的默認值
            interval = interval or self.config.TIMEFRAMES['default']
            days = days or self.config.ANALYSIS['default_days']
            
            if days > self.config.ANALYSIS['max_days']:
                days = self.config.ANALYSIS['max_days']
                
            start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            if not self.config.is_valid_symbol(symbol):
                raise ValueError(f"無效的交易對: {symbol}")
            
            klines = self.binance_client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_time
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 
                'volume', 'close_time', 'quote_volume', 'trades',
                'taker_base', 'taker_quote', 'ignore'
            ])
            
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            df.set_index('timestamp', inplace=True)
            
            return df
        
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return None

    def calculate_technical_indicators(self, df):
        """計算技術指標"""
        df = df.copy()
        
        # 計算多個MA週期
        for period in self.config.INDICATORS['MA']['periods']:
            df[f'MA{period}'] = df['close'].rolling(window=period).mean()
        
        # 計算趨勢線
        df['trend_line'] = self._calculate_trend_line(df['close'])
        
        # 計算支撐和阻力位
        df['support'], df['resistance'] = self._calculate_support_resistance(df)
        
        # 計算布林帶
        bb_period = self.config.INDICATORS['Bollinger']['period']
        bb_std = self.config.INDICATORS['Bollinger']['std_dev']
        df['BB_middle'] = df['close'].rolling(window=bb_period).mean()
        std = df['close'].rolling(window=bb_period).std()
        df['BB_upper'] = df['BB_middle'] + (std * bb_std)
        df['BB_lower'] = df['BB_middle'] - (std * bb_std)
        
        # 計算RSI
        rsi_period = self.config.INDICATORS['RSI']['period']
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # 檢測趨勢突破
        df['trend_break'] = self._detect_trend_breaks(df)
        
        return df
    
    def _calculate_trend_line(self, prices):
        """使用線性回歸計算趨勢線"""
        if len(prices) < self.config.TREND['min_points']:
            return pd.Series(index=prices.index, dtype=float)
            
        x = np.arange(len(prices))
        y = prices.values
        
        coefficients = np.polyfit(x, y, 1)
        trend_line = coefficients[0] * x + coefficients[1]
        
        return trend_line
    
    def _calculate_support_resistance(self, df):
        """計算支撐和阻力位"""
        period = self.config.INDICATORS['MA']['default_period']
        support = df['low'].rolling(window=period).min()
        resistance = df['high'].rolling(window=period).max()
        
        return support, resistance
    
    def _detect_trend_breaks(self, df):
        """檢測趨勢突破"""
        breaks = pd.Series(index=df.index, dtype=float)
        breakout_threshold = self.config.TREND['breakout_threshold']
        
        # 向上突破
        up_break = (df['close'] > df['resistance'].shift(1) * (1 + breakout_threshold)) & \
                   (df['close'].shift(1) <= df['resistance'].shift(1))
        
        # 向下突破
        down_break = (df['close'] < df['support'].shift(1) * (1 - breakout_threshold)) & \
                     (df['close'].shift(1) >= df['support'].shift(1))
        
        breaks[up_break] = 1    # 向上突破
        breaks[down_break] = -1  # 向下突破
        
        return breaks
    
    def analyze_trends(self, symbol, interval='1d', days=30):
        """分析趨勢並生成報告"""
        try:
            # 獲取數據
            df = self.get_historical_data(symbol, interval, days)
            if df is None:
                return {
                    'technical_data': {
                        'break_analysis': 'N/A',
                        'current_price': None,
                        'trend_line': None,
                        'support': None,
                        'resistance': None,
                        'rsi': None
                    },
                    'analysis': '無法獲取市場數據'
                }
                
            # 計算指標
            df = self.calculate_technical_indicators(df)
            
            # 準備分析數據
            current_price = df['close'].iloc[-1]
            trend_line_value = df['trend_line'].iloc[-1]
            support = df['support'].iloc[-1]
            resistance = df['resistance'].iloc[-1]
            rsi = df['RSI'].iloc[-1]
            
            # 檢查是否是重要時刻
            is_critical = self._is_critical_moment(df, current_price, trend_line_value, support, resistance, rsi)
            
            # 檢查最近的趨勢突破
            recent_breaks = df['trend_break'].dropna()[-5:]
            break_analysis = "無明顯突破"
            if (recent_breaks == 1).any():
                break_analysis = "最近出現向上突破"
            elif (recent_breaks == -1).any():
                break_analysis = "最近出現向下突破"

            technical_data = {
                'current_price': current_price,
                'trend_line': trend_line_value,
                'support': support,
                'resistance': resistance,
                'rsi': rsi,
                'break_analysis': break_analysis,
                'is_critical': is_critical
            }

            # 只在重要時刻調用 OpenAI
            if is_critical:
                analysis_text = self._perform_ai_analysis(symbol, technical_data, df)
            else:
                analysis_text = self._generate_basic_analysis(technical_data)

            return {
                'technical_data': technical_data,
                'analysis': analysis_text
            }
                
        except Exception as e:
            logging.error(f"分析過程出錯: {e}")
            return {
                'technical_data': {
                    'break_analysis': 'Error',
                    'current_price': None,
                    'trend_line': None,
                    'support': None,
                    'resistance': None,
                    'rsi': None,
                    'is_critical': False
                },
                'analysis': f'分析錯誤: {str(e)}'
            }
        
    def _is_critical_moment(self, df, current_price, trend_line, support, resistance, rsi):
        """判斷是否是重要時刻"""
        try:
            # 1. 檢查趨勢線突破
            trend_break = False
            if trend_line:
                break_threshold = self.config.TREND['breakout_threshold']
                if abs(current_price - trend_line) / trend_line > break_threshold:
                    trend_break = True

            # 2. 檢查支撐/阻力位突破
            support_resistance_break = False
            if support and resistance:
                price_threshold = (resistance - support) * 0.02  # 2% 緩衝區
                if abs(current_price - support) < price_threshold or \
                abs(current_price - resistance) < price_threshold:
                    support_resistance_break = True

            # 3. 檢查 RSI 極值
            rsi_extreme = False
            if rsi is not None:
                if rsi >= 70 or rsi <= 30:
                    rsi_extreme = True

            # 4. 檢查成交量異常
            volume_spike = False
            if not df['volume'].empty:
                avg_volume = df['volume'].rolling(window=20).mean()
                current_volume = df['volume'].iloc[-1]
                if current_volume > avg_volume.iloc[-1] * 2:  # 成交量是平均的2倍
                    volume_spike = True

            # 5. 檢查假突破
            fake_breakout = self._check_fake_breakout(df)

            # 返回是否是重要時刻
            return trend_break or support_resistance_break or rsi_extreme or volume_spike or fake_breakout

        except Exception as e:
            logging.error(f"判斷重要時刻時出錯: {e}")
            return False

    def _check_fake_breakout(self, df):
        """檢查是否出現假突破"""
        try:
            if len(df) < 3:
                return False

            # 獲取最近三根K線
            last_three = df.tail(3)
            
            # 檢查上升假突破
            resistance = df['resistance'].iloc[-3]
            if (last_three['high'].iloc[0] > resistance and  # 第一根突破
                last_three['close'].iloc[1] > resistance and  # 第二根維持
                last_three['close'].iloc[2] < resistance):    # 第三根回落
                return True

            # 檢查下跌假突破
            support = df['support'].iloc[-3]
            if (last_three['low'].iloc[0] < support and    # 第一根突破
                last_three['close'].iloc[1] < support and   # 第二根維持
                last_three['close'].iloc[2] > support):     # 第三根回升
                return True

            return False

        except Exception as e:
            logging.error(f"檢查假突破時出錯: {e}")
            return False

    def _generate_basic_analysis(self, technical_data):
        """生成基本分析文本（不使用 AI）"""
        try:
            trend = technical_data['break_analysis']
            rsi = technical_data['rsi']
            current_price = technical_data['current_price']
            
            analysis = []
            
            # 趨勢分析
            analysis.append(f"當前趨勢: {trend}")
            
            # RSI 分析
            if rsi >= 70:
                analysis.append(f"RSI ({rsi:.1f}) 顯示市場處於超買狀態")
            elif rsi <= 30:
                analysis.append(f"RSI ({rsi:.1f}) 顯示市場處於超賣狀態")
            else:
                analysis.append(f"RSI ({rsi:.1f}) 處於正常區間")
            
            # 支撐阻力分析
            support = technical_data['support']
            resistance = technical_data['resistance']
            if support and resistance:
                analysis.append(f"支撐位: ${support:.2f}")
                analysis.append(f"阻力位: ${resistance:.2f}")
            
            return "\n".join(analysis)
            
        except Exception as e:
            logging.error(f"生成基本分析時出錯: {e}")
            return "無法生成分析"

    def _perform_ai_analysis(self, symbol, technical_data, df):
        """在重要時刻執行 AI 分析"""
        try:
            # 準備更詳細的 prompt
            prompt = self._prepare_critical_prompt(symbol, technical_data, df)
            
            client = openai.OpenAI(api_key=self.config.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=self.config.OPENAI['model'],
                messages=[
                    {"role": "system", "content": "你是一個專業的技術分析師，專注於加密貨幣市場的趨勢分析和假突破判斷。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.OPENAI['temperature'],
                max_tokens=self.config.OPENAI['max_tokens']
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"AI 分析生成失敗: {e}")
            return self._generate_basic_analysis(technical_data)  # 失敗時返回基本分析

    def _prepare_critical_prompt(self, symbol, technical_data, df):
        """準備重要時刻的詳細提示"""
        return f"""
        請分析 {symbol} 的重要市場信號：
        
        價格數據：
        - 當前價格: ${technical_data['current_price']:.2f}
        - 趨勢線價格: ${technical_data['trend_line']:.2f}
        - 支撐位: ${technical_data['support']:.2f}
        - 阻力位: ${technical_data['resistance']:.2f}
        - RSI: {technical_data['rsi']:.2f}
        
        市場狀況：
        {technical_data['break_analysis']}
        
        請特別關注：
        1. 是否出現假突破
        2. 突破的有效性
        3. 建議的操作策略
        4. 風險提示
        
        請提供專業但易懂的分析。
        """

    def get_realtime_price(self, symbol):
        """獲取即時價格"""
        if not self.config.is_valid_symbol(symbol):
            return None
            
        try:
            ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"Error getting price: {e}")
            return None