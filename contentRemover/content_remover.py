import os
import configparser
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
from plexapi.library import LibrarySection
from datetime import datetime, timedelta
from ast import literal_eval
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentRemover(object):
    def __init__(self, config_path: str = "./config.yaml") -> None:
        if not isinstance(config_path, str):
            raise TypeError(
                f"config_path must be a string not type {type(config_path)}"
            )
        if not os.path.isfile(config_path):
            raise FileNotFoundError(f"Config file {config_path} not found")

        # Load the config file
        self._config_path = config_path
        self._config = configparser.ConfigParser()
        self._config.read(self._config_path)

        self._verbose = self._config.getboolean("DEFAULT", "verbose")
        self._dry_run = self._config.getboolean("DEFAULT", "dry_run")

        # Get the server
        self._server = PlexServer(
            baseurl=self._config.get("auth", "server_url"),
            token=self._config.get("auth", "token"),
        )
        self._account: MyPlexAccount = self._server.myPlexAccount()

        # Check if the server is reachable
        if not self.server_reachable:
            logging.error("Plex server is not reachable")
            raise ConnectionError("Plex server is not reachable")

        logging.info("Plex server is reachable")

    # Properties
    @property
    def server_reachable(self) -> bool:
        return self._account.ping()

    @property
    def dry_run(self) -> bool:
        return self._dry_run

    @property
    def verbose(self) -> bool:
        return self._verbose

    # Methods
    def clean_stale_content(self) -> None:
        stale_movies = self._get_stale_content("movies")
        # stale_shows = self._get_stale_content("tv")

        if self._dry_run:
            logging.warning("Dry run enabled, no content will be removed")
            logging.info(f"Stale movies: {[movie.title for movie in stale_movies]}")
        #     # print(f"Stale shows: {[show.title for show in stale_shows]}")
        #     return

    # Support functions
    def _get_stale_content(self, library_name: str) -> list[str]:
        """Return a list of stale content ids.

        Content is considered stale is it exceeds the number of days since adding
        and is not watchlisted or favorited by any users.
        """
        # Get the library section and stale content
        lib_section: LibrarySection = self._server.library.section(library_name)
        thresh_date = datetime.now().date() - timedelta(
            days=self._config.getint(library_name, "stale_days")
        )
        stale_content = lib_section.search(
            filters={"addedAt<<": thresh_date.strftime("%Y-%m-%d")}
        )
        # Filter out watchlisted or favorited content if configured to do so
        if self._config.getboolean(library_name, "keep_watchlisted"):
            stale_content = self._remove_watchlisted(
                user=self._account,
                stale_content=stale_content,
            )

        # Filter out content in collections if configured to do so
        keep_collections = literal_eval(
            self._config.get(library_name, "keep_collections")
        )
        if len(keep_collections) > 0:
            stale_content = self._remove_collections(
                stale_content=stale_content,
                collections=keep_collections,
                lib_section=lib_section,
            )

        return stale_content

    def _remove_watchlisted(self, user: MyPlexAccount, stale_content: list) -> list:
        # Get the watchlisted content
        watchlist = user.watchlist()

        logging.info(f"Found {len(watchlist)} items in the watchlist")

        for item in watchlist:
            result = self._server.library.search(guid=item.guid, libtype=item.type)
            if len(result) == 0:
                # Movie is watchlisted but not in the library
                continue

            logging.info(f"Found watchlisted item {item.title} on server")

            for res in result:
                if res in stale_content:
                    logging.info(
                        f"Removing watchlisted item {res.title} from stale list"
                    )
                    stale_content.remove(res)

        return stale_content

    def _remove_collections(
        self, stale_content: list, collections: list[int], lib_section: LibrarySection
    ) -> list:
        logging.info(f"Checking {len(collections)} collections to keep")

        # Get the collection items
        in_collections = (
            []
        )  # the collection items that are actually in these collections

        for collection in collections:
            # Get the collection
            coll = lib_section.collection(title=collection)
            if not coll:
                logging.info(f"Collection {collection} not found")
                continue

            # Add the items in the collection to the list
            for item in coll.items():
                # Only add if its not in the collections summary already
                if item not in in_collections:
                    in_collections.append(item)

        # Remove the collection items from the stale content
        filtered = []
        for item in stale_content:
            if item not in in_collections:
                filtered.append(item)
                logging.info(f"Removing item {item.title} from stale list")

        return filtered


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "config.ini")
    remover = ContentRemover(config_path=path)
    remover.clean_stale_content()

    # section: LibrarySection = remover._server.library.section("movies")
    # print(section.collections())
    # print("---- results ----")
    # print(section.search(guid=678))
