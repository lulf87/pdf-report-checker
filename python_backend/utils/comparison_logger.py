"""
比对过程日志记录器
用于收集和存储详细的比对过程信息
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ComparisonStep:
    """单个比对步骤"""
    step_name: str
    start_time: float
    end_time: Optional[float] = None
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    method: str = ""
    is_success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step_name,
            "method": self.method,
            "input": self.input_data,
            "output": self.output_data,
            "execution_time_ms": int((self.end_time - self.start_time) * 1000) if self.end_time else None,
            "is_success": self.is_success,
            "error_message": self.error_message
        }


class ComparisonLogger:
    """比对过程日志记录器"""

    def __init__(self, component_name: str, enable_logging: bool = True):
        self.component_name = component_name
        self.enable_logging = enable_logging
        self.steps: List[ComparisonStep] = []
        self.current_step: Optional[ComparisonStep] = None

    def start_step(self, step_name: str, method: str = "", **inputs) -> 'ComparisonLogger':
        """开始记录一个比对步骤"""
        if not self.enable_logging:
            return self

        self.current_step = ComparisonStep(
            step_name=step_name,
            start_time=time.time(),
            input_data=dict(inputs),
            method=method
        )
        return self

    def end_step(self, success: bool = True, **outputs) -> 'ComparisonLogger':
        """结束当前比对步骤"""
        if not self.enable_logging or not self.current_step:
            return self

        self.current_step.end_time = time.time()
        self.current_step.output_data = dict(outputs)
        self.current_step.is_success = success
        self.steps.append(self.current_step)
        self.current_step = None
        return self

    def record_error(self, error_message: str):
        """记录步骤错误"""
        if self.current_step:
            self.current_step.error_message = error_message
            self.current_step.is_success = False

    def get_details(self) -> List[Dict[str, Any]]:
        """获取所有步骤详情"""
        return [step.to_dict() for step in self.steps]

    def clear(self):
        """清空记录"""
        self.steps = []
        self.current_step = None
