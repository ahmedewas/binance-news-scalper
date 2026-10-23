"""Quantitative safety filters and microstructure checks for opportunity evaluation."""
from typing import Tuple, List, Dict, Any, Optional
from src.core.btc_gate import BitcoinMarketGate
from src.core.adaptive_regulator import AdaptiveScoreRegulator
from src.core.mtf_confluence import MultiTimeframeConfluence
from src.core.hurst_filter import HurstFilter
from src.core.cvd_tracker import CVDTracker
from src.exchange.slippage_guard import SlippageGuard
from src.exchange.orderbook_depth import OrderBookDepthGuard


class OpportunityFilters:
    @staticmethod
    def check_macro_gates(symbol: str, exchange, min_score: float) -> Tuple[bool, float, str, str]:
        """Validates BTC crash gate, adaptive regulator, and 15m MTF confluence."""
        eff_threshold = min_score
        if not symbol.startswith("BTC"):
            btc_kl = exchange.get_historical_klines("BTC/USDT", "1m", 6)
            is_btc_safe, btc_reason = BitcoinMarketGate().evaluate(btc_kl)
            if not is_btc_safe:
                return False, eff_threshold, "BTC_VETO", btc_reason
            btc_15m = exchange.get_historical_klines("BTC/USDT", "15m", 15)
            if btc_15m:
                eff_threshold, _, reg_msg = AdaptiveScoreRegulator(min_score).evaluate_regime(btc_15m)
                if eff_threshold >= 99.0:
                    return False, eff_threshold, "MACRO_VETO", reg_msg

        from src.core.sector_gate import SectorLeaderGate
        sec_safe, sec_msg, sec_bonus = SectorLeaderGate().evaluate_sector(symbol, exchange)
        if not sec_safe:
            return False, eff_threshold, "SECTOR_VETO", sec_msg
        if sec_bonus > 0:
            eff_threshold = max(55.0, eff_threshold - sec_bonus)

        kl_15m = exchange.get_historical_klines(symbol, "15m", 25)
        if kl_15m:
            aligned, mtf_msg = MultiTimeframeConfluence().check_higher_timeframe(kl_15m)
            if not aligned:
                return False, eff_threshold, "MTF_VETO", mtf_msg

        return True, eff_threshold, "", ""

    @staticmethod
    def calculate_alpha_metrics(klines: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
        """Computes Hurst Exponent fractal persistence and CVD order flow delta."""
        try:
            closes = [float(k.get("close", 0.0)) for k in klines]
            ok_h, h_score, _ = HurstFilter().validate_market_regime(closes)
            cvd_score, _ = CVDTracker().evaluate_order_flow(klines)
            eff_hurst = h_score if ok_h else None
            return eff_hurst, cvd_score
        except Exception:
            return None, 50.0

    @staticmethod
    def check_microstructure(symbol: str, klines: List[Dict[str, Any]], cur_price: float) -> Tuple[bool, str]:
        """Validates market buy spread slippage and L2 order book imbalance walls."""
        if cur_price > 0 and klines:
            ok_slip, msg_slip, _ = SlippageGuard().validate_buy_slippage(symbol, float(klines[-1]["close"]), cur_price)
            if not ok_slip:
                return False, msg_slip
            ok_obi, msg_obi, _ = OrderBookDepthGuard().evaluate_depth(symbol)
            if not ok_obi:
                return False, msg_obi
        return True, ""
