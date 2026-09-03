"""Hệ thống đăng ký và tự động khám phá bộ điều khiển đèn giao thông (Controller Registry).

Cho phép thêm thuật toán mới theo nguyên lý Open-Closed (OCP):
- Chỉ cần gắn decorator `@register_controller` lên class thuật toán mới.
- Không cần chỉnh sửa run.py hay bất kỳ file có sẵn nào.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseController


@dataclass
class ControllerMetadata:
    """Thông tin đăng ký của một thuật toán điều khiển."""

    name: str  # Tên định danh chính (vd: "fixedtime")
    cls: Type[BaseController]  # Class thực thi
    aliases: list[str] = field(default_factory=list)  # Các tên viết tắt (vd: ["ft"])
    display_name: str = ""  # Tên hiển thị trên bảng so sánh (vd: "Fixed-Time")
    description: str = ""  # Mô tả tóm tắt thuật toán


class ControllerRegistry:
    """Kho lưu trữ trung tâm các bộ điều khiển đèn giao thông đã được đăng ký."""

    def __init__(self):
        self._registry: dict[str, ControllerMetadata] = {}
        self._alias_map: dict[str, str] = {}  # alias -> primary_name

    def register(
        self,
        name: str,
        aliases: list[str] | None = None,
        display_name: str | None = None,
        description: str = "",
    ) -> Callable[[Type[BaseController]], Type[BaseController]]:
        """Decorator để đăng ký một thuật toán điều khiển vào hệ thống.

        Ví dụ:
            @register_controller(name="my_algo", aliases=["ma"], display_name="My Algorithm")
            class MyAlgoController(BaseController):
                ...
        """
        aliases = aliases or []
        primary_name = name.strip().lower()

        def decorator(cls: Type[BaseController]) -> Type[BaseController]:
            # Gán thuộc tính nhận diện lên class
            cls.name = primary_name
            disp_name = display_name or cls.__name__
            cls.display_name = disp_name

            metadata = ControllerMetadata(
                name=primary_name,
                cls=cls,
                aliases=[a.strip().lower() for a in aliases],
                display_name=disp_name,
                description=description or (cls.__doc__ or "").strip().split("\n")[0],
            )
            self._registry[primary_name] = metadata

            # Đăng ký các alias
            for alias in metadata.aliases:
                self._alias_map[alias] = primary_name

            return cls

        return decorator

    def get(self, name_or_alias: str) -> Type[BaseController]:
        """Lấy class controller theo tên chính hoặc tên viết tắt."""
        key = name_or_alias.strip().lower()
        primary_name = self._alias_map.get(key, key)
        if primary_name in self._registry:
            return self._registry[primary_name].cls

        available = list(self.get_all_names(include_aliases=True))
        raise KeyError(
            f"Không tìm thấy thuật toán: '{name_or_alias}'. "
            f"Các thuật toán hiện có: {', '.join(sorted(available))}"
        )

    def get_metadata(self, name_or_alias: str) -> ControllerMetadata:
        """Lấy thông tin metadata của thuật toán theo tên hoặc alias."""
        key = name_or_alias.strip().lower()
        primary_name = self._alias_map.get(key, key)
        if primary_name in self._registry:
            return self._registry[primary_name]
        raise KeyError(f"Không tìm thấy thông tin cho thuật toán: '{name_or_alias}'")

    def get_all(self) -> dict[str, ControllerMetadata]:
        """Trả về toàn bộ danh sách metadata các thuật toán đã đăng ký."""
        return dict(self._registry)

    def get_all_names(self, include_aliases: bool = False) -> list[str]:
        """Trả về danh sách tên các thuật toán."""
        names = list(self._registry.keys())
        if include_aliases:
            names.extend(self._alias_map.keys())
        return names

    def auto_discover(self, package_path: Path | None = None) -> None:
        """Tự động quét thư mục controllers để import các file .py mới."""
        if package_path is None:
            package_path = Path(__file__).parent

        for file_path in package_path.glob("*.py"):
            mod_name = file_path.stem
            if mod_name in ("__init__", "base", "registry"):
                continue
            full_module_name = f"src.traffic_control.controllers.{mod_name}"
            try:
                importlib.import_module(full_module_name)
            except Exception as e:
                # Không làm crash nếu một file thử nghiệm bị lỗi cú pháp
                import warnings
                warnings.warn(f"Không thể tải controller từ {file_path.name}: {e}")


# Singleton instance toàn cục
CONTROLLER_REGISTRY = ControllerRegistry()
register_controller = CONTROLLER_REGISTRY.register
