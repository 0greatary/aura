import tempfile
import pathlib
import shutil
from urllib.parse import ParseResult

import git

from .. import config
from .base import URIHandler, ScanLocation


LOGGER = config.get_logger(__name__)


class GitRepoHandler(URIHandler):
    scheme = "git"
    help = """
    Git repository handler.
    Clones the target repository into a temporary directory.
    """

    def __init__(self, uri: ParseResult):
        super().__init__(uri)
        self.uri = uri
        self.opts = {}

    @classmethod
    def is_supported(cls, parsed_uri: ParseResult):
        # Both SSH and HTTPS repo uris always ends with .git
        return parsed_uri.path.endswith('.git')

    @property
    def metadata(self):
        m = {
            "uri": self.uri,
            "scheme": self.scheme
        }
        return m

    def get_paths(self, metadata: dict=None):
        if self.opts.get('download_dir') is None:
            p = tempfile.mkdtemp(prefix="aura_git_repo_clone_")
            self.opts["download_dir"] = p
            self.opts["cleanup"] = True
        else:
            p = self.opts["download_dir"]

        LOGGER.info(f"Cloning git repository to {p}")
        git.Repo.clone_from(url=self.uri.geturl(), to_path=p)

        yield ScanLocation(
            location=p,
            metadata=metadata or {"depth": 0}
        )

    def cleanup(self):
        p = pathlib.Path(self.opts["download_dir"])
        if self.opts.get("cleanup", False) and p.exists():
            shutil.rmtree(p)
