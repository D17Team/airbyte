from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class CustomBaseModel(BaseModel):
    @staticmethod
    def convert_to_float_or_return_zero(value):
        """convert the value to int or return zero

        Args:
            value (_type_): _description_

        Returns:
            _type_: _description_
        """
        try:
            value = float(value)
        except (ValueError, TypeError):
            value = 0
        return value


class ConnatixReportItem(CustomBaseModel):
    domain: str
    customer_id: str
    customer_name: str
    player_id: str
    player_name: str
    device: str
    impressions: float
    revenue: float
    hour: int
    date: datetime  # need to specify the best date with the format

    @staticmethod
    def from_dict(row_dict) -> "ConnatixReportItem":
        """this parse one row of item level from the api to a python object

        Args:
            row_dict (dict): the row of the report

        Returns:
            AdUnitPerHourItem: the python object
        """
        return ConnatixReportItem(
            domain=row_dict.get('Domain / App'),
            customer_id=row_dict.get('Customer Id'),
            customer_name=row_dict.get('Customer Name'),
            player_id=row_dict.get('Player Id'),
            player_name=row_dict.get('Player Name'),
            v_tracker=row_dict.get('v_tracker'),
            device=row_dict.get('Device'),
            impressions=ConnatixReportItem.convert_to_float_or_return_zero(row_dict.get('Ad Impressions')),
            revenue=ConnatixReportItem.convert_to_float_or_return_zero(row_dict.get('Publisher Total Revenue ($)')),
            hour=datetime.strptime(row_dict.get('Hour').lower(), '%d-%b-%Y %H:%M').hour,
            date=datetime.strptime(row_dict.get('Hour').lower(), '%d-%b-%Y %H:%M')
        )

