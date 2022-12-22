from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple

import requests
import pandas as pd

from .data_classes import AdRevenuePerHourItem
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
        return {'authorization': f'Bearer {self.bearer_token}',
                'content-type': 'application/graphql'}

    def request_params(
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

    def generate_item(self, row):
        """from a dict returned by the http request generate item

        Args:
            row (_type_): _description_

        Returns:
            _type_: _description_
        """
        # row['customer_name'] = self.customer_name
        try:
            return AdRevenuePerHourItem.from_dict(row)
        except Exception as e:
            # todo: sometimes null values are returned from the apis, ignoring them now and they will be pulled on the next run
            logger.error(f"error while parsing the row {row}, the error is {e}")
            return None

    def parse_response(
        self,
        response: requests.Response,
        stream_state: Mapping[str, Any],
        stream_slice: Mapping[str, Any] = None,
        next_page_token: Mapping[str, Any] = None,
    ) -> Iterable[Mapping]:

        response_data = response.json()
        report_url = response_data['data']['reports']['downloadReport']['uriCsvResult']
        report_df = pd.read_csv(report_url)[:-1]
        for row in report_df.to_dict(orient='records'):
            item = self.generate_item(row)
            yield item.dict()

class SourceConnatix(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        return True, None

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        # NoAuth just means there is no authentication required for this API and is included for completeness.
        # Skip passing an authenticator if no authentication is required.
        # Other authenticators are available for API token-based auth and Oauth2. 
        auth = NoAuth()  
        return [ConnatixReportUrl(config=config, authenticator=auth)]