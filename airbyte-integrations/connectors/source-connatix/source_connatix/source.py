from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.auth import TokenAuthenticator
from airbyte_cdk.sources.streams.http.auth import NoAuth


class ConnatixReportUrl(HttpStream):
    url_base = "https://conapi.connatix.com/"
    http_method = "POST"
    primary_key = None

    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__()
        self.bearer_token = config['BearerToken']
        self.report_id = config['ReportId']

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        # The API does not offer pagination, so we return None to indicate there are no more pages in the response
        return None

    def path(
        self, 
        stream_state: Mapping[str, Any] = None, 
        stream_slice: Mapping[str, Any] = None, 
        next_page_token: Mapping[str, Any] = None
    ) -> str:
        return "graphql"  # TODO

    def request_headers(self, **kwargs) -> Mapping[str, Any]:
        return {'authorization': f'Bearer {self.bearer_token}'}

    def request_json(
            self,
            stream_state: Mapping[str, Any],
            stream_slice: Mapping[str, Any] = None,
            next_page_token: Mapping[str, Any] = None,
    ) -> MutableMapping[str, Any]:
        # The api requires that we include access_key as a query param so we do that in this method

        body = '''
            query {
                reports {
                    downloadReport(reportId: "f356cc84-7fd7-4b20-b56f-17dcc9599c68") {
                    success,
                    uriCsvResult
                    }
                }
            }
            '''
        print(body)
        return {'query': body}

    def parse_response(
        self,
        response: requests.Response,
        stream_state: Mapping[str, Any],
        stream_slice: Mapping[str, Any] = None,
        next_page_token: Mapping[str, Any] = None,
    ) -> Iterable[Mapping]:
        return [response.json()]


class SourceConnatix(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        return True, None

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        # NoAuth just means there is no authentication required for this API and is included for completeness.
        # Skip passing an authenticator if no authentication is required.
        # Other authenticators are available for API token-based auth and Oauth2. 
        auth = NoAuth()  
        return [ConnatixReportUrl(authenticator=auth)]