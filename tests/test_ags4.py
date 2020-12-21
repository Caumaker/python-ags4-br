# import sys
# Prepend path so that AGS4.py is loaded from project file
# instead of current installation
# sys.path.insert(0, './')
from python_ags4 import AGS4, __version__
import toml
import pandas as pd


def test_version():
    pyproject = toml.load('pyproject.toml')

    assert __version__ == pyproject['tool']['poetry']['version']


def test_AGS4_to_dict():
    tables, headings = AGS4.AGS4_to_dict('tests/test_data.ags')

    assert tables['PROJ']['PROJ_ID'][2] == '123456'


def test_AGS4_to_dataframe():
    tables, headings = AGS4.AGS4_to_dataframe('tests/test_data.ags')

    assert tables['LOCA'].loc[2, 'LOCA_ID'] == 'Location_1'


def test_convert_to_numeric():
    tables, headings = AGS4.AGS4_to_dataframe('tests/test_data.ags')
    LOCA = AGS4.convert_to_numeric(tables['LOCA'])

    assert LOCA.loc[0, 'LOCA_NATE'] == 100000.01
    assert LOCA.loc[2, 'LOCA_NATN'] == 5000000.20
    assert LOCA.loc[3, 'LOCA_FDEP'] == 50.44


def test_dataframe_to_AGS4():
    tables, headings = AGS4.AGS4_to_dataframe('tests/test_data.ags')

    AGS4.dataframe_to_AGS4(tables, headings, 'tests/test.out')
    AGS4.dataframe_to_AGS4(tables, {}, 'tests/test.out')


def test_convert_to_text():
    tables, headings = AGS4.AGS4_to_dataframe('tests/test_data.ags')
    LOCA_num = AGS4.convert_to_numeric(tables['LOCA'])

    LOCA_txt = AGS4.convert_to_text(LOCA_num, 'tests/DICT.ags')

    assert LOCA_txt.loc[0, 'LOCA_NATE'] == "100000.01"
    assert LOCA_txt.loc[2, 'LOCA_NATN'] == "5000000.20"
    assert LOCA_txt.loc[3, 'LOCA_FDEP'] == "50.44"


def test_AGS4_to_excel():
    AGS4.AGS4_to_excel('tests/test_data.ags', 'tests/test_data.xlsx')

    tables = pd.read_excel('tests/test_data.xlsx', sheet_name=None, engine='openpyxl')

    assert tables['PROJ'].loc[:, 'PROJ_ID'].values[2] == '123456'
    assert tables['LOCA'].loc[:, 'LOCA_ID'].values[1] == 'ID'
    assert tables['LOCA'].loc[:, 'LOCA_ID'].values[2] == 'Location_1'


def test_excel_to_AGS4():
    AGS4.excel_to_AGS4('tests/test_data.xlsx', 'tests/test.out')
