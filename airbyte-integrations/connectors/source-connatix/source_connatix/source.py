from typing import Any, List, Mapping, Tuple
import logging
from .streams import ConnatixAdRevenueReportStream
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http.requests_native_auth import TokenAuthenticator

logger = logging.getLogger('{}.{}'.format(__name__, 'connatix_report_logger'))


class SourceConnatix(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        # Token implement token base authentication and use it here. # make an api call to check if the credentials are valid
        return True, None

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        auth = TokenAuthenticator(token=config['BearerToken'])
        return [ConnatixAdRevenueReportStream(config=config, authenticator=auth)]
