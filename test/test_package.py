"""Tests for the :mod:`masafi_sim_petri` package layout and metadata."""

import importlib
from importlib.metadata import distribution

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


def test_public_api_is_re_exported_from_the_top_level() -> None:
    """The names in ``__all__`` are importable from the top-level package.

    Consumer projects import from :mod:`masafi_sim_petri` rather than from the
    internal module paths, so every advertised name must resolve there.
    """
    for name in masafi_sim_petri.__all__:
        assert hasattr(masafi_sim_petri, name), name


def test_the_examples_are_not_part_of_the_distribution() -> None:
    """``src/examples`` holds scripts, and scripts are not shipped.

    The distribution declares one top-level package. The example scripts sit
    under ``src`` so that they live with the source, but ``packages.find``
    excludes them, so neither the wheel nor the sdist carries them.

    Note that ``import examples`` does succeed in a development install: an
    editable install puts ``src`` itself on ``sys.path``, which makes every
    directory under it importable. That is a property of the development
    environment, not of the distribution, which is what this checks.
    """
    top_level = distribution('masafi-sim-petri').read_text('top_level.txt')

    assert top_level is not None
    assert top_level.split() == ['masafi_sim_petri']
