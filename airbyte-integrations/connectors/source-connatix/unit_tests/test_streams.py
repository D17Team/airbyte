import pytest
from http import HTTPStatus
from unittest.mock import MagicMock
from datetime import datetime
from source_connatix.data_classes import ConnatixReportItem


def test_request_params(patch_base_class, connatix_ad_revenue_report_stream):
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": None}
    expected_params = '''
            query {
                reports {
                    downloadReport(reportId: "123") {
                    success,
                    uriCsvResult
                    }
                }
            }
            '''
    request_params = connatix_ad_revenue_report_stream.request_params(**inputs)
    assert request_params.get("query")
    assert request_params.get("query") == expected_params


def test_next_page_token(patch_base_class, connatix_ad_revenue_report_stream):
    # TODO: replace this with your input parameters
    inputs = {"response": MagicMock()}
    # TODO: replace this with your expected next page token
    expected_token = None
    assert connatix_ad_revenue_report_stream.next_page_token(**inputs) == expected_token


def test_parse_response(patch_base_class, connatix_ad_revenue_report_stream, mock_response):
    inputs = {"response": mock_response}
    response_iter = connatix_ad_revenue_report_stream.parse_response(**inputs)
    for item in response_iter:
        assert isinstance(item, dict)
        assert item["domain"] in connatix_ad_revenue_report_stream.app_id_list
        assert list(item.keys()) == ['domain', 'customer_id', 'customer_name', 'player_id', 'player_name', 'device', 'impressions', 'revenue', 'hour', 'date']        


def test_request_headers(patch_base_class, connatix_ad_revenue_report_stream):
    inputs = {"stream_slice": None, "stream_state": None, "next_page_token": None}
    expected_headers = {'content-type': 'application/graphql'}
    assert connatix_ad_revenue_report_stream.request_headers(**inputs) == expected_headers


def test_http_method(patch_base_class, connatix_ad_revenue_report_stream):
    expected_method = "POST"
    assert connatix_ad_revenue_report_stream.http_method == expected_method


@pytest.mark.parametrize(
    ("http_status", "should_retry"),
    [
        (HTTPStatus.OK, False),
        (HTTPStatus.BAD_REQUEST, False),
        (HTTPStatus.TOO_MANY_REQUESTS, True),
        (HTTPStatus.INTERNAL_SERVER_ERROR, True),
    ],
)
def test_should_retry(patch_base_class, connatix_ad_revenue_report_stream,  http_status, should_retry):
    response_mock = MagicMock()
    response_mock.status_code = http_status
    assert connatix_ad_revenue_report_stream.should_retry(response_mock) == should_retry


def test_backoff_time(patch_base_class, connatix_ad_revenue_report_stream):
    response_mock = MagicMock()
    expected_backoff_time = None
    assert connatix_ad_revenue_report_stream.backoff_time(response_mock) == expected_backoff_time


def test_primary_key(patch_base_class, connatix_ad_revenue_report_stream):
    assert connatix_ad_revenue_report_stream.primary_key == ["domain", "customer_id", "player_id", "device", "hour", "date", "v_tracker"]


def test_generate_items(patch_base_class, connatix_ad_revenue_report_stream):
    """test if the generate item return an object of the class connatix report item with all the attributes.

    Args:
        patch_base_class (_type_): _description_
        connatix_ad_revenue_report_stream (_type_): _description_
    """
    sample_row = {'Player Id': 'fdf64619-f0f7-4020-a8a4-808666d89037',
                  'Domain / App': 'www.qa.on3.com',
                  'Hour': '19-DEC-2022 11:00',
                  'Player Name': 'On3 Stories Player',
                  'Device': 'Desktop',
                  'Customer Id': 'd5c08bb0-aac7-47ee-a414-99e239c45d9d',
                  'Customer Name': 'D17',
                  'Ad Impressions': 0,
                  'Publisher Total Revenue ($)': 0.0}
    generated_item = connatix_ad_revenue_report_stream.generate_item(sample_row)
    assert isinstance(generated_item, ConnatixReportItem)
    assert generated_item.domain == sample_row['Domain / App']
    assert generated_item.customer_id == sample_row['Customer Id']
    assert generated_item.customer_name == sample_row['Customer Name']
    assert generated_item.player_id == sample_row['Player Id']
    assert generated_item.player_name == sample_row['Player Name']
    assert generated_item.device == sample_row['Device']
    assert generated_item.impressions == sample_row['Ad Impressions']
    assert generated_item.revenue == sample_row['Publisher Total Revenue ($)']
    assert generated_item.hour == datetime.strptime(sample_row.get('Hour').lower(), '%d-%b-%Y %H:%M').hour
    assert generated_item.date == datetime.strptime(sample_row.get('Hour').lower(), '%d-%b-%Y %H:%M')


def test_generate_item_raise_error(patch_base_class, connatix_ad_revenue_report_stream):
    """test if the generate item raise an error if the item does not have the required fields

    Args:
        patch_base_class (_type_): _description_
        connatix_ad_revenue_report_stream (_type_): _description_
    """
    fake_row = {'Player Id': 'fdf64619-f0f7-4020-a8a4-808666d89037',
                'Domain / App': 'www.qa.on3.com'}
    assert not connatix_ad_revenue_report_stream.generate_item(fake_row)
