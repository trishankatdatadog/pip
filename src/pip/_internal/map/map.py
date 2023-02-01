import fnmatch
import json
import logging
import os
import re

from typing import Any, Dict, List, Union

from pip._internal.exceptions import MapFileCouldNotBeLoaded

logger = logging.getLogger(__name__)

# https://peps.python.org/pep-0519/#provide-specific-type-hinting-support
PathLike = Union[str, bytes, os.PathLike]

class Mapping:
    def __init__(self, paths: List[str],
                 repositories: List[str],
                 terminating: bool,
                 threshold: int):
        self.paths = paths
        self.repositories = repositories
        self.terminating = terminating
        self.threshold = threshold

class Map:
    """A class that tracks the TUF TAP 4 idea of the map file."""

    def __init__(self, path_to_map_file: PathLike) -> None:
        """Act like 'cue vet map.cue path_to_map_file'."""

        # Read the map file.
        with open(path_to_map_file, 'r') as f:
            _map: Any = json.load(f)

        # The map file must have a top-level repositories object.
        repositories: Dict[str] = _map.get("repositories")
        if not repositories:
            raise MapFileCouldNotBeLoaded(
                reason="Map file missing the 'repositories' key",
                fname=path_to_map_file,
            )

        # The repositories must be a map from names to URLs.
        for name, urls in repositories.items():
            if not isinstance(urls, List):
                raise MapFileCouldNotBeLoaded(
                        reason=f"for repository {name}, urls not a list: {urls}",
                        fname=path_to_map_file,
                    )

            # The URLs must be a list of strings, and point to HTTPS servers.
            for url in urls:
                if not isinstance(url, str) or not re.match(r"(https://)(.+)", url):
                    raise MapFileCouldNotBeLoaded(
                        reason=f"for repository {name}, a url not valid: {url}",
                        fname=path_to_map_file,
                    )

        # The map file must have a top-level mapping object.
        _mappings: List[Dict] = _map.get("mapping")
        if not _mappings:
            raise MapFileCouldNotBeLoaded(
                reason="Map file missing the 'mapping' key",
                fname=path_to_map_file,
            )
        mappings: List[Mapping] = []

        # The mappings must be a list.
        if not isinstance(_mappings, List):
            raise MapFileCouldNotBeLoaded(
                reason=f"mappings not a list: {_mappings}",
                fname=path_to_map_file,
            )

        # Each mapping must be an object.
        for _mapping in _mappings:
            if not isinstance(_mapping, Dict):
                raise MapFileCouldNotBeLoaded(
                    reason=f"in mappings, not a dict: {_mapping}",
                    fname=path_to_map_file,
                )

            # Each mapping must have paths.
            paths: List[str] = _mapping.get("paths")
            # Paths must be a list.
            if not isinstance(paths, List):
                raise MapFileCouldNotBeLoaded(
                    reason=f"paths not a list: {paths}",
                    fname=path_to_map_file,
                )
            # Each path must match a glob-like syntax.
            # TODO: refine syntax.
            for path in paths:
                if not isinstance(path, str) or not re.match(r"[\w/\*]+", path):
                    raise MapFileCouldNotBeLoaded(
                        reason=f"for paths {paths}, a path not valid: {path}",
                        fname=path_to_map_file,
                    )
            # Paths must be unique at least on a surface level.
            if len(paths) < len(set(paths)):
                raise MapFileCouldNotBeLoaded(
                    reason=f"paths not unique: {paths}",
                    fname=path_to_map_file,
                )

            # Repositories must be a list.
            _repositories: List[str] = _mapping.get("repositories")
            if not isinstance(_repositories, List):
                raise MapFileCouldNotBeLoaded(
                    reason=f"repositories not a list: {_repositories}",
                    fname=path_to_map_file,
                )
            # Each repository must have been defined earlier in the top-level map file.
            for repository in _repositories:
                if not isinstance(repository, str) or repository not in repositories:
                    raise MapFileCouldNotBeLoaded(
                        reason=f"for repositories {_repositories}, a repository not valid: {repository}",
                        fname=path_to_map_file,
                    )
            # Repositories must be unique at least on a surface level.
            if len(_repositories) < len(set(_repositories)):
                raise MapFileCouldNotBeLoaded(
                    reason=f"repositories not unique: {_repositories}",
                    fname=path_to_map_file,
                )

            # Should we terminate any matching search here?
            terminating: bool = _mapping.get("terminating", True)
            if not isinstance(terminating, bool):
                raise MapFileCouldNotBeLoaded(
                    reason=f"terminating not boolean: {terminating}",
                    fname=path_to_map_file,
                )

            # How many of these repositories should we use for our search?
            threshold: int = _mapping.get("threshold", len(_repositories))
            if not isinstance(threshold, int) or threshold < 1 or threshold > len(_repositories):
                raise MapFileCouldNotBeLoaded(
                    reason=f"threshold not valid: {threshold}",
                    fname=path_to_map_file,
                )

            # Add to internal list of mappings.
            mapping = Mapping(paths=paths,
                              repositories=_repositories,
                              terminating=terminating,
                              threshold=threshold)
            mappings.append(mapping)

        # Finally, store the map file information internally after basic validation.
        self.__repositories = repositories
        self.__mappings = mappings

    def resolve(self, project_name: str) -> List[str]:
        for mapping in self.__mappings:
            # Does this mapping match the desired project?
            match = False
            logger.debug(f"paths: {mapping.paths}")
            for path in mapping.paths:
                # Note: pattern matching is case-sensitive.
                if fnmatch.fnmatchcase(project_name, path):
                    logger.debug(f"{project_name} matches {path}")
                    match = True
                    break
            if not match:
                logger.debug(f"{project_name} does not match paths; moving on")
                continue

            # FIXME: Implement neat trick of checking that multiple indices
            # return essentially the same Simple API response
            # (i.e., host identical matching requirements).
            logger.debug(f"threshold: {mapping.threshold}")
            if mapping.threshold > 1:
                raise NotImplementedError(
                    f"threshold > {mapping.threshold} not supported yet: {mapping}"
                )

            # Walk through each index for each repository, and check
            # whether there exists a Simple page for this project.
            # NOTE: Presently, to simplify networking code, it is up to
            # LinkCollector to actually perform this check.
            logger.debug(f"repositories: {mapping.repositories}")
            for repository in mapping.repositories:
                indices = self.__repositories[repository]
                for index in indices:
                    logger.debug(f"index: {index}")
                    yield [index]

            # Terminate the search if project has been found,
            # or if it has been called for regardless of failure.
            logger.debug(f"terminating: {mapping.terminating}")
            if mapping.terminating:
                break

        # Found nothing.
        yield []