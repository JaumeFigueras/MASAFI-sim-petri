"""Tests for the :mod:`masafi_sim_petri` package layout and metadata."""

import importlib

import pytest

import masafi_sim_petri


def test_package_is_importable() -> None:
    """The package is importable by the name consumer projects will use.

    This guards the ``src`` layout: if the packaging configuration stops
    exposing ``src/masafi_sim_petri`` as the ``masafi_sim_petri`` package,
    this test fails before any net code is exercised.
    """
    assert masafi_sim_petri.__name__ == "masafi_sim_petri"


def test_version_is_resolved_from_installed_metadata() -> None:
    """``__version__`` comes from the installed distribution metadata.

    The fallback value ``"0.0.0"`` is used only when the package is imported
    without being installed, so a real version here proves the editable
    install is in place.
    """
    assert masafi_sim_petri.__version__ != "0.0.0"


@pytest.mark.parametrize(
    "subpackage", ["petri_net", "analysis", "simulation"]
)
def test_subpackages_are_importable(subpackage: str) -> None:
    """Every subpackage is reachable under the single top-level package.

    Parameters
    ----------
    subpackage : str
        Name of the subpackage, relative to :mod:`masafi_sim_petri`.
    """
    module = importlib.import_module(f"masafi_sim_petri.{subpackage}")

    assert module.__name__ == f"masafi_sim_petri.{subpackage}"


def test_no_generic_top_level_packages_are_installed() -> None:
    """Generic names are not claimed in the global import namespace.

    ``analysis``, ``simulation`` and ``petri_net`` are names another
    dependency could plausibly want. They must only exist nested inside
    :mod:`masafi_sim_petri`.
    """
    for name in ["petri_net", "analysis", "simulation"]:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(name)
