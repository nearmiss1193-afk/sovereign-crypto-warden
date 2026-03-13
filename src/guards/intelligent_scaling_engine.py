class IntelligentScalingEngine:
    """
    Sovereign Prime Intelligent Scaling Engine (Phase 30)
    Implements Asymmetric Compounding to maximize profit on hot streaks
    and dynamically shield capital during cold streaks.
    """
    @staticmethod
    def calculate_risk(base_risk_usd: float, consecutive_wins: int, consecutive_losses: int) -> float:
        if consecutive_losses > 0:
            # Defensive Protocol: Cut risk in half (0.25%)
            return base_risk_usd * 0.5
        elif consecutive_wins >= 2:
            # God Mode / Aggressive: Double risk (1.0%)
            return base_risk_usd * 2.0
        elif consecutive_wins == 1:
            # Scaling Transition: 1.5x risk (0.75%)
            return base_risk_usd * 1.5
        else:
            # Neutral / Factory Reset: 1.0x risk (0.5%)
            return base_risk_usd
