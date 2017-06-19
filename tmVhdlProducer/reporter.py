# -*- coding: utf-8 -*-
#
# Repository path   : $HeadURL:  $
# Last committed    : $Revision:  $
# Last changed by   : $Author:  $
# Last changed date : $Date: $
#

import tmEventSetup

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from tmVhdlProducer.vhdlhelper import vhdl_label, vhdl_expression

import uuid
import shutil
import tempfile
import datetime
import logging
import re
import sys, os

from tmVhdlProducer import __version__
__all__ = ['Reporter', ]

esMuonTypes = (
    tmEventSetup.SingleMuon,
    tmEventSetup.DoubleMuon,
    tmEventSetup.TripleMuon,
    tmEventSetup.QuadMuon,
)

esEgammaTypes = (
    tmEventSetup.SingleEgamma,
    tmEventSetup.DoubleEgamma,
    tmEventSetup.TripleEgamma,
    tmEventSetup.QuadEgamma,
    tmEventSetup.SingleEgammaOvRm,
    tmEventSetup.DoubleEgammaOvRm,
    tmEventSetup.TripleEgammaOvRm,
    tmEventSetup.QuadEgammaOvRm,
)

esJetTypes = (
    tmEventSetup.SingleJet,
    tmEventSetup.DoubleJet,
    tmEventSetup.TripleJet,
    tmEventSetup.QuadJet,
    tmEventSetup.SingleJetOvRm,
    tmEventSetup.DoubleJetOvRm,
    tmEventSetup.TripleJetOvRm,
    tmEventSetup.QuadJetOvRm,
)

esTauTypes = (
    tmEventSetup.SingleTau,
    tmEventSetup.DoubleTau,
    tmEventSetup.TripleTau,
    tmEventSetup.QuadTau,
    tmEventSetup.SingleTauOvRm,
    tmEventSetup.DoubleTauOvRm,
    tmEventSetup.TripleTauOvRm,
    tmEventSetup.QuadTauOvRm,
)

esEnergySumsTypes = (
    tmEventSetup.TotalEt,
    tmEventSetup.TotalHt,
    tmEventSetup.TotalEtEM,
    tmEventSetup.MissingEt,
    tmEventSetup.MissingHt,
    tmEventSetup.MissingEtHF,
)

esMinBiasHfTypes = (
    tmEventSetup.MinBiasHFM0,
    tmEventSetup.MinBiasHFM1,
    tmEventSetup.MinBiasHFP0,
    tmEventSetup.MinBiasHFP1,
)

esTowerCountTypes = (
    tmEventSetup.TowerCount,
)

esCorrelationTypes = (
    tmEventSetup.MuonMuonCorrelation,
    tmEventSetup.MuonEsumCorrelation,
    tmEventSetup.CaloMuonCorrelation,
    tmEventSetup.CaloCaloCorrelation,
    tmEventSetup.CaloEsumCorrelation,
    tmEventSetup.CaloCaloCorrelationOvRm,
)

esMassTypes = (
    tmEventSetup.InvariantMass,
    tmEventSetup.TransverseMass,
    tmEventSetup.InvariantMassOvRm,
)

esMuonGroup = "Muon"
esEgammaGroup = "E/gamma"
esJetGroup = "Jet"
esTauGroup = "Tau"
esEnergySumsGroup = "Energy Sums"
esMinBiasHfGroup = "Min Bias HF"
esTowerCountGroup = "Tower Count"
esCrossGroup = "Cross"
esCorrelationGroup = "Correlation"
esMassGroup = "Mass"
esExternalGroup = "External"

esTriggerGroups = (
    esMuonGroup,
    esEgammaGroup,
    esJetGroup,
    esTauGroup,
    esEnergySumsGroup,
    esMinBiasHfGroup,
    esTowerCountGroup,
    esCrossGroup,
    esCorrelationGroup,
    esMassGroup,
    esExternalGroup,
)

esCutType = {
    tmEventSetup.Threshold: 'Threshold',
    tmEventSetup.Eta: 'Eta',
    tmEventSetup.Phi: 'Phi',
    tmEventSetup.Charge: 'Charge',
    tmEventSetup.Quality: 'Quality',
    tmEventSetup.Isolation: 'Isolation',
    tmEventSetup.DeltaEta: 'DeltaEta',
    tmEventSetup.DeltaPhi: 'DeltaPhi',
    tmEventSetup.DeltaR: 'DeltaR',
    tmEventSetup.Mass: 'Mass',
    tmEventSetup.TwoBodyPt: 'TwoBodyPt',
    tmEventSetup.Slice: 'Slice',
    tmEventSetup.OvRmDeltaEta: 'OvRmDeltaEta',
    tmEventSetup.OvRmDeltaPhi: 'OvRmDeltaPhi',
    tmEventSetup.OvRmDeltaR: 'OvRmDeltaR',
    tmEventSetup.ChargeCorrelation: 'ChargeCorrelation',
    tmEventSetup.Count: 'Count',
}

# -----------------------------------------------------------------------------
#  Helpers
# -----------------------------------------------------------------------------

def getenv(name):
    """Get environment variable. Raises a RuntimeError exception if variable not set."""
    value = os.getenv(name)
    if value is None:
        raise RuntimeError("`{name}' environment not set".format(**locals()))
    return value

# -----------------------------------------------------------------------------
#  Jinja Filters
# -----------------------------------------------------------------------------

def exprColorize(expression):
    rules = (
        (r',',
         r', '),
        (r'(dist|comb|mass|mass_inv|mass_trv|dist_orm|comb_orm|mass_inv_orm|mass_trv_orm)(\{)([^\}]*)(\})',
         r'<span class="function">\1</span><span class="curl">\2</span>\3<span class="curl">\4</span>'),
        (r'\b(AND|OR|XOR|NOT)\b',
         r'<span class="keyword">\1</span>'),
    )
    for pattern, repl in rules:
        expression = re.sub(pattern, repl, expression)
    return expression

def vhdlColorize(expression):
    rules = (
        (r'\b([a-zA-Z_][a-zA-Z0-9_]*[0-9]+)\b',
         lambda match: '<span class="vhdlsig">{0}</span>'.format(match.group(1))),
        (r'\b(and|or|xor|not|AND|OR|XOR|NOT)\b',
         lambda match: '<span class="vhdlop">{0}</span>'.format(match.group(1).lower())),
    )
    for pattern, repl in rules:
        expression = re.sub(pattern, repl, expression)
    return expression

# -----------------------------------------------------------------------------
#  Structs
# -----------------------------------------------------------------------------

class MenuStub:
    """Menu template helper class.
    name             full menu name
    uuid_menu        UUID of originating menu
    uuid_firmware    UUID of firmware build
    scale_set        used scale set label
    grammar_version  grammar version of menu
    datetime         optional menu creation timestamp
    comment          optional menu comment
    algorithms       list of algorithm template helpers
    """
    def __init__(self, es):
        self.name = es.getName()
        self.uuid_menu = es.getMenuUuid()
        self.uuid_firmware = es.getFirmwareUuid()
        self.scale_set = es.getScaleSetName()
        self.grammar_version = es.getVersion()
        self.datetime = es.getDatetime()
        self.comment = es.getComment()
        self.algorithms = self._getAlgorithms(es)
    def _getAlgorithms(self, es):
        """Returns list of algorithm stubs sorted by index."""
        algorithmMapPtr = es.getAlgorithmMapPtr()
        algorithms = [AlgorithmStub(es, algorithm) for algorithm in es.getAlgorithmMapPtr().values()]
        algorithms.sort(key=lambda algorithm: algorithm.index)
        return algorithms

class AlgorithmStub:
    """Algorithm template helper class.
    name            full algorithm name
    index           global algorithm index (int)
    moduleId        module ID (int)
    moduleIndex     local module algorithm index (int)
    expression      original grammar notation of expression
    vhdlExpression  VHDL notation of expression
    rpnVector       reversed polish notation of expression
    comment         n/a
    conditions      list of condition template helpers
    """
    def __init__(self, es, ptr):
        self.name = ptr.getName()
        self.index = ptr.getIndex()
        self.moduleId = ptr.getModuleId()
        self.moduleIndex = ptr.getModuleIndex()
        self.expression = ptr.getExpression()
        self.vhdlExpression = ptr.getExpressionInCondition()
        self.rpnVector = ptr.getRpnVector()
        self.comment = "" # not retrievable from esAlgorithm
        self.conditions = self._getConditions(es)
    def _getConditions(self, es):
        """Returns list of condition stubs assigned to algorithm, sorted by order of appereance."""
        conditionMapPtr = es.getConditionMapPtr()
        conditions = {}
        mapping = self._getMapping()
        for token in self.rpnVector:
            if token in conditionMapPtr:
                conditions[token] = ConditionStub(conditionMapPtr[token], token=mapping[token])
        conditions = conditions.values()
        conditions.sort(key=lambda condition: self.rpnVector.index(condition.name))
        return conditions
    def _getMapping(self):
        """Returns token mapping."""
        mapping = {}
        # split expression and vhdl expression and try to map the tokens, thats just completely manky
        vhdlTokens = re.sub(r'[\(\)]', ' ', self.vhdlExpression).split() # remove braces and split
        exprTokens = re.sub(r'[\(\)]', ' ', self.expression).split()
        assert len(vhdlTokens) == len(exprTokens)
        for i in range(len(vhdlTokens)):
            mapping[vhdlTokens[i]] = exprTokens[i]
        return mapping

class ConditionStub:
    """Condition template helper class.
    name     auto generated condtion name
    type     condition type (enum)
    objects  list of object template helpers
    cuts     list of cut template helpers
    token    expression token for display purposes
    """
    def __init__(self, ptr, token=None):
        self.name = ptr.getName()
        self.type = ptr.getType()
        self.objects = [ObjectStub(obj) for obj in ptr.getObjects()]
        self.cuts = [CutStub(cut) for cut in ptr.getCuts()]
        self.token = token or "" # store the expression notation for display purposes

class ObjectStub:
    """Object template helper class.
    name           full object name
    type           object type (enum)
    comparisonOperator  comparision operator (enum)
    bxOffset       bunch crossing offset (int)
    threshold      object threshold in GeV (float)
    extSignalName  external signal name (only valid for EXT type objects)
    extChannelId   channel id of external signal (only valid for EXT type objects)
    cuts           list of cut template helpers
    """
    def __init__(self, ptr):
        self.name = ptr.getName()
        self.type = ptr.getType()
        self.comparisonOperator = ptr.getComparisonOperator()
        self.bxOffset = ptr.getBxOffset()
        self.threshold = ptr.getThreshold() # in GeV
        self.extSignalName = ptr.getExternalSignalName()
        self.extChannelId = ptr.getExternalChannelId()
        self.cuts = [CutStub(cut) for cut in ptr.getCuts()]

class CutStub:
    """Cut template helper class.
    name          full cut name
    objectType    object type, optional (enum)
    cutType       cut type (enum)
    minimumValue  minimum range value (float)
    maximumValue  maximum range value (float)
    minimumIndex  minimum range index (int)
    maximumIndex  maximum range index (int)
    precision     assigned decimal precision for values (int)
    data          payload data (for non range cuts)
    key           scale access key
    """
    def __init__(self, ptr):
        self.name = ptr.getName()
        self.objectType = ptr.getObjectType()
        self.cutType = ptr.getCutType()
        self.minimumValue = ptr.getMinimumValue()
        self.maximumValue = ptr.getMaximumValue()
        self.minimumIndex = ptr.getMinimumIndex()
        self.maximumIndex = ptr.getMaximumIndex()
        self.precision = ptr.getPrecision()
        self.data = ptr.getData()
        self.key = ptr.getKey()

# -----------------------------------------------------------------------------
#  Template engines with custom resource loader environment.
# -----------------------------------------------------------------------------

class TemplateEngine(object):
    """Custom tempalte engine class."""

    def __init__(self, searchpath, encoding='utf-8'):
        # Create Jinja environment.
        loader = FileSystemLoader(searchpath, encoding)
        self.environment = Environment(loader=loader, undefined=StrictUndefined)
        # Add filters
        self.environment.filters['exprColorize'] = exprColorize
        self.environment.filters['vhdlColorize'] = vhdlColorize
        self.environment.filters['vhdlLabel'] = vhdl_label
        self.environment.filters['vhdlExpression'] = vhdl_expression
        def hex(value, n=1): return format(value, '0{n}x'.format(n=n))
        self.environment.filters['hex'] = hex

    def render(self, template, data={}):
        template = self.environment.get_template(template)
        return template.render(data)

# -----------------------------------------------------------------------------
#  Reporter class
# -----------------------------------------------------------------------------

class Reporter(object):
    """Reporter class."""

    def __init__(self, searchpath, eventSetup):
        # Template search path
        self.searchpath = searchpath
        # Initialize empty menu content.
        self.eventSetup = eventSetup

    def getTriggerGroups(self, menu):
        """Returns ordered list of trigger group tuples."""
        triggerGroups = {}
        def add_algorithm(group, algorithm):
            """Adds algorithm to trigger group dictionary, creates new sets on demand."""
            if group not in triggerGroups:
                triggerGroups[group] = set()
            triggerGroups[group].add(algorithm)
        # Categorize algorithms
        for algorithm in menu.algorithms:
            if len(algorithm.conditions) > 1:
                add_algorithm(esCrossGroup, algorithm)
            else:
                condition = algorithm.conditions[0]
                if condition.type in esMuonTypes:
                    add_algorithm(esMuonGroup, algorithm)
                elif condition.type in esEgammaTypes:
                    add_algorithm(esEgammaGroup, algorithm)
                elif condition.type in esJetTypes:
                    add_algorithm(esJetGroup, algorithm)
                elif condition.type in esTauTypes:
                    add_algorithm(esTauGroup, algorithm)
                elif condition.type in esEnergySumsTypes:
                    add_algorithm(esEnergySumsGroup, algorithm)
                elif condition.type in esMinBiasHfTypes:
                    add_algorithm(esMinBiasHfGroup, algorithm)
                elif condition.type in esTowerCountTypes:
                    add_algorithm(esTowerCountGroup, algorithm)
                elif condition.type in esCorrelationTypes:
                    add_algorithm(esCorrelationGroup, algorithm)
                elif condition.type in esMassTypes:
                    add_algorithm(esMassGroup, algorithm)
                elif condition.type == tmEventSetup.Externals:
                    add_algorithm(esExternalGroup, algorithm)
                else:
                    raise KeyError("unknown condition type")
        # Sort algorithms
        for group in triggerGroups:
            triggerGroups[group] = sorted(triggerGroups[group], key=lambda algorithm: algorithm.conditions[0].type)
            triggerGroups[group].sort(key=lambda algorithm: algorithm.index) # sort algorithms of group by index
        # Sort groups
        sortedTriggerGroups = []
        sortedKeys = sorted(triggerGroups.keys(), key=lambda group: esTriggerGroups.index(group))
        for group in sortedKeys:
            sortedTriggerGroups.append((group, triggerGroups[group]))
        return sortedTriggerGroups

    def render_html(self):
        """Render HTML report."""
        menu = MenuStub(self.eventSetup)
        data = dict(
            menu=menu,
            es=tmEventSetup,
            reporter=dict(
                timestamp=datetime.datetime.now().strftime("%F %T"),
                version=__version__,
            ),
        )
        return TemplateEngine(self.searchpath).render('report.html', data)

    def render_twiki(self):
        """Render TWIKI report."""
        menu = MenuStub(self.eventSetup)
        menu.triggerGroups = self.getTriggerGroups(menu)
        data = dict(menu=menu)
        return TemplateEngine(self.searchpath).render('report.twiki', data)

    def write_html(self, filename):
        """Write HTML report to file, provided for convenience."""
        with open(filename, 'wb') as handle:
            handle.write(self.render_html())

    def write_twiki(self, filename):
        """Write TWIKI report to file, provided for convenience."""
        with open(filename, 'wb') as handle:
            handle.write(self.render_twiki())
