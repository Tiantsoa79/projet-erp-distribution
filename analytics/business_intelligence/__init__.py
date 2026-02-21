"""
Business Intelligence Module - ERP Distribution

Ce module contient les tableaux de bord et calculateurs de KPIs
pour l'analyse business intelligence.
"""

from .kpis_calculator import KPIsCalculator
from .dashboard_strategic import StrategicDashboard
from .dashboard_tactical import TacticalDashboard
from .dashboard_operational import OperationalDashboard

__version__ = "1.0.0"
__author__ = "ERP Distribution Team"

# Classes exportées pour faciliter l'import
__all__ = [
    'KPIsCalculator',
    'StrategicDashboard', 
    'TacticalDashboard',
    'OperationalDashboard'
]
