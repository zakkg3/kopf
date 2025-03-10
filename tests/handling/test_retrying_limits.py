import asyncio
import logging

import freezegun
import pytest

import kopf
from kopf.reactor.causation import HANDLER_REASONS, Reason
from kopf.reactor.handling import resource_handler
from kopf.structs.containers import ResourceMemories
from kopf.structs.primitives import Toggle


# The timeout is hard-coded in conftest.py:handlers().
# The extrahandlers are needed to prevent the cycle ending and status purging.
@pytest.mark.parametrize('cause_type', HANDLER_REASONS)
@pytest.mark.parametrize('now, ts', [
    ['2099-12-31T23:59:59', '2020-01-01T00:00:00'],
], ids=['slow'])
async def test_timed_out_handler_fails(
        registry, handlers, extrahandlers, resource, cause_mock, cause_type,
        caplog, assert_logs, k8s_mocked, now, ts):
    caplog.set_level(logging.DEBUG)
    name1 = f'{cause_type}_fn'

    event_type = None if cause_type == Reason.RESUME else 'irrelevant'
    cause_mock.reason = cause_type
    cause_mock.body.update({
        'status': {'kopf': {'progress': {
            'create_fn': {'started': ts},
            'update_fn': {'started': ts},
            'delete_fn': {'started': ts},
            'resume_fn': {'started': ts},
        }}}
    })

    with freezegun.freeze_time(now):
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

    assert not handlers.create_mock.called
    assert not handlers.update_mock.called
    assert not handlers.delete_mock.called
    assert not handlers.resume_mock.called

    # Progress is reset, as the handler is not going to retry.
    assert not k8s_mocked.sleep_or_wait.called
    assert k8s_mocked.patch_obj.called

    patch = k8s_mocked.patch_obj.call_args_list[0][1]['patch']
    assert patch['status']['kopf']['progress'] is not None
    assert patch['status']['kopf']['progress'][name1]['failure'] is True

    assert_logs([
        "Handler .+ has timed out after",
    ])


# The limits are hard-coded in conftest.py:handlers().
# The extrahandlers are needed to prevent the cycle ending and status purging.
@pytest.mark.parametrize('cause_type', HANDLER_REASONS)
async def test_retries_limited_handler_fails(
        registry, handlers, extrahandlers, resource, cause_mock, cause_type,
        caplog, assert_logs, k8s_mocked):
    caplog.set_level(logging.DEBUG)
    name1 = f'{cause_type}_fn'

    event_type = None if cause_type == Reason.RESUME else 'irrelevant'
    cause_mock.reason = cause_type
    cause_mock.body.update({
        'status': {'kopf': {'progress': {
            'create_fn': {'retries': 100},
            'update_fn': {'retries': 100},
            'delete_fn': {'retries': 100},
            'resume_fn': {'retries': 100},
        }}}
    })

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

    assert not handlers.create_mock.called
    assert not handlers.update_mock.called
    assert not handlers.delete_mock.called
    assert not handlers.resume_mock.called

    # Progress is reset, as the handler is not going to retry.
    assert not k8s_mocked.sleep_or_wait.called
    assert k8s_mocked.patch_obj.called

    patch = k8s_mocked.patch_obj.call_args_list[0][1]['patch']
    assert patch['status']['kopf']['progress'] is not None
    assert patch['status']['kopf']['progress'][name1]['failure'] is True

    assert_logs([
        r"Handler .+ has exceeded \d+ retries",
    ])
