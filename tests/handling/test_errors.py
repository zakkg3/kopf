import asyncio
import logging

import pytest

import kopf
from kopf.reactor.causation import Reason, HANDLER_REASONS
from kopf.reactor.handling import PermanentError, TemporaryError
from kopf.reactor.handling import resource_handler
from kopf.structs.containers import ResourceMemories
from kopf.structs.primitives import Toggle


# The extrahandlers are needed to prevent the cycle ending and status purging.
@pytest.mark.parametrize('cause_type', HANDLER_REASONS)
async def test_fatal_error_stops_handler(
        registry, handlers, extrahandlers, resource, cause_mock, cause_type,
        caplog, assert_logs, k8s_mocked):
    caplog.set_level(logging.DEBUG)
    name1 = f'{cause_type}_fn'

    event_type = None if cause_type == Reason.RESUME else 'irrelevant'
    cause_mock.reason = cause_type
    handlers.create_mock.side_effect = PermanentError("oops")
    handlers.update_mock.side_effect = PermanentError("oops")
    handlers.delete_mock.side_effect = PermanentError("oops")
    handlers.resume_mock.side_effect = PermanentError("oops")

    await resource_handler(
        lifecycle=kopf.lifecycles.one_by_one,
        registry=registry,
        resource=resource,
        memories=ResourceMemories(),
        event={'type': event_type, 'object': cause_mock.body},
        freeze_mode=Toggle(),
        replenished=asyncio.Event(),
        event_queue=asyncio.Queue(),
    )

    assert handlers.create_mock.call_count == (1 if cause_type == Reason.CREATE else 0)
    assert handlers.update_mock.call_count == (1 if cause_type == Reason.UPDATE else 0)
    assert handlers.delete_mock.call_count == (1 if cause_type == Reason.DELETE else 0)
    assert handlers.resume_mock.call_count == (1 if cause_type == Reason.RESUME else 0)

    assert not k8s_mocked.sleep_or_wait.called
    assert k8s_mocked.patch_obj.called

    patch = k8s_mocked.patch_obj.call_args_list[0][1]['patch']
    assert patch['status']['kopf']['progress'] is not None
    assert patch['status']['kopf']['progress'][name1]['failure'] is True
    assert patch['status']['kopf']['progress'][name1]['message'] == 'oops'

    assert_logs([
        "Handler .+ failed permanently: oops",
    ])


# The extrahandlers are needed to prevent the cycle ending and status purging.
@pytest.mark.parametrize('cause_type', HANDLER_REASONS)
async def test_retry_error_delays_handler(
        registry, handlers, extrahandlers, resource, cause_mock, cause_type,
        caplog, assert_logs, k8s_mocked):
    caplog.set_level(logging.DEBUG)
    name1 = f'{cause_type}_fn'

    event_type = None if cause_type == Reason.RESUME else 'irrelevant'
    cause_mock.reason = cause_type
    handlers.create_mock.side_effect = TemporaryError("oops")
    handlers.update_mock.side_effect = TemporaryError("oops")
    handlers.delete_mock.side_effect = TemporaryError("oops")
    handlers.resume_mock.side_effect = TemporaryError("oops")

    await resource_handler(
        lifecycle=kopf.lifecycles.one_by_one,
        registry=registry,
        resource=resource,
        memories=ResourceMemories(),
        event={'type': event_type, 'object': cause_mock.body},
        freeze_mode=Toggle(),
        replenished=asyncio.Event(),
        event_queue=asyncio.Queue(),
    )

    assert handlers.create_mock.call_count == (1 if cause_type == Reason.CREATE else 0)
    assert handlers.update_mock.call_count == (1 if cause_type == Reason.UPDATE else 0)
    assert handlers.delete_mock.call_count == (1 if cause_type == Reason.DELETE else 0)
    assert handlers.resume_mock.call_count == (1 if cause_type == Reason.RESUME else 0)

    assert not k8s_mocked.sleep_or_wait.called
    assert k8s_mocked.patch_obj.called

    patch = k8s_mocked.patch_obj.call_args_list[0][1]['patch']
    assert patch['status']['kopf']['progress'] is not None
    assert patch['status']['kopf']['progress'][name1]['failure'] is False
    assert patch['status']['kopf']['progress'][name1]['success'] is False
    assert patch['status']['kopf']['progress'][name1]['delayed']

    assert_logs([
        "Handler .+ failed temporarily: oops",
    ])


# The extrahandlers are needed to prevent the cycle ending and status purging.
@pytest.mark.parametrize('cause_type', HANDLER_REASONS)
async def test_arbitrary_error_delays_handler(
        registry, handlers, extrahandlers, resource, cause_mock, cause_type,
        caplog, assert_logs, k8s_mocked):
    caplog.set_level(logging.DEBUG)
    name1 = f'{cause_type}_fn'

    event_type = None if cause_type == Reason.RESUME else 'irrelevant'
    cause_mock.reason = cause_type
    handlers.create_mock.side_effect = Exception("oops")
    handlers.update_mock.side_effect = Exception("oops")
    handlers.delete_mock.side_effect = Exception("oops")
    handlers.resume_mock.side_effect = Exception("oops")

    await resource_handler(
        lifecycle=kopf.lifecycles.one_by_one,
        registry=registry,
        resource=resource,
        memories=ResourceMemories(),
        event={'type': event_type, 'object': cause_mock.body},
        freeze_mode=Toggle(),
        replenished=asyncio.Event(),
        event_queue=asyncio.Queue(),
    )

    assert handlers.create_mock.call_count == (1 if cause_type == Reason.CREATE else 0)
    assert handlers.update_mock.call_count == (1 if cause_type == Reason.UPDATE else 0)
    assert handlers.delete_mock.call_count == (1 if cause_type == Reason.DELETE else 0)
    assert handlers.resume_mock.call_count == (1 if cause_type == Reason.RESUME else 0)

    assert not k8s_mocked.sleep_or_wait.called
    assert k8s_mocked.patch_obj.called

    patch = k8s_mocked.patch_obj.call_args_list[0][1]['patch']
    assert patch['status']['kopf']['progress'] is not None
    assert patch['status']['kopf']['progress'][name1]['failure'] is False
    assert patch['status']['kopf']['progress'][name1]['success'] is False
    assert patch['status']['kopf']['progress'][name1]['delayed']

    assert_logs([
        "Handler .+ failed with an exception. Will retry.",
    ])
