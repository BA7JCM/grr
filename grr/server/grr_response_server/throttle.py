#!/usr/bin/env python
"""Throttle user calls to flows."""

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import flows as rdf_flows
from grr_response_server import data_store
from grr_response_server.rdfvalues import mig_flow_objects


class Error(Exception):
  """Base error class."""


class DailyFlowRequestLimitExceededError(Error):
  """Too many flows run by a user on a client."""


class DuplicateFlowError(Error):
  """The same exact flow has run recently on this client."""

  def __init__(self, message, flow_id):
    super().__init__(message)

    if not flow_id:
      raise ValueError("flow_id has to be specified.")
    self.flow_id = flow_id


class FlowThrottler(object):
  """Checks for excessive or repetitive flow requests."""

  def __init__(self, daily_req_limit=0, dup_interval=rdfvalue.Duration(0)):
    """Create flow throttler object.

    Args:
      daily_req_limit: Number of flows allow per user per client. Integer.
      dup_interval: rdfvalue.Duration time during which duplicate flows will be
        blocked.
    """
    self.daily_req_limit = daily_req_limit
    self.dup_interval = dup_interval

  def _LoadFlows(self, client_id, min_create_time):
    """Yields all flows for the given client_id and time range.

    Args:
      client_id: Client id string.
      min_create_time: minimum creation time (inclusive)

    Yields: flow_objects.Flow objects
    """
    flow_list = data_store.REL_DB.ReadAllFlowObjects(
        client_id=client_id,
        min_create_time=min_create_time,
        include_child_flows=False,
    )
    flow_list = [mig_flow_objects.ToRDFFlow(flow) for flow in flow_list]
    for flow_obj in flow_list:
      yield flow_obj

  def EnforceLimits(self, client_id, user, flow_name, flow_args=None):
    """Enforce DailyFlowRequestLimit and FlowDuplicateInterval.

    Look at the flows that have run on this client recently and check
    we aren't exceeding our limits. Raises if limits will be exceeded by running
    the specified flow.

    Args:
      client_id: client URN
      user: username string
      flow_name: name of the Flow. Only used for FlowDuplicateInterval.
      flow_args: flow args rdfvalue for the flow being launched

    Raises:
      DailyFlowRequestLimitExceededError: if the user has already run
        API.DailyFlowRequestLimit on this client in the previous 24h.
      DuplicateFlowError: an identical flow was run on this machine by a user
        within the API.FlowDuplicateInterval
    """
    if not self.dup_interval and not self.daily_req_limit:
      return

    now = rdfvalue.RDFDatetime.Now()
    yesterday = now - rdfvalue.Duration.From(1, rdfvalue.DAYS)
    dup_boundary = now - self.dup_interval
    min_create_time = min(yesterday, dup_boundary)

    flow_count = 0
    flow_objs = self._LoadFlows(client_id, min_create_time)

    if flow_args is None:
      flow_args = rdf_flows.EmptyFlowArgs()

    for flow_obj in flow_objs:
      if (
          flow_obj.create_time > dup_boundary
          and flow_obj.flow_class_name == flow_name
          and flow_obj.args == flow_args
      ):
        raise DuplicateFlowError(
            "Identical %s already run on %s at %s"
            % (flow_name, client_id, flow_obj.create_time),
            flow_id=flow_obj.flow_id,
        )

      # Filter for flows started by user within the 1 day window.
      if flow_obj.creator == user and flow_obj.create_time > yesterday:
        flow_count += 1

    # If limit is set, enforce it.
    if self.daily_req_limit and flow_count >= self.daily_req_limit:
      raise DailyFlowRequestLimitExceededError(
          "%s flows run since %s, limit: %s"
          % (flow_count, yesterday, self.daily_req_limit)
      )
