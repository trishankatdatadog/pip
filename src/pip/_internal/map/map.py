import json
import os
import re

from typing import Any, Dict, List, Union

from pip._internal.exceptions import ConfigurationFileCouldNotBeLoaded

# https://peps.python.org/pep-0519/#provide-specific-type-hinting-support
PathLike = Union[str, bytes, os.PathLike]

class Map:
    """A class that tracks the TUF TAP 4 idea of the map file.
    """

    def __init__(self, path_to_config_file: PathLike) -> None:
        """Act like 'cue vet map.cue path_to_config_file'.
        """

        # Read the map file.
        with open(path_to_config_file, 'r') as f:
            map: Any = json.load(f)

        # The map file must have a top-level repositories object.
        repositories: Dict[str] = map.get("repositories")
        if not repositories:
            raise ConfigurationFileCouldNotBeLoaded(
                reason="Map file missing the 'repositories' key",
                fname=path_to_config_file,
            )

        # The repositories must be a map from names to URLs.
        for name, urls in repositories.items():
            if not isinstance(urls, List):
                raise ConfigurationFileCouldNotBeLoaded(
                        reason=f"for repository {name}, urls not a list: {urls}",
                        fname=path_to_config_file,
                    )

            # The URLs must be a list of strings, and point to HTTPS servers.
            for url in urls:
                if not isinstance(url, str) or not re.match(r"(https://)(.+)", url):
                    raise ConfigurationFileCouldNotBeLoaded(
                        reason=f"for repository {name}, a url not valid: {url}",
                        fname=path_to_config_file,
                    )

        # The map file must have a top-level mapping object.
        mapping: List[Dict] = map.get("mapping")
        if not mapping:
            raise ConfigurationFileCouldNotBeLoaded(
                reason="Map file missing the 'mapping' key",
                fname=path_to_config_file,
            )

        # The mapping must be a list.
        if not isinstance(mapping, List):
            raise ConfigurationFileCouldNotBeLoaded(
                reason=f"mapping not a list: {mapping}",
                fname=path_to_config_file,
            )

        # Each mapping must be an object.
        for m in mapping:
            if not isinstance(m, Dict):
                raise ConfigurationFileCouldNotBeLoaded(
                    reason=f"in mapping, not a dict: {m}",
                    fname=path_to_config_file,
                )

            # Each mapping must have paths.
            paths: List[str] = m.get("paths")
            # Paths must be a list.
            if not isinstance(paths, List):
                raise ConfigurationFileCouldNotBeLoaded(
                    reason=f"paths not a list: {paths}",
                    fname=path_to_config_file,
                )
            # Each path must match a glob-like syntax.
            # TODO: refine syntax.
            for path in paths:
                if not isinstance(path, str) or not re.match(r"[/w/\*]+", path):
                    raise ConfigurationFileCouldNotBeLoaded(
                        reason=f"for paths {paths}, a path not valid: {path}",
                        fname=path_to_config_file,
                    )
            # Paths must be unique at least on a surface level.
            if len(paths) < len(set(paths)):
                raise ConfigurationFileCouldNotBeLoaded(
                    reason=f"paths not unique: {paths}",
                    fname=path_to_config_file,
                )

            # Repositories must be a list.
            _repositories: List[str] = m.get("repositories")
            if not isinstance(_repositories, List):
                raise ConfigurationFileCouldNotBeLoaded(
                    reason=f"repositories not a list: {_repositories}",
                    fname=path_to_config_file,
                )
            # Each repository must have been defined earlier in the top-level map file.
            for repository in _repositories:
                if not isinstance(repository, str) or repository not in repositories:
                    raise ConfigurationFileCouldNotBeLoaded(
                        reason=f"for repositories {_repositories}, a repository not valid: {repository}",
                        fname=path_to_config_file,
                    )
            # Repositories must be unique at least on a surface level.
            if len(_repositories) < len(set(_repositories)):
                raise ConfigurationFileCouldNotBeLoaded(
                    reason=f"repositories not unique: {_repositories}",
                    fname=path_to_config_file,
                )

            # Should we terminate any matching search here?
            terminating: bool = m.get("terminating", True)
            if not isinstance(terminating, bool):
                raise ConfigurationFileCouldNotBeLoaded(
                    reason=f"terminating not boolean: {terminating}",
                    fname=path_to_config_file,
                )

            # How many of these repositories should we use for our search?
            threshold: int = m.get("threshold", len(_repositories))
            if not isinstance(threshold, int) or threshold < 1 or threshold > len(_repositories):
                raise ConfigurationFileCouldNotBeLoaded(
                    reason=f"threshold not valid: {threshold}",
                    fname=path_to_config_file,
                )

        # Finally, store the map file internally after basic validation.
        self.__map = map
