import uuid
import os
import datetime
import tempfile
from unittest.mock import Mock, patch
from xmlrpc import client as xml_client

import responses
import pytz
import pytest

from aura import package
from aura import exceptions


REQUESTS_DEPS = [str(uuid.uuid4()) for _ in range(2896)]  # Mock `requests` reverse dependencies for pacakge score matrix


def test_non_existing_package():
    with pytest.raises(exceptions.NoSuchPackage):
        package.PypiPackage.from_pypi(f"does_not_exists_{str(uuid.uuid4())}")


def test_package_listing():
    existing = {
        "requests",
        "django",
    }

    xml_client.ServerProxy = Mock()
    instance = xml_client.ServerProxy.return_value
    instance.list_packages.return_value = existing
    on_pypi = set(x.lower() for x in package.PypiPackage.list_packages())

    assert len(existing.difference(on_pypi)) == 0


@responses.activate
def test_package_retrieval(mock_pypi_rest_api):
    mock_pypi_rest_api(responses)
    pkg = package.PypiPackage.from_pypi("wheel")
    url = "https://files.pythonhosted.org/packages/8c/23/848298cccf8e40f5bbb59009b32848a4c38f4e7f3364297ab3c3e2e2cd14/wheel-0.34.2-py2.py3-none-any.whl"

    assert pkg.name == "wheel"
    assert pkg.source == "pypi"  # TODO: add tests for other package options

    with pkg.url2local(url) as location:
        assert location.is_file()
        file_name = url.split("/")[-1]
        assert location.name.endswith(file_name), (location, file_name)

    with tempfile.TemporaryDirectory(prefix="aura_pytest_") as tmp:
        downloaded = [x["filename"] for x in pkg.download_release(tmp, packagetype="all", release="0.34.2")]
        content = os.listdir(tmp)

    assert "wheel-0.34.2.tar.gz" in downloaded
    assert "wheel-0.34.2.tar.gz" in content
    assert "wheel-0.34.2-py2.py3-none-any.whl" in downloaded
    assert "wheel-0.34.2-py2.py3-none-any.whl" in content


@responses.activate
@patch("aura.package.get_reverse_dependencies", return_value=REQUESTS_DEPS)
def test_package_score(mock1, mock_github, mock_pypi_rest_api, mock_pypi_stats):
    mock_github(responses)
    mock_pypi_rest_api(responses)

    pkg = package.PackageScore("requests")
    pkg.now = pytz.UTC.localize(datetime.datetime.fromisoformat("2020-04-18T14:21:43.572676"))

    assert pkg.package_name == "requests"
    assert pkg.pkg.info["info"]["name"] == "requests"
    assert pkg.github is not None
    assert pkg.github.owner == "psf"
    assert pkg.github.name == "requests"

    matrix = pkg.get_score_matrix()

    scores = {x["slug"]: x["normalized"] for x in matrix["entries"]}

    assert scores["github_contributors"] == 2
    assert scores["github_forks"] == 4
    assert scores["github_stars"] == 5
    assert scores["has_documentation"] == 1
    assert scores["has_homepage"] == 1
    assert scores["has_sdist"] == 1
    assert scores["has_source_repository"] == 1
    assert scores["has_wheel"] == 1
    assert scores["new_on_github"] == 1
    assert scores["recent_commit"] == 1
    assert scores["multiple_releases"] == 3
    assert matrix["total"] >= 19

    # Make the package seem outdated
    pkg.now = pytz.UTC.localize(
        datetime.datetime.utcnow() + datetime.timedelta(365)
    )
    matrix = pkg.get_score_matrix()
    scores = {x["slug"]: x["normalized"] for x in matrix["entries"]}
    assert scores["recent_commit"] == 0


@responses.activate
@patch("aura.package.get_reverse_dependencies", return_value=[])
def test_bad_package_score(mock1, mock_github, mock_pypi_rest_api, mock_pypi_stats):
    mock_pypi_rest_api(responses)
    mock_github(responses)

    pkg = package.PackageScore("badboy")
    matrix = pkg.get_score_matrix()
    assert matrix["total"] == 0


@responses.activate
def test_package_diff_candidates(mock_pypi_rest_api):
    mock_pypi_rest_api(responses)
    convert = lambda x: (x[0]["filename"], x[1]["filename"])
    requests = package.PypiPackage.from_pypi("requests")
    requests2 = package.PypiPackage.from_pypi("requests2")

    candidates = tuple(map(convert, requests.get_diff_candidates(requests2)))
    assert ('requests-2.16.0.tar.gz', 'requests2-2.16.0.tar.gz') in candidates
    assert ('requests-2.24.0.tar.gz', 'requests2-2.16.0.tar.gz') not in candidates

    requests.opts["diff_include_latest"] = True
    candidates = tuple(map(convert, requests.get_diff_candidates(requests2)))
    assert ('requests-2.16.0.tar.gz', 'requests2-2.16.0.tar.gz') in candidates
    assert ('requests-2.24.0.tar.gz', 'requests2-2.16.0.tar.gz') in candidates
