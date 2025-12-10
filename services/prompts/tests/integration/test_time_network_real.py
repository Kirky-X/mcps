import time
from datetime import datetime, timezone

import prompt_manager.infrastructure.time_network as tn


def test_real_connectivity_and_offset():
    online = tn.check_connectivity()
    if online:
        off = tn.refresh_time_offset()
        assert off is not None
        now = tn.get_precise_time()
        assert now.tzinfo == timezone.utc
    else:
        off = tn.refresh_time_offset()
        assert off is None


def test_background_monitor_real():
    tn.start_background_monitor(interval_seconds=1)
    time.sleep(2)
    now = tn.get_precise_time()
    assert isinstance(now, datetime)
    assert now.tzinfo == timezone.utc
    tn.stop_background_monitor()

