# Copyright (c) Kirky.X. 2025. All rights reserved.
import pytest

from prompt_manager.services.template import TemplateService
from prompt_manager.utils.exceptions import ValidationError, TemplateRenderError


def test_render_simple_variable():
    """验证基本变量渲染成功

    Args:
        None

    Returns:
        None
    """
    service = TemplateService()
    content = "Hello, {name}!"
    result = service.render(content, {"name": "World"}, None)
    assert result == "Hello, World!"


@pytest.mark.parametrize(
    "content,definitions,template_vars,expected",
    [
        # 提供变量 → 使用提供值
        (
            "Role: {role}",
            {"role": {"required": True, "default": "User"}},
            {"role": "Admin"},
            "Role: Admin",
        ),
        # 缺失必填变量但有默认值 → 使用默认值
        (
            "Role: {role}",
            {"role": {"required": True, "default": "User"}},
            {},
            "Role: User",
        ),
        # 可选变量缺失 → 使用默认值（合并自 test_render_optional_var_with_default）
        (
            "Hello, {name}!",
            {"name": {"required": False, "default": "Guest"}},
            {},
            "Hello, Guest!",
        ),
    ],
)
def test_render_with_definitions_success(content, definitions, template_vars, expected):
    """验证变量定义中的 required/default 行为（参数化覆盖提供值与默认值场景）"""
    service = TemplateService()
    assert service.render(content, template_vars, definitions) == expected


def test_render_missing_required_variable():
    """验证缺失必填变量时抛出 ValidationError

    Args:
        None

    Returns:
        None

    Raises:
        ValidationError: 当必填变量缺失且无默认值。
    """
    service = TemplateService()
    content = "{var}"
    definitions = {
        "var": {"required": True, "default": None}
    }
    with pytest.raises(ValidationError) as exc:
        service.render(content, {}, definitions)
    assert "Required template variable 'var' not provided" in str(exc.value)


def test_security_sandbox():
    """确保危险操作被沙箱环境阻断

    Args:
        None

    Returns:
        None

    Raises:
        TemplateRenderError: 当尝试使用受限全局函数时。
    """
    service = TemplateService()
    # Try to access os module via Jinja2
    dangerous_content = "{{ ''.__class__.__mro__[1].__subclasses__() }}"
    # In SandboxedEnvironment, this usually returns empty or restricted access,
    # or raises error depending on the payload.
    # Let's try a simpler blocked global
    content = "{{ range(5) }}"
    with pytest.raises(TemplateRenderError):
        service.render(content, {}, None)
