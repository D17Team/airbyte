#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


from abc import ABC, abstractmethod
from typing import Any, Iterable, Mapping, Optional, List
import logging
import time
import requests
from airbyte_cdk.sources.streams import Stream
from googleads import ad_manager
from googleads.errors import AdManagerReportError
from typing import Any, Mapping, Union, List
from csv import DictReader as csv_dict_reader
from .data_classes import AdUnitPerHourItem, AdUnitPerReferrerItem

_CHUNK_SIZE = 16 * 1024


logger = logging.getLogger('{}.{}'.format(__name__, 'google_ad_manager_report_downloader'))


class BaseGoogleAdManagerReportStream(Stream, ABC):
    """
    this is the base stream class used to generate the report
    """

    def __init__(self, google_ad_manager_client: ad_manager.AdManagerClient) -> None:
        super().__init__()
        self.google_ad_manager_client = google_ad_manager_client
        self.report_downloader = self.google_ad_manager_client.GetDataDownloader(version='v202208')
    
    def download_report(self, report_job_id: str, export_format: str, include_report_properties: bool = False,
                        include_totals_row: bool = None, use_gzip_compression: bool = True) -> requests.Response:
        """make an api call to the api with the report job id and return a response containing the report

        Args:
          report_job_id: The ID of the report job to wait for, as a string.
          export_format: The export format for the report file, as a string.
          outfile: A writeable, file-like object to write to.
          include_report_properties: Whether or not to include the report
            properties (e.g. network, user, date generated...)
            in the generated report.
          include_totals_row: Whether or not to include the totals row.
          use_gzip_compression: Whether or not to use gzip compression.
        """
        service = self.report_downloader._GetReportService()

        if include_totals_row is None:  # True unless CSV export if not specified
            include_totals_row = True if export_format != 'CSV_DUMP' else False
        opts = {
            'exportFormat': export_format,
            'includeReportProperties': include_report_properties,
            'includeTotalsRow': include_totals_row,
            'useGzipCompression': use_gzip_compression
        }
        report_url = service.getReportDownloadUrlWithOptions(report_job_id, opts)
        logger.info('Request Summary: Report job ID: %s, %s', report_job_id, opts)

        response = self.report_downloader.url_opener.open(report_url)
        return response

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        """
        this is the base method to parse the api response
        """
        logger.info("start parsing the response stream, should be replaced with logger")

        while True:
            chunk = response.read(_CHUNK_SIZE)
            if not chunk:
                break
            lines = chunk.decode('utf-8')
            reader = csv_dict_reader(lines.splitlines())
            for row in reader:
                item = self.generate_item(row)
                yield item.dict()
    
    def run_report(self, report_job: str) -> str:
        """Runs a report, then waits (blocks) for the report to finish generating.

        Args:
          report_job: The report job to wait for. This may be a dictionary or an
              instance of the SOAP ReportJob class.

        Returns:
          The completed report job's ID as a string.

        Raises:
          An AdManagerReportError if the report job fails to complete.
        """
        service = self.report_downloader._GetReportService()
        report_job_id = service.runReportJob(report_job)['id']

        status = service.getReportJobStatus(report_job_id)

        while status != 'COMPLETED' and status != 'FAILED':
            logger.debug('Report job status: %s', status)
            time.sleep(30)
            status = service.getReportJobStatus(report_job_id)

        if status == 'FAILED':
            raise AdManagerReportError(report_job_id)
        else:
            logger.debug('Report has completed successfully')
            return report_job_id
    
    @staticmethod
    def add_dates_ranges(report_job, start_date, end_date):
        """add the start date and the end date to the report job.

        Args:
            report_job (_type_): _description_
            start_date (_type_): _description_
            end_date (_type_): _description_
        """
        if start_date and end_date:
            report_job['reportQuery']['dateRangeType'] = 'CUSTOM_DATE'
            report_job['reportQuery']['startDate'] = start_date
            report_job['reportQuery']['endDate'] = end_date
        else:
            report_job["reportQuery"]["dateRangeType"] = 'YESTERDAY'
        return report_job
    
    @abstractmethod
    def generate_report_query(self, start_date, end_date):
        raise NotImplementedError("generate_report_query should be implemented")
    
    @abstractmethod
    def generate_item(self, row):
        raise NotImplementedError("generate_item should be implemented")
    
    def get_query(self, report_job: Mapping[str, Any]) -> str:
        """convenience method to the generate the URl

        Args:
            stream_slice (Mapping[str, Any]): _description_

        Returns:
            str: _description_
        """
        return self.run_report(report_job)

    def read_records(self, **kwargs) -> Iterable[Mapping[str, Any]]:
        """the main method that read the records from the report"""
        try:
            report_job_id = self.get_query(self.report_job)
            response = self.download_report(report_job_id, export_format='CSV_DUMP', use_gzip_compression=False)
            # TODO: do something with the response before parsing it
            yield from self.parse_response(response)
        except AdManagerReportError as exc:
            # the error handling should be implemented here, for now raise
            raise exc
    

class AdUnitPerHourReportStream(BaseGoogleAdManagerReportStream):
    """this class generate the report for the Ad unit PerHour

    Args:
        BaseGoogleAdManagerReportStream (_type_): _description_

    Returns:
        _type_: _description_
    """

    def __init__(self, google_ad_manager_client: ad_manager.AdManagerClient, start_date: Mapping, end_date: Mapping, customer_name: str) -> None:
        super().__init__(google_ad_manager_client)
        self.customer_name = customer_name
        self.report_job = self.generate_report_query(start_date=start_date, end_date=end_date)

    def generate_report_query(self, start_date: Mapping, end_date: Mapping) -> Mapping:
        """generate the report query for the ad unit per hour report

        Returns:
            _type_: _description_
        """
        columns = ["TOTAL_INVENTORY_LEVEL_UNFILLED_IMPRESSIONS",
                   "TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS",
                   "TOTAL_LINE_ITEM_LEVEL_CLICKS",
                   "TOTAL_LINE_ITEM_LEVEL_CPM_AND_CPC_REVENUE",
                   "TOTAL_LINE_ITEM_LEVEL_WITHOUT_CPD_AVERAGE_ECPM",
                   "TOTAL_LINE_ITEM_LEVEL_CTR",
                   "TOTAL_CODE_SERVED_COUNT"]
        dimensions = ['AD_UNIT_NAME', 'HOUR', "DATE"]
        report_job = {"reportQuery": {}}
        report_job['reportQuery']['dimensions'] = dimensions
        report_job['reportQuery']['columns'] = columns
        report_job["reportQuery"]["adUnitView"] = 'HIERARCHICAL'
        report_job = self.add_dates_ranges(report_job, start_date, end_date)
        return report_job
    
    def generate_item(self, row):
        """from a dict returned by the http request generate item

        Args:
            row (_type_): _description_

        Returns:
            _type_: _description_
        """
        row['customer_name'] = self.customer_name
        return AdUnitPerHourItem.from_dict(row)
    
    @property
    def primary_key(self) -> Optional[Union[str, List[str], List[List[str]]]]:
        """
        :return: string if single primary key,
        list of strings if composite primary key,
        list of list of strings if composite primary key consisting of nested fields.
        If the stream has no primary keys, return None.
        """
        return ["ad_unit", "hour", "date"]


class AdUnitPerReferrerReportStream(BaseGoogleAdManagerReportStream):
    """this class generate report query for the ad unit per referrer

    Args:
        BaseGoogleAdManagerReportStream (_type_): _description_
    """
    
    def __init__(self, google_ad_manager_client: ad_manager.AdManagerClient, start_date: Mapping, end_date: Mapping, customer_name: str) -> None:
        super().__init__(google_ad_manager_client)
        targeting_values = self.get_custom_targeting_keys_ids("referrer")  # @TODO: I can make this manual instead of getting from the api.
        self.customer_name = customer_name
        self.report_job = self.generate_report_query(targeting_values, start_date=start_date, end_date=end_date)

    def generate_report_query(self, targeting_values: List, start_date: Mapping, end_date: Mapping) -> Mapping:
        """generate the report query for the ad unit per referrer report

        Returns:
            _type_: _description_
        """
        targets_ids = [targeting_value['id'] for targeting_value in targeting_values if targeting_value["id"]]
        targets_ids = ", ".join([str(target_id) for target_id in targets_ids])
        report_job = {"reportQuery": {}}
        custom_traffic_source_columns = [
                "TOTAL_LINE_ITEM_LEVEL_CPM_AND_CPC_REVENUE",
                "TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS",
                "TOTAL_LINE_ITEM_LEVEL_CLICKS",
                "TOTAL_LINE_ITEM_LEVEL_WITHOUT_CPD_AVERAGE_ECPM",
                "TOTAL_ACTIVE_VIEW_VIEWABLE_IMPRESSIONS",
                "TOTAL_ACTIVE_VIEW_MEASURABLE_IMPRESSIONS",
                "TOTAL_ACTIVE_VIEW_ELIGIBLE_IMPRESSIONS",
            ]
        dimensions = ['ADVERTISER_NAME', 'CUSTOM_CRITERIA', 'AD_UNIT_ID', "DATE"]
        report_job["reportQuery"]["dimensions"] = dimensions
        report_job["reportQuery"]["columns"] = custom_traffic_source_columns
        report_job["reportQuery"]["adUnitView"] = 'HIERARCHICAL'
        statement_builder = ad_manager.StatementBuilder(version='v202208')
        statement_builder.Where(f"CUSTOM_TARGETING_VALUE_ID IN ({targets_ids})")
        statement_builder.Limit(None).Offset(None)
        report_job["reportQuery"]["statement"] = statement_builder.ToStatement()
        report_job = self.add_dates_ranges(report_job, start_date, end_date)
        return report_job

    def get_custom_targeting_keys_ids(self, name: str) -> List:
        all_keys = []
        custom_targeting_service = self.google_ad_manager_client.GetService('CustomTargetingService', version='v202208')
        statement_builder = ad_manager.StatementBuilder(version='v202208')
        page_size = ad_manager.SUGGESTED_PAGE_LIMIT
        if name:
            statement_builder = statement_builder.Where("name = :name").WithBindVariable('name', name)
        statement_builder.limit = page_size
        while True:
            response = custom_targeting_service.getCustomTargetingKeysByStatement(statement_builder.ToStatement())
            if 'results' in response and len(response['results']):
                all_keys.extend(response['results'])
                statement_builder.offset += statement_builder.limit
            else:
                break
        customs_target_values = self.get_custom_targeting_values(all_keys)
        return customs_target_values

    def get_custom_targeting_values(self, all_keys: list) -> List:
        """given a list of keys retrieve the custom targeting values

        Args:
            all_keys (list): _description_

        Returns:
            dict: _description_
        """
        targeting_values = list()
        if all_keys:
            statement_builder = ad_manager.StatementBuilder(version='v202208')
            custom_targeting_service = self.google_ad_manager_client.GetService('CustomTargetingService', version='v202208')
            statement = statement_builder.Where("customTargetingKeyId IN ({})".format(",".join([str(key['id']) for key in all_keys])))
            while True:
                response = custom_targeting_service.getCustomTargetingValuesByStatement(statement.ToStatement())
                if 'results' in response and len(response['results']):
                    for custom_targeting_value in response['results']:
                        custom_targe_dict = {"id": custom_targeting_value['id'],
                                             "name": custom_targeting_value['name'],
                                             "displayName": custom_targeting_value['displayName'],
                                             "customTargetingKeyId": custom_targeting_value['customTargetingKeyId']}
                        targeting_values.append(custom_targe_dict)
                    statement.offset += statement.limit
                else:
                    break
        logger.info("found {} custom targeting values".format(len(targeting_values)))
        return targeting_values

    def generate_item(self, row):
        """from a dict returned by the http request generate item

        Args:
            row (_type_): _description_

        Returns:
            _type_: _description_
        """
        row['customer_name'] = self.customer_name
        return AdUnitPerReferrerItem.from_dict(row)

    @property
    def primary_key(self) -> Optional[Union[str, List[str], List[List[str]]]]:
        """
        :return: string if single primary key,
        list of strings if composite primary key,
        list of list of strings if composite primary key consisting of nested fields.
        If the stream has no primary keys, return None.
        """
        return ["ad_unit", "referrer", "date"]

