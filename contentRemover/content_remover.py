import os
import configparser
from plexapi.server import PlexServer
from ast import literal_eval
from datetime import datetime, timedelta


class ContentRemover(object):
    def __init__(self, config_path: str = "./config.yaml") -> None:
        if not isinstance(config_path, str):
            raise TypeError(
                f"config_path must be a string not type {type(config_path)}"
            )
        if not os.path.isfile(config_path):
            raise FileNotFoundError(f"Config file {config_path} not found")
        self._config_path = config_path
        config = configparser.ConfigParser()
        config.read(self._config_path)

        # Get the server
        self._server = PlexServer(
            baseurl=config.get("auth", "server_name"),
            token=config.get("auth", "token"),
        )
        self._account = self._server.myPlexAccount()

        # Get the cleaning settings
        self._movies_settings = {
            "keep_watchlisted_users": literal_eval(
                config.get("movies", "keep_watchlisted_users")
            ),
            "keep_watchlisted": config.getboolean("movies", "keep_watchlisted"),
            "keep_favorite_users": literal_eval(
                config.get("movies", "keep_favorite_users")
            ),
            "keep_favorite": config.getboolean("movies", "keep_favorite"),
            "stale_days": config.getint("movies", "stale_days"),
        }
        self._tv_settings = {
            "keep_watchlisted_users": literal_eval(
                config.get("tv", "keep_watchlisted_users")
            ),
            "keep_watchlisted": config.getboolean("tv", "keep_watchlisted"),
            "keep_favorite_users": literal_eval(
                config.get("tv", "keep_favorite_users")
            ),
            "keep_favorite": config.getboolean("tv", "keep_favorite"),
            "stale_days": config.getint("tv", "stale_days"),
        }

    # Properties
    @property
    def server_reachable(self) -> bool:
        return self._account.ping()

    # Methods
    def clean_stale_content(self, content_ids, library_section) -> None:
        raise NotImplementedError("Method not implemented yet")

    # Support functions
    def _get_stale_content(self, lib_section, settings: dict) -> list[str]:
        """Return a list of stale content ids.

        Content is considered stale is it exceeds the number of days since adding
        and is not watchlisted or favorited by any users.
        """
        thresh_date = datetime.now().date() - timedelta(days=settings["stale_days"])
        stale_content = lib_section.search(
            filter={"lastViewedAt<<": thresh_date.strftime("%Y-%m-%d")}
        )

    def _is_watchlisted(self, item) -> bool:
        """Return True if the item is watchlisted by any user in the keep_watchlisted_users list."""
        for user in item.watchlistedBy:
            if user.title in self._movies_settings["keep_watchlisted_users"]:
                return True
        return False

    def _is_favorited(self, item) -> bool:
        """Return True if the item is favorited by any user in the keep_favorite_users list."""
        for user in item.favoritedBy:
            if user.title in self._movies_settings["keep_favorite_users"]:
                return True
        return False


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "config.ini")
    remover = ContentRemover(config_path=path)
