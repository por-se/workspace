from typing import Dict

from cached_property import cached_property

from .vyper import get


class UriSchemes:
    """The configured extra URI schemas (Dict[str, str])"""

    name = "uri-schemes"

    def resolve(self, uri: str) -> str:
        for (prefix, replacement) in self.value.items():
            if uri.startswith(prefix):
                return replacement + uri[len(prefix):]
        return uri

    @cached_property
    def value(self) -> Dict[str, str]:
        value = get(self.name)
        if value is None:
            return {}

        assert isinstance(value, dict)
        for key, val in value.items():
            assert isinstance(key, str)
            assert isinstance(val, str)

        return value
