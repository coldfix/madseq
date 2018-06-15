"""
Serialization primitives.
"""

from __future__ import absolute_import
from __future__ import division

from decimal import Decimal

from madseq.util import stri, odicti
from madseq.types import Value, Array, Composed, Identifier, Symbolic


class Json(object):

    """JSON serialization utility."""

    def __init__(self):
        """Import json module for later use."""
        import json
        self.json = json

    def dump(self, data, stream):
        """Dump data with types defined in this module."""
        json = self.json
        class fakefloat(float):
            """Used to serialize Decimal.
            See: http://stackoverflow.com/a/8274307/650222"""
            def __init__(self, value):
                self._value = value
            def __repr__(self):
                return str(self._value)
        class ValueEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, Value):
                    return obj.value
                if isinstance(obj, Decimal):
                    return fakefloat(obj.normalize())
                # Let the base class default method raise the TypeError
                return json.JSONEncoder.default(self, obj)
        json.dump(data, stream,
                  indent=2,
                  separators=(',', ' : '),
                  cls=ValueEncoder)

    def load(self, stream):
        """Load data from, using ordered case insensitive dictionaries."""
        return self.json.load(stream, object_pairs_hook=odicti)


class Yaml(object):

    """YAML serialization utility."""

    def __init__(self):
        """Import yaml module for later use."""
        import yaml
        self.yaml = yaml

    def dump(self, data, stream=None):
        """Dump data with types defined in this module."""
        yaml = self.yaml
        class Dumper(yaml.SafeDumper):
            pass
        def _dict_representer(dumper, data):
            return dumper.represent_mapping(
                yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                data.items())
        def _stri_representer(dumper, data):
            return dumper.represent_str(data)
        def _Value_representer(dumper, data):
            return dumper.represent_str(data.value)
        def _Decimal_representer(dumper, data):
            return dumper.represent_scalar(u'tag:yaml.org,2002:float',
                                           str(data).lower())
        Dumper.add_representer(odicti, _dict_representer)
        Dumper.add_representer(stri.cls, _stri_representer)
        Dumper.add_representer(Symbolic, _Value_representer)
        Dumper.add_representer(Identifier, _Value_representer)
        Dumper.add_representer(Composed, _Value_representer)
        Dumper.add_representer(Array, _Value_representer)
        Dumper.add_representer(Decimal, _Decimal_representer)
        return yaml.dump(data, stream, Dumper, default_flow_style=False)

    def load(self, stream):
        """Load data from, using ordered case insensitive dictionaries."""
        yaml = self.yaml
        class OrderedLoader(yaml.SafeLoader):
            pass
        OrderedLoader.add_constructor(
            yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
            lambda loader, node: odicti(loader.construct_pairs(node)))
        return yaml.load(stream, OrderedLoader)
