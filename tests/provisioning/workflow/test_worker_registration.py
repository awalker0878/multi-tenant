"""Deterministic regressions for the disposable engine gate's routing boundary."""
from __future__ import annotations

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from temporalio.api.workflowservice.v1 import DescribeWorkerDeploymentResponse
from temporalio.service import RPCError, RPCStatusCode

from tests.provisioning.workflow import worker_version_gate as gate


DEPLOYMENT = 'test-mobility'
BUILD = 'a' * 40
OTHER_BUILD = 'b' * 40


def description(*versions: tuple[str, str], token: bytes = b'token'):
    """Use the SDK's real protobuf messages, not an invented service shape."""
    response = DescribeWorkerDeploymentResponse(conflict_token=token)
    for deployment, build in versions:
        version = response.worker_deployment_info.version_summaries.add()
        version.deployment_version.deployment_name = deployment
        version.deployment_version.build_id = build
    return response


class WorkerRegistrationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.service = SimpleNamespace(
            describe_worker_deployment=AsyncMock(),
            set_worker_deployment_current_version=AsyncMock())
        self.client = SimpleNamespace(
            namespace='test-only',
            service_client=SimpleNamespace(workflow_service=self.service))
        self.sleep = AsyncMock()
        self.patch_sleep = patch.object(gate.asyncio, 'sleep', self.sleep)
        self.patch_sleep.start()
        self.addCleanup(self.patch_sleep.stop)

    async def test_existing_deployment_waits_for_new_version(self):
        self.service.describe_worker_deployment.side_effect = [
            description((DEPLOYMENT, OTHER_BUILD), token=b'old-token'),
            description((DEPLOYMENT, OTHER_BUILD), (DEPLOYMENT, BUILD), token=b'new-token')]
        await gate._set_current(self.client, DEPLOYMENT, BUILD)
        self.assertEqual(self.service.describe_worker_deployment.await_count, 2)
        self.sleep.assert_awaited_once_with(1)
        self.service.set_worker_deployment_current_version.assert_awaited_once()
        request = self.service.set_worker_deployment_current_version.await_args.args[0]
        self.assertEqual((request.namespace, request.deployment_name, request.build_id,
                          request.conflict_token),
                         ('test-only', DEPLOYMENT, BUILD, b'new-token'))

    async def test_never_activates_absent_or_foreign_versions(self):
        for versions in ((), ((DEPLOYMENT, OTHER_BUILD),), (('other-deployment', BUILD),)):
            with self.subTest(versions=versions):
                self.service.describe_worker_deployment.reset_mock()
                self.sleep.reset_mock()
                self.service.describe_worker_deployment.return_value = description(*versions)
                with self.assertRaisesRegex(RuntimeError, 'failed to register or activate'):
                    await gate._set_current(self.client, DEPLOYMENT, BUILD)
                self.assertEqual(self.service.describe_worker_deployment.await_count, 30)
                self.assertEqual(self.sleep.await_count, 29)
                self.service.set_worker_deployment_current_version.assert_not_awaited()

    async def test_missing_deployment_can_register_later(self):
        self.service.describe_worker_deployment.side_effect = [
            RPCError('pending', RPCStatusCode.NOT_FOUND, b''),
            description((DEPLOYMENT, BUILD))]
        await gate._set_current(self.client, DEPLOYMENT, BUILD)
        self.sleep.assert_awaited_once_with(1)
        self.service.set_worker_deployment_current_version.assert_awaited_once()

    async def test_precondition_retry_refreshes_conflict_token(self):
        self.service.describe_worker_deployment.side_effect = [
            description((DEPLOYMENT, BUILD), token=b'before'),
            description((DEPLOYMENT, BUILD), token=b'after')]
        self.service.set_worker_deployment_current_version.side_effect = [
            RPCError('routing changed', RPCStatusCode.FAILED_PRECONDITION, b''), None]
        await gate._set_current(self.client, DEPLOYMENT, BUILD)
        tokens = [call.args[0].conflict_token for call in
                  self.service.set_worker_deployment_current_version.await_args_list]
        self.assertEqual(tokens, [b'before', b'after'])

    async def test_permanent_errors_fail_without_retry(self):
        for method in ('describe_worker_deployment', 'set_worker_deployment_current_version'):
            for status in (RPCStatusCode.PERMISSION_DENIED, RPCStatusCode.UNAUTHENTICATED,
                           RPCStatusCode.INVALID_ARGUMENT):
                with self.subTest(method=method, status=status):
                    self.service.describe_worker_deployment.reset_mock(side_effect=True)
                    self.service.set_worker_deployment_current_version.reset_mock(side_effect=True)
                    self.sleep.reset_mock()
                    self.service.describe_worker_deployment.return_value = description((DEPLOYMENT, BUILD))
                    error = RPCError('refused', status, b'')
                    getattr(self.service, method).side_effect = error
                    with self.assertRaises(RPCError) as caught:
                        await gate._set_current(self.client, DEPLOYMENT, BUILD)
                    self.assertIs(caught.exception, error)
                    self.assertEqual(getattr(self.service, method).await_count, 1)
                    self.sleep.assert_not_awaited()

    async def test_unexpected_error_is_not_masked_as_pending_registration(self):
        self.service.describe_worker_deployment.side_effect = ValueError('invalid response')
        with self.assertRaisesRegex(ValueError, 'invalid response'):
            await gate._set_current(self.client, DEPLOYMENT, BUILD)
        self.sleep.assert_not_awaited()
        self.service.set_worker_deployment_current_version.assert_not_awaited()

    async def test_stalled_rpc_has_a_deadline_and_no_activation(self):
        async def stall(_request):
            await asyncio.Event().wait()
        self.service.describe_worker_deployment.side_effect = stall
        with patch.object(gate, '_RPC_TIMEOUT_SECONDS', 0.01):
            with self.assertRaises(TimeoutError):
                await gate._set_current(self.client, DEPLOYMENT, BUILD)
        self.sleep.assert_not_awaited()
        self.service.set_worker_deployment_current_version.assert_not_awaited()

    async def test_cancellation_is_not_retried(self):
        self.service.describe_worker_deployment.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await gate._set_current(self.client, DEPLOYMENT, BUILD)
        self.sleep.assert_not_awaited()
        self.service.set_worker_deployment_current_version.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
