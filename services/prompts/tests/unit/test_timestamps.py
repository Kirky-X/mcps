from datetime import timezone

from prompt_manager.infrastructure.time_network import get_precise_time
from prompt_manager.models.orm import Prompt, PromptVersion, Tag, PrinciplePrompt


def _is_close(a, b, seconds=2.0):
    return abs((a - b).total_seconds()) <= seconds


def test_prompt_timestamps_use_time_manager():
    now = get_precise_time()
    p = Prompt(name="ts_test")
    assert p.created_at.tzinfo == timezone.utc
    assert p.updated_at.tzinfo == timezone.utc
    assert _is_close(p.created_at, now)
    assert _is_close(p.updated_at, now)


def test_prompt_version_timestamp_use_time_manager():
    now = get_precise_time()
    v = PromptVersion(prompt_id="pid", version="1.0", description="d")
    assert v.created_at.tzinfo == timezone.utc
    assert _is_close(v.created_at, now)


def test_tag_timestamp_use_time_manager():
    now = get_precise_time()
    t = Tag(name="ts_tag")
    assert t.created_at.tzinfo == timezone.utc
    assert _is_close(t.created_at, now)


def test_principle_prompt_timestamp_use_time_manager():
    now = get_precise_time()
    pr = PrinciplePrompt(name="p", version="1.0", content="c")
    assert pr.created_at.tzinfo == timezone.utc
    assert _is_close(pr.created_at, now)

