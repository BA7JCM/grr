#!/usr/bin/env python
"""Test for the foreman client rule classes."""

from absl import app

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import test_base as rdf_test_base
from grr_response_server import data_store
from grr_response_server import foreman_rules
from grr_response_server.rdfvalues import mig_objects
from grr.test_lib import test_lib


class ForemanClientRuleSetTest(
    rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest
):
  rdfvalue_class = foreman_rules.ForemanClientRuleSet

  def CheckRDFValue(self, value, sample):
    # TODO: Accessing a repeated field changes the structs value.
    # Until this major deficiency in RDFValues is fixed, access `rules` to
    # prevent failure due to [] != None. Side effects... (ノಠ益ಠ)ノ彡┻━┻
    value.rules  # pylint: disable=pointless-statement
    sample.rules  # pylint: disable=pointless-statement
    super().CheckRDFValue(value, sample)

  def GenerateSample(self, number=0):
    ret = foreman_rules.ForemanClientRuleSet()

    # Use the number's least significant bit to assign a match mode
    if number % 1:
      ret.match_mode = foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ALL
    else:
      ret.match_mode = foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ANY

    # Generate a sequence of rules using all other bits
    ret.rules = [
        ForemanClientRuleTest.GenerateSample(n) for n in range(number // 2)
    ]

    return ret

  def testEvaluatesPositiveInMatchAnyModeIfOneRuleMatches(self):
    # Instantiate a rule set that matches if any of its two
    # operating system rules matches
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False
                ),
            ),
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True
                ),
            ),
        ],
    )

    client_id_dar = self.SetupClient(0, system="Darwin")
    # One of the set's rules has os_darwin=True, so the whole set matches
    # with the match any match mode
    self.assertTrue(
        rs.Evaluate(
            mig_objects.ToRDFClientFullInfo(
                data_store.REL_DB.ReadClientFullInfo(client_id_dar)
            )
        )
    )

  def testEvaluatesNegativeInMatchAnyModeIfNoRuleMatches(self):
    # Instantiate a rule set that matches if any of its two
    # operating system rules matches
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False
                ),
            ),
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True
                ),
            ),
        ],
    )

    client_id_win = self.SetupClient(0, system="Windows")
    # None of the set's rules has os_windows=True, so the whole set doesn't
    # match
    self.assertFalse(
        rs.Evaluate(
            mig_objects.ToRDFClientFullInfo(
                data_store.REL_DB.ReadClientFullInfo(client_id_win)
            )
        )
    )

  def testEvaluatesNegativeInMatchAllModeIfOnlyOneRuleMatches(self):
    # Instantiate a rule set that matches if all of its two
    # operating system rules match
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False
                ),
            ),
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True
                ),
            ),
        ],
    )

    client_id_dar = self.SetupClient(0, system="Darwin")
    # One of the set's rules has os_darwin=False, so the whole set doesn't
    # match with the match all match mode
    self.assertFalse(
        rs.Evaluate(
            mig_objects.ToRDFClientFullInfo(
                data_store.REL_DB.ReadClientFullInfo(client_id_dar)
            )
        )
    )

  def testEvaluatesPositiveInMatchAllModeIfAllRuleMatch(self):
    # Instantiate a rule set that matches if all of its two
    # operating system rules match
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=False
                ),
            ),
            foreman_rules.ForemanClientRule(
                rule_type=foreman_rules.ForemanClientRule.Type.OS,
                os=foreman_rules.ForemanOsClientRule(
                    os_windows=False, os_linux=True, os_darwin=True
                ),
            ),
        ],
    )

    client_id_lin = self.SetupClient(0, system="Linux")
    # All of the set's rules have os_linux=False, so the whole set matches
    self.assertTrue(
        rs.Evaluate(
            mig_objects.ToRDFClientFullInfo(
                data_store.REL_DB.ReadClientFullInfo(client_id_lin)
            )
        )
    )

  def testEvaluatesNegativeInMatchAnyModeWithNoRules(self):
    # Instantiate an empty rule set that matches if any of its rules matches
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ANY,
        rules=[],
    )

    client_id_lin = self.SetupClient(0, system="Linux")
    # None of the set's rules has os_linux=True, so the set doesn't match
    self.assertFalse(
        rs.Evaluate(
            mig_objects.ToRDFClientFullInfo(
                data_store.REL_DB.ReadClientFullInfo(client_id_lin)
            )
        )
    )

  def testEvaluatesPositiveInMatchAllModeWithNoRules(self):
    # Instantiate an empty rule set that matches if all of its rules match
    rs = foreman_rules.ForemanClientRuleSet(
        match_mode=foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ALL,
        rules=[],
    )

    client_id_lin = self.SetupClient(0, system="Linux")
    # All of the set's rules have os_linux=True, so the set matches
    self.assertTrue(
        rs.Evaluate(
            mig_objects.ToRDFClientFullInfo(
                data_store.REL_DB.ReadClientFullInfo(client_id_lin)
            )
        )
    )

  def testFromDictEmpty(self):
    dct = {
        "match_mode": "MATCH_ALL",
        "rules": [],
    }

    rdf = foreman_rules.ForemanClientRuleSet()
    rdf.FromDict(dct)

    self.assertEqual(
        rdf.match_mode, foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ALL
    )
    self.assertEmpty(rdf.rules)

  def testFromDictMixedRules(self):
    dct = {
        "match_mode": "MATCH_ANY",
        "rules": [
            {
                "rule_type": "OS",
                "os": {
                    "os_windows": True,
                    "os_linux": True,
                },
            },
            {
                "rule_type": "LABEL",
                "label": {
                    "label_names": ["foo", "bar"],
                    "match_mode": "MATCH_ALL",
                },
            },
        ],
    }

    rdf = foreman_rules.ForemanClientRuleSet()
    rdf.FromDict(dct)

    self.assertEqual(
        rdf.match_mode, foreman_rules.ForemanClientRuleSet.MatchMode.MATCH_ANY
    )
    self.assertLen(rdf.rules, 2)

    self.assertEqual(
        rdf.rules[0].rule_type, foreman_rules.ForemanClientRule.Type.OS
    )
    self.assertTrue(rdf.rules[0].os.os_windows)
    self.assertTrue(rdf.rules[0].os.os_linux)
    self.assertFalse(rdf.rules[0].os.os_darwin)

    self.assertEqual(
        rdf.rules[1].rule_type, foreman_rules.ForemanClientRule.Type.LABEL
    )
    self.assertEqual(rdf.rules[1].label.label_names, ["foo", "bar"])
    self.assertEqual(
        rdf.rules[1].label.match_mode,
        foreman_rules.ForemanLabelClientRule.MatchMode.MATCH_ALL,
    )


class ForemanClientRuleTest(
    rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest
):
  rdfvalue_class = foreman_rules.ForemanClientRule

  @staticmethod
  def GenerateSample(number=0):
    # Wrap the operating system rule sample generator
    return foreman_rules.ForemanClientRule(
        rule_type=foreman_rules.ForemanClientRule.Type.OS,
        os=ForemanOsClientRuleTest.GenerateSample(number),
    )

  def testEvaluatesPositiveIfNestedRuleEvaluatesPositive(self):
    r = foreman_rules.ForemanClientRule(
        rule_type=foreman_rules.ForemanClientRule.Type.OS,
        os=foreman_rules.ForemanOsClientRule(
            os_windows=True, os_linux=True, os_darwin=False
        ),
    )

    client_id_win = self.SetupClient(0, system="Windows")
    # The Windows client matches rule r
    self.assertTrue(
        r.Evaluate(
            mig_objects.ToRDFClientFullInfo(
                data_store.REL_DB.ReadClientFullInfo(client_id_win)
            )
        )
    )

  def testEvaluatesNegativeIfNestedRuleEvaluatesNegative(self):
    r = foreman_rules.ForemanClientRule(
        rule_type=foreman_rules.ForemanClientRule.Type.OS,
        os=foreman_rules.ForemanOsClientRule(
            os_windows=False, os_linux=True, os_darwin=False
        ),
    )

    client_id_win = self.SetupClient(0, system="Windows")
    # The Windows client doesn't match rule r
    self.assertFalse(
        r.Evaluate(
            mig_objects.ToRDFClientFullInfo(
                data_store.REL_DB.ReadClientFullInfo(client_id_win)
            )
        )
    )

  def testFromDictOs(self):
    dct = {
        "rule_type": "OS",
        "os": {
            "os_windows": False,
            "os_linux": True,
        },
    }

    rdf = foreman_rules.ForemanClientRule()
    rdf.FromDict(dct)

    self.assertEqual(rdf.rule_type, foreman_rules.ForemanClientRule.Type.OS)
    self.assertFalse(rdf.os.os_windows)
    self.assertTrue(rdf.os.os_linux)

  def testFromDictLabel(self):
    dct = {
        "rule_type": "LABEL",
        "label": {
            "label_names": ["quux", "norf", "thud"],
            "match_mode": "MATCH_ANY",
        },
    }

    rdf = foreman_rules.ForemanClientRule()
    rdf.FromDict(dct)

    self.assertEqual(rdf.rule_type, foreman_rules.ForemanClientRule.Type.LABEL)
    self.assertEqual(rdf.label.label_names, ["quux", "norf", "thud"])
    self.assertEqual(
        rdf.label.match_mode,
        foreman_rules.ForemanLabelClientRule.MatchMode.MATCH_ANY,
    )

  def testFromDictRegex(self):
    dct = {
        "rule_type": "REGEX",
        "regex": {
            "attribute_regex": "[a-z]+[0-9]",
            "field": "FQDN",
        },
    }

    rdf = foreman_rules.ForemanClientRule()
    rdf.FromDict(dct)

    self.assertEqual(rdf.rule_type, foreman_rules.ForemanClientRule.Type.REGEX)
    self.assertEqual(rdf.regex.attribute_regex, "[a-z]+[0-9]")
    self.assertEqual(
        rdf.regex.field,
        foreman_rules.ForemanRegexClientRule.ForemanStringField.FQDN,
    )

  def testFromDictInteger(self):
    dct = {
        "rule_type": "INTEGER",
        "integer": {
            "operator": "EQUAL",
            "value": 42,
            "field": "CLIENT_VERSION",
        },
    }

    rdf = foreman_rules.ForemanClientRule()
    rdf.FromDict(dct)

    self.assertEqual(
        rdf.rule_type, foreman_rules.ForemanClientRule.Type.INTEGER
    )
    self.assertEqual(
        rdf.integer.operator,
        foreman_rules.ForemanIntegerClientRule.Operator.EQUAL,
    )
    self.assertEqual(rdf.integer.value, 42)
    self.assertEqual(
        rdf.integer.field,
        foreman_rules.ForemanIntegerClientRule.ForemanIntegerField.CLIENT_VERSION,
    )


class ForemanOsClientRuleTest(test_lib.GRRBaseTest):

  @staticmethod
  def GenerateSample(number=0):
    # Assert that the argument uses at most the three least significant bits
    num_combinations = 2**3
    if number < 0 or number >= num_combinations:
      raise ValueError(
          "Only %d distinct instances of %s exist, numbered from 0 to %d."
          % (
              num_combinations,
              foreman_rules.ForemanOsClientRule.__name__,
              num_combinations - 1,
          )
      )

    # Assign the bits to new rule's boolean fields accordingly
    return foreman_rules.ForemanOsClientRule(
        os_windows=number & 1, os_linux=number & 2, os_darwin=number & 4
    )

  def testWindowsClientDoesNotMatchRuleWithNoOsSelected(self):
    r = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False
    )

    client_id = self.SetupClient(0, system="Windows")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)
    self.assertFalse(r.Evaluate(info))

  def testLinuxClientMatchesIffOsLinuxIsSelected(self):
    r0 = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=False, os_darwin=False
    )

    r1 = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False
    )

    client_id = self.SetupClient(0, system="Linux")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)
    self.assertFalse(r0.Evaluate(info))
    self.assertTrue(r1.Evaluate(info))

  def testDarwinClientMatchesIffOsDarwinIsSelected(self):
    r0 = foreman_rules.ForemanOsClientRule(
        os_windows=False, os_linux=True, os_darwin=False
    )

    r1 = foreman_rules.ForemanOsClientRule(
        os_windows=True, os_linux=False, os_darwin=True
    )

    client_id = self.SetupClient(0, system="Darwin")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)
    self.assertFalse(r0.Evaluate(info))
    self.assertTrue(r1.Evaluate(info))


class ForemanLabelClientRuleTest(
    rdf_test_base.RDFValueTestMixin, test_lib.GRRBaseTest
):
  rdfvalue_class = foreman_rules.ForemanLabelClientRule

  def GenerateSample(self, number=0):
    # Sample rule matches clients labeled str(number)
    return foreman_rules.ForemanLabelClientRule(label_names=[str(number)])

  def _Evaluate(self, rule):
    client_id = self.SetupClient(0)

    data_store.REL_DB.WriteGRRUser("GRR")
    data_store.REL_DB.AddClientLabels(client_id, "GRR", ["hello", "world"])

    client_info = data_store.REL_DB.ReadClientFullInfo(client_id)
    client_info = mig_objects.ToRDFClientFullInfo(client_info)
    return rule.Evaluate(client_info)

  def testEvaluatesToFalseForClientWithoutTheLabel(self):
    r = foreman_rules.ForemanLabelClientRule(label_names=["arbitrary text"])

    # The client isn't labeled "arbitrary text"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueForClientWithTheLabel(self):
    r = foreman_rules.ForemanLabelClientRule(label_names=["world"])

    # The client is labeled "world"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToTrueInMatchAnyModeIfClientHasOneOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.MATCH_ANY,
        label_names=["nonexistent", "world"],
    )

    # The client is labeled "world"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToFalseInMatchAnyModeIfClientHasNoneOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.MATCH_ANY,
        label_names=["nonexistent", "arbitrary"],
    )

    # The client isn't labeled "nonexistent", nor "arbitrary"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueInMatchAllModeIfClientHasAllOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.MATCH_ALL,
        label_names=["world", "hello"],
    )

    # The client is labeled both "world" and "hello"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToFalseInMatchAllModeIfClientDoesntHaveOneOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.MATCH_ALL,
        label_names=["world", "random"],
    )

    # The client isn't labeled "random"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToFalseInDoesntMatchAnyModeIfClientHasOneOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ANY,
        label_names=["nonexistent", "world"],
    )

    # The client is labeled "world"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueInDoesntMatchAnyModeIfClientHasNoneOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ANY,
        label_names=["nonexistent", "arbitrary"],
    )

    # The client isn't labeled "nonexistent", nor "arbitrary"
    self.assertTrue(self._Evaluate(r))

  def testEvaluatesToFalseInDoesntMatchAllModeIfClientHasAllOfTheLabels(self):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ALL,
        label_names=["world", "hello"],
    )

    # The client is labeled both "world" and "hello"
    self.assertFalse(self._Evaluate(r))

  def testEvaluatesToTrueInDoesntMatchAllModeIfClientDoesntHaveOneOfTheLabels(
      self,
  ):
    r = foreman_rules.ForemanLabelClientRule(
        match_mode=foreman_rules.ForemanLabelClientRule.MatchMode.DOES_NOT_MATCH_ALL,
        label_names=["world", "random"],
    )

    # The client isn't labeled "random"
    self.assertTrue(self._Evaluate(r))


class ForemanRegexClientRuleTest(test_lib.GRRBaseTest):

  def testEvaluation(self):
    now = rdfvalue.RDFDatetime().Now()
    client_id = self.SetupClient(0, last_boot_time=now)
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    for f in foreman_rules.ForemanRegexClientRule.ForemanStringField.enum_dict:
      if f == "UNSET":
        continue

      r = foreman_rules.ForemanRegexClientRule(field=f, attribute_regex=".")
      r.Evaluate(info)

  def testEvaluatesTheWholeAttributeToTrue(self):
    r = foreman_rules.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="^Linux$"
    )

    client_id = self.SetupClient(0, system="Linux")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)
    self.assertTrue(r.Evaluate(info))

  def testEvaluatesAttributesSubstringToTrue(self):
    r = foreman_rules.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="inu"
    )

    client_id = self.SetupClient(0, system="Linux")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # The system contains the substring inu
    self.assertTrue(r.Evaluate(info))

  def testEvaluatesNonSubstringToFalse(self):
    r = foreman_rules.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex="foo"
    )

    client_id = self.SetupClient(0, system="Linux")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # The system doesn't contain foo
    self.assertFalse(r.Evaluate(info))

  def testUnsetFieldRaises(self):
    client_id = self.SetupClient(0, system="Linux")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    r = foreman_rules.ForemanRegexClientRule(attribute_regex="foo")
    with self.assertRaises(ValueError):
      r.Evaluate(info)

  def testUsernames(self):
    client_id = self.SetupClient(0)
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match identifier
    r = foreman_rules.ForemanRegexClientRule(
        field="USERNAMES", attribute_regex=r"user1"
    )
    self.assertTrue(r.Evaluate(info))

    # Non-match
    r = foreman_rules.ForemanRegexClientRule(
        field="USERNAMES", attribute_regex=r"root"
    )
    self.assertFalse(r.Evaluate(info))

  def testFqdn(self):
    client_id = self.SetupClient(0, fqdn="foo.bar.example.com")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match identifier
    r = foreman_rules.ForemanRegexClientRule(
        field="FQDN", attribute_regex=r"foo.*\.example\.com"
    )
    self.assertTrue(r.Evaluate(info))

    # Non-match
    r = foreman_rules.ForemanRegexClientRule(
        field="FQDN", attribute_regex=r"localhost"
    )
    self.assertFalse(r.Evaluate(info))

  def testHostIps(self):
    client_id = self.SetupClient(0)
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match first address
    r = foreman_rules.ForemanRegexClientRule(
        field="HOST_IPS", attribute_regex=r"\b192\.168\.0\.\d+\b"
    )
    self.assertTrue(r.Evaluate(info))

    # Match second address
    r = foreman_rules.ForemanRegexClientRule(
        field="HOST_IPS", attribute_regex=r"\b2001:abcd::"
    )
    self.assertTrue(r.Evaluate(info))

    # Non-match
    r = foreman_rules.ForemanRegexClientRule(
        field="HOST_IPS", attribute_regex=r"10"
    )
    self.assertFalse(r.Evaluate(info))

  def testClientName(self):
    client_id = self.SetupClient(0)
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match identifier
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_NAME", attribute_regex=r"Monitor"
    )
    self.assertTrue(r.Evaluate(info))

    # Non-match
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_NAME", attribute_regex=r"GRRMonitor"
    )
    self.assertFalse(r.Evaluate(info))

  def testClientDescription(self):
    client_id = self.SetupClient(0, description="GRR Description Text")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match identifier
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_DESCRIPTION", attribute_regex=r"description text"
    )
    self.assertTrue(r.Evaluate(info))

    # Non-match
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_DESCRIPTION", attribute_regex=r"GRRDescription"
    )
    self.assertFalse(r.Evaluate(info))

  def testSystem(self):
    client_id = self.SetupClient(0, system="Windows")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match identifier
    r = foreman_rules.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex=r"Win"
    )
    self.assertTrue(r.Evaluate(info))

    # Non-match
    r = foreman_rules.ForemanRegexClientRule(
        field="SYSTEM", attribute_regex=r"Linux"
    )
    self.assertFalse(r.Evaluate(info))

  def testMacAddresses(self):
    client_id = self.SetupClient(0)
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match first address
    r = foreman_rules.ForemanRegexClientRule(
        field="MAC_ADDRESSES", attribute_regex=r"\bAABBCCDDEE\d+\b"
    )
    self.assertTrue(r.Evaluate(info))

    # Match second address
    r = foreman_rules.ForemanRegexClientRule(
        field="MAC_ADDRESSES", attribute_regex=r"\bBBCCDDEEFF\d+\b"
    )
    self.assertTrue(r.Evaluate(info))

    # Non-match
    r = foreman_rules.ForemanRegexClientRule(
        field="MAC_ADDRESSES", attribute_regex=r"\b000000"
    )
    self.assertFalse(r.Evaluate(info))

  def testKernelVersion(self):
    client_id = self.SetupClient(0, kernel="5.15.0-1042-gcp")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match identifier
    r = foreman_rules.ForemanRegexClientRule(
        field="KERNEL_VERSION", attribute_regex=r"^5\..*-gcp$"
    )
    self.assertTrue(r.Evaluate(info))

    # Non-match
    r = foreman_rules.ForemanRegexClientRule(
        field="KERNEL_VERSION", attribute_regex=r"^4"
    )
    self.assertFalse(r.Evaluate(info))

  def testOsVersion(self):
    client_id = self.SetupClient(0, os_version="10.0.22621")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match identifier
    r = foreman_rules.ForemanRegexClientRule(
        field="OS_VERSION", attribute_regex=r"^10\..*"
    )
    self.assertTrue(r.Evaluate(info))

    # Non-match
    r = foreman_rules.ForemanRegexClientRule(
        field="OS_VERSION", attribute_regex=r"22.04"
    )
    self.assertFalse(r.Evaluate(info))

  def testOsRelease(self):
    client_id = self.SetupClient(0, os_release="Debian")
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match identifier
    r = foreman_rules.ForemanRegexClientRule(
        field="OS_RELEASE", attribute_regex=r"\bDebian\b"
    )
    self.assertTrue(r.Evaluate(info))

    # Non-match
    r = foreman_rules.ForemanRegexClientRule(
        field="OS_RELEASE", attribute_regex=r"\bVista\b"
    )
    self.assertFalse(r.Evaluate(info))

  def testLabels(self):
    client_id = self.SetupClient(0, system="Linux")

    data_store.REL_DB.WriteGRRUser("GRR")
    data_store.REL_DB.AddClientLabels(client_id, "GRR", ["hello", "world"])

    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match a system label.
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_LABELS", attribute_regex="label1"
    )
    self.assertTrue(r.Evaluate(info))

    # Match a user label.
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_LABELS", attribute_regex="ell"
    )
    self.assertTrue(r.Evaluate(info))

    # This rule doesn't match any label.
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_LABELS", attribute_regex="NonExistentLabel"
    )
    self.assertFalse(r.Evaluate(info))

  def testClientId(self):
    client_id = self.SetupClient(0)
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    # Match identifier
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_ID", attribute_regex=client_id
    )
    self.assertTrue(r.Evaluate(info))

    # Match slice
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_ID", attribute_regex=r"c\.10.*"
    )
    self.assertTrue(r.Evaluate(info))

    # Non-match
    r = foreman_rules.ForemanRegexClientRule(
        field="CLIENT_ID", attribute_regex=r"abc"
    )
    self.assertFalse(r.Evaluate(info))


class ForemanIntegerClientRuleTestRelational(test_lib.GRRBaseTest):

  def testEvaluation(self):
    now = rdfvalue.RDFDatetime().Now()
    client_id = self.SetupClient(0, last_boot_time=now)
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    int_f = foreman_rules.ForemanIntegerClientRule.ForemanIntegerField
    for f in int_f.enum_dict:
      if f == "UNSET":
        continue

      r = foreman_rules.ForemanIntegerClientRule(
          field=f,
          operator=foreman_rules.ForemanIntegerClientRule.Operator.LESS_THAN,
          value=now.AsSecondsSinceEpoch(),
      )
      r.Evaluate(info)

  def testEvaluatesSizeLessThanEqualValueToFalse(self):
    now = rdfvalue.RDFDatetime().Now()
    client_id = self.SetupClient(0, last_boot_time=now)
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    r = foreman_rules.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=foreman_rules.ForemanIntegerClientRule.Operator.LESS_THAN,
        value=now.AsSecondsSinceEpoch(),
    )

    # The values are the same, less than should not trigger.
    self.assertFalse(r.Evaluate(info))

  def testEvaluatesSizeGreaterThanSmallerValueToTrue(self):
    now = rdfvalue.RDFDatetime().Now()
    client_id = self.SetupClient(0, last_boot_time=now)
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    before_boot = now - 1

    r = foreman_rules.ForemanIntegerClientRule(
        field="LAST_BOOT_TIME",
        operator=foreman_rules.ForemanIntegerClientRule.Operator.GREATER_THAN,
        value=before_boot.AsSecondsSinceEpoch(),
    )

    self.assertTrue(r.Evaluate(info))

  def testEvaluatesRaisesWithUnsetField(self):
    r = foreman_rules.ForemanIntegerClientRule(
        operator=foreman_rules.ForemanIntegerClientRule.Operator.EQUAL,
        value=123,
    )

    client_id = self.SetupClient(0)
    info = data_store.REL_DB.ReadClientFullInfo(client_id)
    info = mig_objects.ToRDFClientFullInfo(info)

    with self.assertRaises(ValueError):
      r.Evaluate(info)


def main(argv):
  # Run the full test suite
  test_lib.main(argv)


if __name__ == "__main__":
  app.run(main)
