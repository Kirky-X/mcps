"""版本工具模块 - 处理版本解析、比较和冲突检测"""

import logging
from typing import List, Dict, Any, Optional, Set
from packaging.specifiers import SpecifierSet
from packaging.version import Version, parse

logger = logging.getLogger(__name__)

class VersionUtils:
    """版本工具类"""

    @staticmethod
    def parse_python_specifier(spec_str: str) -> SpecifierSet:
        """解析Python版本约束字符串"""
        try:
            # 处理 * 或空字符串
            if not spec_str or spec_str == "*":
                return SpecifierSet("")
            return SpecifierSet(spec_str)
        except Exception as e:
            logger.warning(f"Failed to parse specifier '{spec_str}': {e}")
            return SpecifierSet("")

    @staticmethod
    def check_conflicts(constraints: Dict[str, List[str]], language: str) -> Dict[str, Any]:
        """检查依赖冲突
        
        Args:
            constraints: 字典 {library_name: [constraint1, constraint2, ...]}
            language: 编程语言
            
        Returns:
            Dict 包含 conflicts(列表) 和 suggestions(字典)
        """
        conflicts = []
        suggestions = {}

        if language.lower() == "python":
            conflicts, suggestions = VersionUtils._check_python_conflicts(constraints)
        else:
            # 对于其他语言，目前仅做简单的字符串比较或基础SemVer检查
            # 后续可集成 node-semver 等逻辑
            conflicts, suggestions = VersionUtils._check_generic_conflicts(constraints)
            
        return {
            "conflicts": conflicts,
            "suggestions": suggestions
        }

    @staticmethod
    def _check_python_conflicts(constraints: Dict[str, List[str]]) -> tuple:
        """检查Python依赖冲突"""
        conflicts = []
        suggestions = {}

        for lib_name, specs in constraints.items():
            if not specs:
                continue
                
            try:
                # 合并所有约束
                combined_spec = SpecifierSet("")
                valid_specs = []
                
                for s in specs:
                    try:
                        # 忽略无效或通配符
                        if s and s != "*":
                            current = SpecifierSet(s)
                            combined_spec &= current
                            valid_specs.append(s)
                    except Exception:
                        pass
                
                # 检查是否存在交集
                # 由于SpecifierSet本身不直接暴露"是否为空集"的API，
                # 我们通常需要通过尝试匹配版本来验证，或者依靠它在不兼容时抛出异常（但它通常只是合并）
                # 简单的冲突检测：如果合并后的约束在逻辑上不可能满足（例如 >2.0, <1.0）
                # packaging库在合并时不会自动检测逻辑冲突，直到filter时才发现。
                # 因此，更好的策略是记录所有约束，并尝试找到一个满足所有约束的"最新"版本（如果提供了候选版本列表）。
                # 但这里我们没有所有可用版本列表。
                # 替代方案：检查显式冲突，如 ==1.0 和 ==2.0
                
                # 简化策略：检测是否有互斥的固定版本
                exact_versions = set()
                for s in valid_specs:
                    if s.startswith("=="):
                        exact_versions.add(s[2:])
                
                if len(exact_versions) > 1:
                    conflicts.append({
                        "library": lib_name,
                        "constraints": specs,
                        "reason": f"Conflicting exact versions: {exact_versions}"
                    })
                    continue
                
                # 如果没有显式冲突，我们假设存在解，并建议一个满足约束的"可读"形式
                suggestions[lib_name] = str(combined_spec) if str(combined_spec) else "Any"
                
            except Exception as e:
                logger.warning(f"Error checking conflicts for {lib_name}: {e}")
                
        return conflicts, suggestions

    @staticmethod
    def _check_generic_conflicts(constraints: Dict[str, List[str]]) -> tuple:
        """通用（简单）冲突检测"""
        conflicts = []
        suggestions = {}

        for lib_name, specs in constraints.items():
            unique_specs = set(specs)
            # 如果有多个不同的版本约束，且都看似具体版本（非范围），则标记为潜在冲突
            # 这只是一个非常基础的启发式检查
            if len(unique_specs) > 1:
                # 检查是否都是具体版本（不含 > < ~ ^）
                is_all_exact = all(not any(c in s for c in "><~^") for s in unique_specs if s != "*")
                
                if is_all_exact:
                    conflicts.append({
                        "library": lib_name,
                        "constraints": list(unique_specs),
                        "reason": "Multiple exact versions specified"
                    })
                else:
                    # 混合了范围，取最长/最复杂的作为建议（权宜之计）
                    suggestions[lib_name] = max(unique_specs, key=len)
            elif unique_specs:
                suggestions[lib_name] = list(unique_specs)[0]
                
        return conflicts, suggestions
