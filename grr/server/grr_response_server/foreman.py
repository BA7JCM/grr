#!/usr/bin/env python
"""The GRR Foreman."""

import logging

from grr_response_core.lib import rdfvalue
from grr_response_server import data_store
from grr_response_server import flow
from grr_response_server import hunt
from grr_response_server import message_handlers
from grr_response_server import mig_foreman_rules
from grr_response_server.databases import db
from grr_response_server.rdfvalues import mig_objects


class Error(Exception):
  pass


class UnknownHuntTypeError(Error):
  pass


# TODO(amoser): Now that Foreman rules are directly stored in the db,
# consider removing this class altogether once the AFF4 Foreman has
# been removed.
class Foreman(object):
  """The foreman starts flows for clients depending on rules."""

  def _CheckIfHuntTaskWasAssigned(self, client_id, hunt_id):
    """Will return True if hunt's task was assigned to this client before."""
    flow_id = hunt_id
    try:
      cur_flow = data_store.REL_DB.ReadFlowObject(client_id, flow_id)
    except db.UnknownFlowError:
      return False

    if cur_flow.parent_hunt_id != hunt_id:
      raise RuntimeError(
          "Cannot start Hunt {} on {} because unrelated {} already exists."
          .format(hunt_id, client_id, cur_flow.long_flow_id)
      )

    return True

  def _RunAction(self, rule, client_id):
    """Run all the actions specified in the rule.

    Args:
      rule: Rule which actions are to be executed.
      client_id: Id of a client where rule's actions are to be executed.

    Returns:
      Number of actions started.
    """
    actions_count = 0

    try:
      if self._CheckIfHuntTaskWasAssigned(client_id, rule.hunt_id):
        raise flow.CanNotStartFlowWithExistingIdError(client_id, rule.hunt_id)

      hunt.StartHuntFlowOnClient(client_id, rule.hunt_id)
      logging.info(
          "Foreman: Started hunt %s on client %s.", rule.hunt_id, client_id
      )
      actions_count += 1

    except flow.CanNotStartFlowWithExistingIdError:
      logging.info(
          "Foreman: ignoring hunt %s on client %s: was started here before",
          rule.hunt_id,
          client_id,
      )

    # There could be all kinds of errors we don't know about when starting the
    # hunt so we catch everything here.
    except Exception as e:  # pylint: disable=broad-except
      logging.exception(
          "Failure running hunt %s on client %s: %s", rule.hunt_id, client_id, e
      )

    return actions_count

  def _GetLastForemanRunTime(self, client_id):
    md = data_store.REL_DB.ReadClientMetadata(client_id)
    return rdfvalue.RDFDatetime(md.last_foreman_time)

  def _SetLastForemanRunTime(self, client_id, latest_rule):
    data_store.REL_DB.WriteClientMetadata(client_id, last_foreman=latest_rule)

  def AssignTasksToClient(self, client_id):
    """Examines our rules and starts up flows based on the client.

    Args:
      client_id: Client id of the client for tasks to be assigned.

    Returns:
      Number of assigned tasks.
    """
    proto_rules = data_store.REL_DB.ReadAllForemanRules()
    rules = [
        mig_foreman_rules.ToRDFForemanCondition(cond) for cond in proto_rules
    ]
    if not rules:
      return 0

    last_foreman_run = self._GetLastForemanRunTime(client_id)

    latest_rule_creation_time = max(rule.creation_time for rule in rules)

    if latest_rule_creation_time > last_foreman_run:
      # Update the latest checked rule on the client.
      self._SetLastForemanRunTime(client_id, latest_rule_creation_time)

    relevant_rules = []
    expired_rules = []

    now = rdfvalue.RDFDatetime.Now()

    for rule in rules:
      if rule.expiration_time < now:
        expired_rules.append(rule)
      elif rule.creation_time > last_foreman_run:
        relevant_rules.append(rule)

    actions_count = 0
    if relevant_rules:
      client_data = data_store.REL_DB.ReadClientFullInfo(client_id)
      if client_data is None:
        return

      client_data = mig_objects.ToRDFClientFullInfo(client_data)
      for rule in relevant_rules:
        if rule.Evaluate(client_data):
          actions_count += self._RunAction(rule, client_id)

    if expired_rules:
      for rule in expired_rules:
        hunt.CompleteHuntIfExpirationTimeReached(rule.hunt_id)
      data_store.REL_DB.RemoveExpiredForemanRules()

    return actions_count


class ForemanMessageHandler(message_handlers.MessageHandler):
  """A handler for Foreman messages."""

  handler_name = "ForemanHandler"

  def ProcessMessages(self, msgs):
    # TODO(amoser): The foreman reads the rules from the database for each
    # client. In the old implementation we used to have a cache. If this is a
    # performance hit, lets consider putting the cache back.

    foreman_obj = Foreman()
    for msg in msgs:
      foreman_obj.AssignTasksToClient(msg.client_id)
