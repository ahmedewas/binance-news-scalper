"""Volume Profile Calculator: Computes POC (Point of Control) and 70% Value Area (VAH/VAL)."""
from typing import List, Dict, Any, Tuple


class VolumeProfileAnalyzer:
    def __init__(self, num_bins: int = 25, value_area_pct: float = 0.70):
        self.num_bins = num_bins
        self.va_pct = value_area_pct

    def compute_profile(self, klines: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculates POC, VAH, VAL, and total profile volume."""
        if not klines or len(klines) < 2:
            return {"poc": 0.0, "vah": 0.0, "val": 0.0, "total_vol": 0.0}

        highs = [float(k.get("high", 0.0)) for k in klines]
        lows = [float(k.get("low", 0.0)) for k in klines]
        min_p, max_p = min(lows), max(highs)

        if min_p <= 0 or max_p <= min_p:
            return {"poc": min_p, "vah": max_p, "val": min_p, "total_vol": 0.0}

        bin_size = (max_p - min_p) / self.num_bins
        bins = [0.0] * self.num_bins

        for k in klines:
            h, l, v = float(k.get("high", 0)), float(k.get("low", 0)), float(k.get("volume", 0))
            if v <= 0 or h <= l:
                continue
            start_bin = min(self.num_bins - 1, max(0, int((l - min_p) / bin_size)))
            end_bin = min(self.num_bins - 1, max(0, int((h - min_p) / bin_size)))
            cnt = (end_bin - start_bin) + 1
            vol_per_bin = v / cnt
            for b in range(start_bin, end_bin + 1):
                bins[b] += vol_per_bin

        total_vol = sum(bins)
        poc_idx = max(range(self.num_bins), key=lambda i: bins[i])
        poc_price = min_p + (poc_idx + 0.5) * bin_size

        # Find Value Area: expand outward from POC until 70% volume is covered
        target_vol = total_vol * self.va_pct
        accum_vol = bins[poc_idx]
        low_idx, high_idx = poc_idx, poc_idx

        while accum_vol < target_vol and (low_idx > 0 or high_idx < self.num_bins - 1):
            next_low = bins[low_idx - 1] if low_idx > 0 else 0.0
            next_high = bins[high_idx + 1] if high_idx < self.num_bins - 1 else 0.0
            if next_high >= next_low and high_idx < self.num_bins - 1:
                high_idx += 1
                accum_vol += next_high
            elif low_idx > 0:
                low_idx -= 1
                accum_vol += next_low
            else:
                break

        val_price = min_p + low_idx * bin_size
        vah_price = min_p + (high_idx + 1) * bin_size

        return {"poc": round(poc_price, 6), "vah": round(vah_price, 6),
                "val": round(val_price, 6), "total_vol": round(total_vol, 2)}

    def evaluate_entry_edge(self, current_price: float, klines: List[Dict[str, Any]]) -> Tuple[bool, str, float]:
        """Evaluates entry quality relative to Volume Profile Value Area."""
        vp = self.compute_profile(klines)
        if current_price <= 0 or vp["poc"] <= 0:
            return True, "VP_BYPASS", 0.0

        # Institutional sweet spot: near Value Area Low or reclaiming POC
        if current_price <= vp["val"] * 1.003:
            return True, "VP_VALUE_AREA_ACCUMULATION: Buying near institutional VAL", 8.0
        if abs(current_price - vp["poc"]) / current_price <= 0.002:
            return True, "VP_POC_SUPPORT: Reclaiming high-volume POC node", 5.0
        if current_price >= vp["vah"] * 1.015:
            return False, "VP_EXTENDED_ABOVE_VAH: Risk of mean reversion into value", -10.0

        return True, "VP_FAIR_VALUE: Within normal value area corridor", 0.0
