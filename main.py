import time
import threading
from datetime import datetime
import logging
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich import box
from config.config import Config
from src.analyzer import CryptoTrendAnalyzer

class CryptoRealtimeAgent:
    def __init__(self):
        # 保持原有的初始化
        self.config = Config()
        self.analyzer = CryptoTrendAnalyzer(self.config)
        self.console = Console()
        
        self.current_prices = {}
        self.price_changes = {}
        self.last_analysis = {}
        self.alerts = []
        self.processed_alerts = set()

        # 初始化日誌
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
    def update_prices(self):
        """更新即時價格"""
        for symbol in self.config.SYMBOLS_TO_MONITOR:
            try:
                # 獲取當前價格
                price = self.analyzer.get_realtime_price(symbol)
                if price:
                    # 計算價格變化
                    old_price = self.current_prices.get(symbol, {}).get('price')
                    if old_price:
                        change = ((price - old_price) / old_price) * 100
                    else:
                        change = 0
                        
                    # 更新價格數據
                    self.current_prices[symbol] = {
                        'price': price,
                        'timestamp': datetime.now()
                    }
                    
                    # 更新價格變化
                    self.price_changes[symbol] = {
                        'change_percent': f"{change:+.2f}"
                    }
                    
                    logging.debug(f"{symbol} 價格更新: ${price:,.2f} ({change:+.2f}%)")
                    
                    # 檢查價格警報
                    self.check_price_alerts(symbol, price)
                    
            except Exception as e:
                logging.error(f"更新 {symbol} 價格時出錯: {e}")
                # 保持最後一次有效的價格
                if symbol not in self.current_prices:
                    self.current_prices[symbol] = {
                        'price': 'N/A',
                        'timestamp': datetime.now()
                    }

    def add_alert(self, message, alert_id):
        """添加新警報"""
        if alert_id not in self.processed_alerts:
            # 創建新警報
            new_alert = {
                'message': message,
                'timestamp': datetime.now(),
                'id': alert_id
            }
            
            # 添加到警報列表
            self.alerts.append(new_alert)
            # 記錄已處理的警報ID
            self.processed_alerts.add(alert_id)
            
            # 記錄到日誌
            logging.info(f"新警報: {message}")
            
            # 保持警報列表在合理大小（只保留最新的5條）
            if len(self.alerts) > 5:
                self.alerts = self.alerts[-5:]
            
            # 清理過期的處理記錄（可選）
            if len(self.processed_alerts) > 1000:
                # 只保留最近的警報ID
                self.processed_alerts = set(alert['id'] for alert in self.alerts)
        
    def perform_analysis(self):
        """執行完整分析"""
        for symbol in self.config.SYMBOLS_TO_MONITOR:
            try:
                analysis = self.analyzer.analyze_trends(symbol)
                
                if isinstance(analysis, dict):
                    self.last_analysis[symbol] = analysis
                    
                    # 檢查是否是重要時刻
                    technical_data = analysis.get('technical_data', {})
                    if technical_data.get('is_critical', False):
                        # 生成重要時刻警報
                        alert_id = f"{symbol}_critical_{datetime.now().strftime('%Y%m%d_%H%M')}"
                        self.add_alert(
                            f"⚠️ {symbol} 出現重要信號！\n{analysis.get('analysis', '未有分析')}",
                            alert_id
                        )
                        logging.info(f"{symbol} 出現重要信號")
                    
                    logging.info(f"完成 {symbol} 的分析更新")
                else:
                    logging.warning(f"{symbol} 分析返回非預期格式: {analysis}")
                    self.last_analysis[symbol] = self._get_default_analysis()
                    
            except Exception as e:
                logging.error(f"分析 {symbol} 時出錯: {e}")
                self.last_analysis[symbol] = self._get_default_analysis()
    
    def _get_default_analysis(self):
        """獲取默認的分析結果"""
        return {
            'technical_data': {
                'break_analysis': 'N/A',
                'current_price': None,
                'trend_line': None,
                'support': None,
                'resistance': None,
                'rsi': None,
                'is_critical': False
            },
            'analysis': 'No analysis available'
        }

    def check_price_alerts(self, symbol, current_price):
        """檢查價格警報"""
        if symbol in self.last_analysis:
            analysis = self.last_analysis[symbol]
            technical_data = analysis.get('technical_data', {})
            
            # 只在非重要時刻檢查基本警報
            if not technical_data.get('is_critical', False):
                alert_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M')}"
                
                # 檢查趨勢線突破
                if technical_data.get('trend_line'):
                    trend_line = technical_data['trend_line']
                    threshold = self.config.TREND['breakout_threshold']
                    
                    if current_price > trend_line * (1 + threshold) and alert_id not in self.processed_alerts:
                        self.add_alert(f"🔔 {symbol} 向上突破趨勢線！當前價格: ${current_price:,.2f}", alert_id)
                    elif current_price < trend_line * (1 - threshold) and alert_id not in self.processed_alerts:
                        self.add_alert(f"⚠️ {symbol} 向下突破趨勢線！當前價格: ${current_price:,.2f}", alert_id)

    def generate_display(self):
        """生成顯示內容"""
        display = Table(title="加密貨幣即時監控", box=box.ROUNDED)
        display.add_column("交易對", style="cyan")
        display.add_column("當前價格", style="green")
        display.add_column("24h 變化", style="blue")
        display.add_column("趨勢狀態", style="magenta")
        display.add_column("RSI", style="yellow")  # 添加 RSI 列
        display.add_column("最後更新", style="yellow")

        for symbol in self.config.SYMBOLS_TO_MONITOR:
            try:
                price_data = self.current_prices.get(symbol, {})
                analysis = self.last_analysis.get(symbol, {})
                technical_data = analysis.get('technical_data', {})
                
                current_price = price_data.get('price', 'N/A')
                if current_price != 'N/A':
                    current_price = f"${current_price:,.2f}"
                
                change = self.price_changes.get(symbol, {}).get('change_percent', 'N/A')
                if change != 'N/A':
                    change_style = "green" if change.startswith('+') else "red"
                    change = f"[{change_style}]{change}%[/]"
                
                # 趨勢狀態可能包含重要時刻標記
                trend = technical_data.get('break_analysis', 'N/A')
                if technical_data.get('is_critical', False):
                    trend = f"[bold red]❗{trend}[/]"
                
                # 添加 RSI 值
                rsi = technical_data.get('rsi', 'N/A')
                if rsi != 'N/A':
                    rsi = f"{rsi:.1f}"
                    if float(rsi) > 70:
                        rsi = f"[red]{rsi}[/]"
                    elif float(rsi) < 30:
                        rsi = f"[green]{rsi}[/]"
                
                update_time = price_data.get('timestamp', datetime.now()).strftime('%H:%M:%S')
                
                display.add_row(
                    symbol,
                    str(current_price),
                    str(change),
                    str(trend),
                    str(rsi),
                    update_time
                )
                
            except Exception as e:
                logging.error(f"處理 {symbol} 顯示數據時出錯: {e}")
                display.add_row(
                    symbol,
                    "Error",
                    "Error",
                    "Error",
                    "Error",
                    datetime.now().strftime('%H:%M:%S')
                )

        return display

    def start(self):
        """啟動代理"""
        logging.info("啟動加密貨幣監控代理...")
        
        # 初始執行分析
        self.perform_analysis()
        
        # 使用 Rich 的 Live Display
        with Live(self.generate_display(), refresh_per_second=1) as live:
            try:
                last_analysis_time = datetime.now()
                last_price_update = datetime.now()
                
                while True:
                    current_time = datetime.now()
                    
                    # 每10秒更新價格
                    if (current_time - last_price_update).seconds >= 10:
                        self.update_prices()
                        last_price_update = current_time
                    
                    # 每5分鐘執行一次完整分析
                    if (current_time - last_analysis_time).seconds >= 300:
                        self.perform_analysis()
                        last_analysis_time = current_time
                    
                    # 更新顯示
                    live.update(self.generate_display())
                    
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                logging.info("正在關閉代理...")

if __name__ == "__main__":
    agent = CryptoRealtimeAgent()
    agent.start()