# 하위 호환 re-export — 실제 구현은 각 모듈에 있음
from collectors.welfare.central_collector import WelfareCentralCollector
from collectors.welfare.local_collector import WelfareLocalCollector

__all__ = ["WelfareCentralCollector", "WelfareLocalCollector"]
