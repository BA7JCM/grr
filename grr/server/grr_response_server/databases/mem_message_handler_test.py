#!/usr/bin/env python
from absl import app
from absl.testing import absltest

from grr_response_server.databases import db_message_handler_test
from grr_response_server.databases import mem_test_base
from grr.test_lib import test_lib


class MemoryDBHandlerTest(
    db_message_handler_test.DatabaseTestHandlerMixin,
    mem_test_base.MemoryDBTestBase,
    absltest.TestCase,
):
  pass


if __name__ == "__main__":
  app.run(test_lib.main)
