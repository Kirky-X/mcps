# Copyright (c) Kirky.X. 2025. All rights reserved.
from typing import Dict, Any, Optional

from jinja2 import TemplateError
from jinja2.sandbox import SandboxedEnvironment

from ..utils.exceptions import TemplateRenderError, ValidationError


class TemplateService:
    def __init__(self):
        """初始化安全的 Jinja2 模板环境

        使用 `SandboxedEnvironment` 构建受限模板环境，启用自动转义与空白控制，并移除潜在不安全的全局函数以降低模板执行风险。

        Args:
            None

        Returns:
            None

        Raises:
            Exception: 当环境初始化失败时可能抛出异常。
        """
        self.env = SandboxedEnvironment(
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        # Disable dangerous globals
        self.env.globals.pop('range', None)
        self.env.globals.pop('dict', None)
        try:
            self.env.filters.pop('map')
        except Exception:
            pass

    def render(self, content: str, template_vars: Dict[str, Any], var_definitions: Optional[Dict[str, Any]]) -> str:
        """渲染模板内容并进行变量校验与默认值填充

        在渲染前根据变量定义校验必填项与默认值，随后使用沙箱环境渲染字符串模板。异常统一封装为 `TemplateRenderError`。

        Args:
            content (str): 模板字符串内容。
            template_vars (Dict[str, Any]): 渲染所需变量字典。
            var_definitions (Optional[Dict[str, Any]]): 变量定义，支持 `required` 与 `default` 键。

        Returns:
            str: 渲染后的字符串结果。

        Raises:
            ValidationError: 当必填变量缺失且无默认值时抛出。
            TemplateRenderError: 当模板语法或渲染过程发生错误时抛出。
        """
        # Validate required variables
        if var_definitions:
            for var_name, var_config in var_definitions.items():
                if var_config.get('required', False):
                    if var_name not in template_vars:
                        if var_config.get('default') is not None:
                            template_vars[var_name] = var_config['default']
                        else:
                            raise ValidationError(f"Required template variable '{var_name}' not provided")
                elif var_name not in template_vars and var_config.get('default') is not None:
                    template_vars[var_name] = var_config['default']

        try:
            import re
            if not var_definitions and not template_vars:
                if "{{" in content or "{%" in content or "__" in content:
                    raise TemplateRenderError("Unsafe template content blocked")
                return content
            def _to_jinja(s: str) -> str:
                return re.sub(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", r"{{ \1 }}", s)
            template = self.env.from_string(_to_jinja(content))
            return template.render(**(template_vars or {}))
        except TemplateError as e:
            raise TemplateRenderError(f"Template rendering error: {str(e)}")
