from source_connatix.streams import ConnatixAdRevenueReportStream
from unittest.mock import MagicMock
import pytest
import pandas as pd
from pathlib import Path


class MockResponse:
    def __init__(self, status_code, test_file_path):
        self.json_data = {"data": {"reports": {"downloadReport": {"uriCsvResult": test_file_path}}}}
        self.status_code = status_code
    
    def json(self):
        return self.json_data


@pytest.fixture
def patch_base_class(mocker):
    # Mock abstract methods to enable instantiating abstract class
    mocker.patch.object(ConnatixAdRevenueReportStream, "__abstractmethods__", set())


@pytest.fixture(name="connatix_ad_revenue_report_stream")
def connatix_stream_fixture(patch_base_class):
    config = {"ReportId": "123", "AccountId": "123", "BearerToken": "sample_token"}
    return ConnatixAdRevenueReportStream(config=config, authenticator=MagicMock())


@pytest.fixture(name="test_file_path")
def read_sample_dataframe_test_data():
    """read the csv in data folder from the current file and return the path"""
    current_path = Path(__file__).parent
    return current_path.joinpath("data", "test_data.csv")

@pytest.fixture(name="mock_response")
def mock_response(test_file_path):
    return MockResponse(200, test_file_path)
