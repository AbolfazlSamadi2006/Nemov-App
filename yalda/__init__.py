"""
Backward-compatibility redirection shim for legacy imports.
Redirects all `yalda` imports and submodules transparently to `nemov`.
"""
import sys
import importlib
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec


class _YaldaAliasLoader(Loader):
    def __init__(self, target_name):
        self.target_name = target_name

    def create_module(self, spec):
        mod = importlib.import_module(self.target_name)
        sys.modules[spec.name] = mod
        return mod

    def exec_module(self, module):
        pass


class _YaldaAliasFinder(MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == "yalda" or fullname.startswith("yalda."):
            nemov_name = "nemov" + fullname[len("yalda"):]
            try:
                mod = importlib.import_module(nemov_name)
                is_pkg = hasattr(mod, "__path__")
                return ModuleSpec(fullname, _YaldaAliasLoader(nemov_name), is_package=is_pkg)
            except ModuleNotFoundError:
                return None
        return None


# 1. Register MetaPathFinder hook
if not any(isinstance(finder, _YaldaAliasFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _YaldaAliasFinder())

# 2. Import nemov package
import nemov

# 3. Share __path__ so standard import machinery explores nemov subdirectories
if hasattr(nemov, "__path__"):
    __path__ = list(nemov.__path__)

# 4. Point sys.modules['yalda'] directly to nemov
sys.modules[__name__] = nemov

# 5. Mirror top-level attributes
for _k, _v in list(vars(nemov).items()):
    if not _k.startswith("__"):
        globals()[_k] = _v


# 6. Dynamic getattr fallback
def __getattr__(name):
    return getattr(nemov, name)
