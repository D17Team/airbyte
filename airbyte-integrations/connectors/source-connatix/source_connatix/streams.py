from typing import Any, Iterable, Mapping, MutableMapping, Optional, Union, List
import requests
import pandas as pd
import logging
from .data_classes import ConnatixReportItem
from string import Template
from airbyte_cdk.sources.streams.http import HttpStream


logger = logging.getLogger('{}.{}'.format(__name__, 'connatix_report_logger'))


class ConnatixAdRevenueReportStream(HttpStream):
    url_base = "https://conapi.connatix.com/"
    http_method = "POST"

    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__(authenticator=kwargs.get("authenticator"))
        self.report_id = config['ReportId']

    def path(
        self,
        **kwargs
    ) -> str:
        return "graphql"

    def request_headers(self, **kwargs) -> Mapping[str, Any]:
        return {'content-type': 'application/graphql'}

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        # The API does not offer pagination, so we return None to indicate there are no more pages in the response
        return None

    def request_params(
            self,
            **kwargs
    ) -> MutableMapping[str, Any]:
        # The api requires that we include access_key as a query param so we do that in this method

        body = Template('''
            query {
                reports {
                    downloadReport(reportId: "$report_id") {
                    success,
                    uriCsvResult
                    }
                }
            }
            ''').substitute(report_id=self.report_id)
        return {'query': body}

    def generate_item(self, row):
        """from a dict returned by the http request generate item

        Args:
            row (_type_): _description_

        Returns:
            _type_: _description_
        """
        try:
            return ConnatixReportItem.from_dict(row)
        except Exception as e:
            # todo: sometimes null values are returned from the apis, ignoring them now and they will be pulled on the next run
            logger.error(f"error while parsing the row {row}, the error is {e}")
            return None

    def parse_response(
        self,
        response: requests.Response,
        **kwargs
    ) -> Iterable[Mapping]:
        response_data = response.json()
        report_url = response_data['data']['reports']['downloadReport']['uriCsvResult']
        report_df = pd.read_csv(report_url)[:-1]
        report_df = report_df[report_df['Domain / App'].isin(self.app_id_list)]
        for row in report_df.to_dict(orient='records'):
            item = self.generate_item(row)
            yield item.dict()

    @property
    def primary_key(self) -> Optional[Union[str, List[str], List[List[str]]]]:
        """
        :return: string if single primary key,
        list of strings if composite primary key,
        list of list of strings if composite primary key consisting of nested fields.
        If the stream has no primary keys, return None.
        """
        return ["domain", "customer_id", "player_id", "device", "hour", "date"]
