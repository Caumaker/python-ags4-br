# Copyright (C) 2020  Asitha Senanayake
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# https://github.com/asitha-sena/python-ags4


# Helper functions

def add_error_msg(ags_errors, rule, line, group, desc):
    '''Store AGS4 error in a dictionary.

    Parameters
    ----------
    ags_errors : dict
        Python dictionary to store details of errors in the AGS4 file being checked.
    rule : str
        Name/number of rule infringed.
    line : int
        Line number where error is located.
    group : str
        Name of GROUP in which error is located.
    desc : str
        Description of error.

    Returns
    -------
    dict
        Updated Python dictionary.

    '''

    try:
        ags_errors[rule].append({'line': line, 'group': group, 'desc': desc})

    except KeyError:
        ags_errors[rule] = []
        ags_errors[rule].append({'line': line, 'group': group, 'desc': desc})

    return ags_errors


def combine_DICT_tables(input_files):
    '''Read multiple .ags files and cobmbine the DICT tables.

    If duplicate rows are encountered, the first will be kept and the rest dropped.
    Only 'HEADING','DICT_TYPE','DICT_GRP','DICT_HDNG' columns will be considered
    to determine duplicate rows. Precedence will be given to files in the order in
    which they appear in the input_files list.
    IMPORTANT: The standard AGS4 dictionary has to be the first entry in order for
    order of headings (Rule 7) to checked correctly.

    Parameters
    ----------
    input_files : list
        List of paths to .ags files.

    Returns
    -------
    DataFrame
        Pandas DataFrame with combined DICT tables.
    '''

    from pandas import DataFrame, concat
    from python_ags4.AGS4 import AGS4_to_dataframe
    import sys
    from rich import print as rprint

    # Initialize DataFrame to hold all dictionary entries
    master_DICT = DataFrame()

    for file in input_files:
        try:
            tables, _ = AGS4_to_dataframe(file)

            master_DICT = concat([master_DICT, tables['DICT']])

        except KeyError:
            # KeyError if there is no DICT table in an input file
            rprint(f'[yellow]  WARNING:There is no DICT table in {file}.[/yellow]')

    # Check whether master_DICT is empty
    if master_DICT.shape[0] == 0:
        rprint('[red]  ERROR: No DICT tables available to proceed with checking.[/red]')
        rprint('[red]         Please ensure the input file has a DICT table or provide file with standard AGS4 dictionary.[/red]')
        sys.exit()

    # Drop duplicate entries
    master_DICT.drop_duplicates(['HEADING', 'DICT_TYPE', 'DICT_GRP', 'DICT_HDNG'], keep='first', inplace=True)

    return master_DICT


# Line Rules

def rule_1(line, line_number=0, ags_errors={}):
    '''AGS4 Rule 1: The file shall be entirely composed of ASCII characters.
    '''

    if line.isascii() is False:
        add_error_msg(ags_errors, 'Rule 1', line_number, '', 'Has Non-ASCII character(s).')

    return ags_errors


def rule_2a(line, line_number=0, ags_errors={}):
    '''AGS4 Rule 2a: Each line should be delimited by a carriage return and line feed.
    '''

    if line[-2:] != '\r\n':
        add_error_msg(ags_errors, 'Rule 2a', line_number, '', 'Is not terminated by <CR> and <LF> characters.')

    return ags_errors


def rule_2c(line, line_number=0, ags_errors={}):
    '''AGS4 Rule 2c: HEADING row should fully define the data. Therefore, it should not have duplicate fields.
    '''

    if line.strip('"').startswith('HEADING'):
        temp = line.rstrip().split('","')
        temp = [item.strip('"') for item in temp]

        if len(temp) != len(set(temp)):
            add_error_msg(ags_errors, 'Rule 2c', line_number, '', 'HEADER row has duplicate fields.')

    return ags_errors


def rule_3(line, line_number=0, ags_errors={}):
    '''AGS4 Rule 3: Each line should be start with a data descriptor that defines its contents.
    '''

    if not line.isspace():
        temp = line.rstrip().split('","')
        temp = [item.strip('"') for item in temp]

        if temp[0] not in ['GROUP', 'HEADING', 'TYPE', 'UNIT', 'DATA']:
            add_error_msg(ags_errors, 'Rule 3', line_number, '', 'Does not start with a valid data descriptor.')

    return ags_errors


def rule_4a(line, line_number=0, ags_errors={}):
    '''AGS4 Rule 4a: A GROUP row should only contain the GROUP name as data
    '''

    if line.startswith('"GROUP"'):
        temp = line.rstrip().split('","')
        temp = [item.strip('"') for item in temp]

        if len(temp) > 2:
            add_error_msg(ags_errors, 'Rule 4a', line_number, temp[1], 'GROUP row has more than one field.')
        elif len(temp) < 2:
            add_error_msg(ags_errors, 'Rule 4a', line_number, '', 'GROUP row is malformed.')

    return ags_errors


def rule_4b(line, line_number=0, group='', headings=[], ags_errors={}):
    '''AGS4 Rule 4b: UNIT, TYPE, and DATA rows should have entries defined by the HEADING row.
    '''

    if line.strip('"').startswith(('UNIT', 'TYPE', 'DATA')):
        temp = line.rstrip().split('","')
        temp = [item.strip('"') for item in temp]

        if len(headings) == 0:
            # Avoid repetitions of same error by adding it only it is not already there
            try:

                if not any([(d['group'] == group) and (d['desc'] == 'Headings row missing.') for d in ags_errors['Rule 4b']]):
                    add_error_msg(ags_errors, 'Rule 4b', '-', group, 'Headings row missing.')

            except KeyError:
                add_error_msg(ags_errors, 'Rule 4b', '-', group, 'Headings row missing.')

        elif len(temp) != len(headings):
            add_error_msg(ags_errors, 'Rule 4b', line_number, group, 'Number of fields does not match the HEADING row.')

    return ags_errors


def rule_5(line, line_number=0, ags_errors={}):
    '''AGS4 Rule 5: All fields should be enclosed in double quotes.
    '''

    if not line.isspace():
        if not line.startswith('"') or not line.strip('\r\n').endswith('"'):
            add_error_msg(ags_errors, 'Rule 5', line_number, '', 'Contains fields that are not enclosed in double quotes.')

        elif line.strip('"').startswith(('HEADING', 'UNIT', 'TYPE')):
            # If all fields are enclosed in double quotes then splitting by
            # ',' and '","' will return the same number of filelds
            if len(line.split('","')) != len(line.split(',')):
                add_error_msg(ags_errors, 'Rule 5', line_number, '', 'Contains fields that are not enclosed in double quotes.')

            # This check is not applied to DATA rows as it is possible that commas could be
            # present in fields with string data (i.e TYPE="X"). However, fields in DATA
            # rows that are not enclosed in double quotes will be caught by rule_4b() as
            # they will not be of the same length as the headings row after splitting by '","'.

    elif (line == '\r\n') or (line == '\n'):
        pass

    else:
        add_error_msg(ags_errors, 'Rule 5', line_number, '', 'Contains only spaces.')

    return ags_errors


def rule_6(line, line_number=0, ags_errors={}):
    '''AGS4 Rule 6: All fields should be separated by commas and carriage returns are not
    allowed within a data field.
    '''

    # This will be satisfied if rule_2a, rule_4b and rule_5 are satisfied

    return ags_errors


def rule_19(line, line_number=0, ags_errors={}):
    '''AGS4 Rule 19: GROUP name should consist of four uppercase letters.
    '''

    if line.strip('"').startswith('GROUP'):
        temp = line.rstrip().split('","')
        temp = [item.strip('"') for item in temp]

        if len(temp) >= 2:
            if (len(temp[1]) != 4) or not temp[1].isupper():
                add_error_msg(ags_errors, 'Rule 19', line_number, temp[1], 'GROUP name should consist of four uppercase letters.')

    return ags_errors


def rule_19a(line, line_number=0, group='', ags_errors={}):
    '''AGS4 Rule 19a: HEADING names should consist of uppercase letters.
    '''

    if line.strip('"').startswith('HEADING'):
        temp = line.rstrip().split('","')
        temp = [item.strip('"') for item in temp]

        if len(temp) >= 2:
            for item in temp[1:]:
                if not item.isupper() or (len(item) > 9):
                    add_error_msg(ags_errors, 'Rule 19a', line_number, group, f'Heading {item} should be uppercase and limited to 9 character in length.')

        else:
            add_error_msg(ags_errors, 'Rule 19a', line_number, group, 'Headings row does not seem to have any fields.')

    return ags_errors


def rule_19b(line, line_number=0, group='', ags_errors={}):
    '''AGS4 Rule 19b: HEADING names shall start with the group name followed by an underscore character.
    Where a HEADING referes to an existing HEADING within another GROUP, it shall bear the same name.
    '''

    if line.strip('"').startswith('HEADING'):
        temp = line.rstrip().split('","')
        temp = [item.strip('"') for item in temp]

        if len(temp) >= 2:
            for item in temp[1:]:
                try:
                    if (len(item.split('_')[0]) != 4) or (len(item.split('_')[1]) > 4):
                        add_error_msg(ags_errors, 'Rule 19b', line_number, group, f'Heading {item} should consist of a 4 charater group name and a field name of upto 4 characters.')

                    # TODO: Check whether heading name is present in the standard AGS4 dictionary or in the DICT group in the input file

                except IndexError:
                    add_error_msg(ags_errors, 'Rule 19b', line_number, group, f'Heading {item} should consist of group name and field name separated by "_".')

    return ags_errors


# Group Rules

def rule_2(tables, headings, ags_errors={}):
    '''AGS4 Rule 2: Each file should consist of one or more GROUPs and each GROUP should
    consist of one or more DATA rows.
    '''

    for key in tables:
        # Re-index table to ensure row numbering starts from zero
        tables[key].reset_index(drop=True, inplace=True)

        # Check if there is a UNIT row in the table
        # NOTE: .tolist() used instead of .values to avoid "FutureWarning: elementwise comparison failed."
        #       ref: https://stackoverflow.com/questions/40659212/futurewarning-elementwise-comparison-failed-returning-scalar-but-in-the-futur
        if 'DATA' not in tables[key]['HEADING'].tolist():
            add_error_msg(ags_errors, 'Rule 2', '-', key, 'No DATA rows in group.')

    return ags_errors


def rule_2b(tables, headings, ags_errors={}):
    '''AGS4 Rule 2b: UNIT and TYPE rows should be defined at the start of each GROUP
    '''

    for key in tables:
        # Re-index table to ensure row numbering starts from zero
        tables[key].reset_index(drop=True, inplace=True)

        # Check if there is a UNIT row in the table
        # NOTE: .tolist() used instead of .values to avoid "FutureWarning: elementwise comparison failed."
        #       ref: https://stackoverflow.com/questions/40659212/futurewarning-elementwise-comparison-failed-returning-scalar-but-in-the-futur
        if 'UNIT' not in tables[key]['HEADING'].tolist():
            add_error_msg(ags_errors, 'Rule 2b', '-', key, 'UNIT row missing from group.')

        # Check if the UNIT row is in the correct location within the table
        elif tables[key].loc[0, 'HEADING'] != 'UNIT':
            add_error_msg(ags_errors, 'Rule 2b', '-', key, 'UNIT row is misplaced. It should be immediately below the HEADING row.')

        # Check if there is a TYPE row in the table
        if 'TYPE' not in tables[key]['HEADING'].tolist():
            add_error_msg(ags_errors, 'Rule 2b', '-', key, 'TYPE row missing from group.')

        # Check if the UNIT row is in the correct location within the table
        elif tables[key].loc[1, 'HEADING'] != 'TYPE':
            add_error_msg(ags_errors, 'Rule 2b', '-', key, 'TYPE row is misplaced. It should be immediately below the UNIT row.')

    return ags_errors


def rule_7(headings, dictionary, ags_errors={}):
    '''AGS4 Rule 7: HEADINGs shall be in the order described in the AGS4 dictionary.
    '''

    for key in headings:
        # Extract list of headings defined for the group in the dictionaries
        mask = dictionary.DICT_GRP == key
        reference_headings_list = dictionary.loc[mask, 'DICT_HDNG'].tolist()

        # Verify that all headings names in the group are defined in the dictionaries
        if set(headings[key][1:]).issubset(set(reference_headings_list)):

            # Make a copy of reference list to modify
            temp = reference_headings_list.copy()

            for item in reference_headings_list:
                # Drop heading names that are not used in the file
                if item not in headings[key]:
                    temp.remove(item)

            # Finally compare the two lists. They will be identical only if all element are in the same order
            if not temp == headings[key][1:]:
                msg = f'HEADING names in {key} are not in the order that they are defined in the DICT table and the standard dictionary.'
                add_error_msg(ags_errors, 'Rule 7', '-', key, msg)

        else:
            msg = 'Order of headings could not be checked as one or more fields were not found in either the DICT table or the standard dictionary. Check error log under Rule 9.'
            add_error_msg(ags_errors, 'Rule 7', '-', key, msg)

    return ags_errors


def rule_9(headings, dictionary, ags_errors={}):
    '''AGS4 Rule 9: GROUP and HEADING names will be taken from the standard AGS4 dictionary or
    defined in DICT table in the .ags file.
    '''

    for key in headings:
        # Extract list of headings defined for the group in the dictionaries
        mask = dictionary.DICT_GRP == key
        reference_headings_list = dictionary.loc[mask, 'DICT_HDNG'].tolist()

        for item in headings[key][1:]:
            if item not in reference_headings_list:
                add_error_msg(ags_errors, 'Rule 9', '-', key, f'{item} not found in DICT table or the standard AGS4 dictionary.')

    return ags_errors


def rule_10a(tables, headings, dictionary, ags_errors={}):
    '''AGS4 Rule 10a: KEY fields in a GROUP must be present (even if null). There should not be any dupliate KEY field combinations.
    '''

    for group in tables:
        # Extract KEY fields from dictionary
        mask = (dictionary.DICT_GRP == group) & (dictionary.DICT_STAT.str.contains('key', case=False))
        key_fields = dictionary.loc[mask, 'DICT_HDNG'].tolist()

        # Check for missing KEY fields
        for heading in key_fields:
            if heading not in headings[group]:
                add_error_msg(ags_errors, 'Rule 10a', '-', group, f'Key field {heading} not found.')

        # Check for duplicate KEY field combinations if all KEY fields are present
        if set(key_fields).issubset(set(headings[group])):
            # 'HEADING' column has to added explicity as it is not in the key field list
            key_fields = ['HEADING'] + key_fields

            mask = tables[group].duplicated(key_fields, keep=False)
            duplicate_rows = tables[group].loc[mask, :]

            for i, row in duplicate_rows.iterrows():
                duplicate_key_combo = '|'.join(row[key_fields].tolist())
                add_error_msg(ags_errors, 'Rule 10a', '-', group, f'Duplicate key field combination: {duplicate_key_combo}')

    return ags_errors


def rule_10b(tables, headings, dictionary, ags_errors={}):
    '''AGS4 Rule 10b: REQUIRED fields in a GROUP must be present and cannot be empty.
    '''

    for group in tables:
        # Extract REQUIRED fields from dictionary
        mask = (dictionary.DICT_GRP == group) & (dictionary.DICT_STAT.str.contains('required', case=False))
        required_fields = dictionary.loc[mask, 'DICT_HDNG'].tolist()

        # Check for missing REQUIRED fields
        for heading in required_fields:
            if heading not in headings[group]:
                add_error_msg(ags_errors, 'Rule 10b', '-', group, f'Required field {heading} not found.')

        # Check for missing entries in REQUIRED fields
        # First make copy of table so that it can be modified without unexpected side-effects
        df = tables[group].copy()

        for heading in set(required_fields).intersection(set(headings[group])):

            # Regex ^\s*$ should catch empty entries as well as entries that contain only whitespace
            mask = (df['HEADING'] == 'DATA') & df[heading].str.contains('^\s*$', regex=True)

            # Replace missing/blank entries with '???' so that they can be clearly seen in the output
            df[heading] = df[heading].str.replace('^\s*$', '???', regex=True)
            missing_required_fields = df.loc[mask, :]

            # Add each row with missing entries to the error log
            for i, row in missing_required_fields.iterrows():
                msg = '|'.join(row.tolist())
                add_error_msg(ags_errors, 'Rule 10b', '-', group, f'Empty REQUIRED fields: {msg}')

    return ags_errors


def rule_10c(tables, headings, dictionary, ags_errors={}):
    '''AGS4 Rule 10c: Each DATA row should have a parent entry in the parent GROUP.
    '''

    for group in tables:
        # Find parent group name
        if group not in ['PROJ', 'TRAN', 'ABBR', 'DICT', 'UNIT', 'TYPE', 'LOCA']:

            try:
                mask = (dictionary.DICT_TYPE == 'GROUP') & (dictionary.DICT_GRP == group)
                parent_group = dictionary.loc[mask, 'DICT_PGRP'].to_list()[0]

                # Check whether parent entries exist
                if parent_group == '':
                    add_error_msg(ags_errors, 'Rule 10c', '-', group, 'Parent group left blank in dictionary.')

                else:
                    # Extract KEY fields from dictionary
                    mask = (dictionary.DICT_GRP == parent_group) & (dictionary.DICT_STAT.str.contains('key', case=False))
                    parent_key_fields = dictionary.loc[mask, 'DICT_HDNG'].tolist()
                    parent_df = tables[parent_group].copy()

                    child_df = tables[group].copy()

                    # Check that both child and parent groups have the parent key fields. Otherwise an IndexError will occur
                    # when merge operation is attempted
                    if set(parent_key_fields).issubset(set(headings[group])) and set(parent_key_fields).issubset(headings[parent_group]):
                        # Merge parent and child tables using parent key fields and find entries that not in the
                        # parent table
                        orphan_rows = child_df.merge(parent_df, how='left', on=parent_key_fields, indicator=True).query('''_merge=="left_only"''')

                        for i, row in orphan_rows.iterrows():
                            msg = '|'.join(row[parent_key_fields].tolist())
                            add_error_msg(ags_errors, 'Rule 10a', '-', group, f'Parent entry for line not found in {parent_group}: {msg}')

                    else:
                        msg = f'Could not check parent entries due to missing key fields in {group} or {parent_group}. Check error log under Rule 10a.'
                        add_error_msg(ags_errors, 'Rule 10c', '-', group, msg)
                        # Missing key fields in child and/or parent groups. Rule 10a should catch this error.

            except IndexError:
                add_error_msg(ags_errors, 'Rule 10c', '-', group, 'Could not check parent entries since group definitions not found in standard dictionary or DICT table.')

            except KeyError:
                add_error_msg(ags_errors, 'Rule 10c', '-', group, f'Could not find parent group {parent_group}.')

    return ags_errors


def rule_12(tables, headings, ags_errors={}):
    '''AGS4 Rule 12: Only REQUIRED fields needs to be filled. Others can be null.
    '''

    # This is already checked by Rule 10b. No additional checking necessary

    return ags_errors


def rule_13(tables, headings, ags_errors={}):
    '''AGS4 Rule 13: File shall contain a PROJ group with only DATA. All REQUIRED fields in this
    row should be filled.
    '''

    if 'PROJ' not in tables.keys():
        add_error_msg(ags_errors, 'Rule 13', '-', 'PROJ', 'PROJ table not found.')

    elif tables['PROJ'].loc[tables['PROJ']['HEADING'] == 'DATA', :].shape[0] < 1:
        add_error_msg(ags_errors, 'Rule 13', '-', 'PROJ', 'There should be at least one DATA row in the PROJ table.')

    elif tables['PROJ'].loc[tables['PROJ']['HEADING'] == 'DATA', :].shape[0] > 1:
        add_error_msg(ags_errors, 'Rule 13', '-', 'PROJ', 'There should not be more than one DATA row in the PROJ table.')

    return ags_errors


def rule_14(tables, headings, ags_errors={}):
    '''AGS4 Rule 14: File shall contain a TRAN group with only DATA. All REQUIRED fields in this
    row should be filled.
    '''

    if 'TRAN' not in tables.keys():
        add_error_msg(ags_errors, 'Rule 14', '-', 'TRAN', 'TRAN table not found.')

    elif tables['TRAN'].loc[tables['TRAN']['HEADING'] == 'DATA', :].shape[0] < 1:
        add_error_msg(ags_errors, 'Rule 14', '-', 'TRAN', 'There should be at least one DATA row in the TRAN table.')

    elif tables['TRAN'].loc[tables['TRAN']['HEADING'] == 'DATA', :].shape[0] > 1:
        add_error_msg(ags_errors, 'Rule 14', '-', 'TRAN', 'There should not be more than one DATA row in the TRAN table.')

    return ags_errors


def rule_15(tables, headings, ags_errors={}):
    '''AGS4 Rule 15: The UNIT group shall list all units used in within the data file.
    '''

    try:
        # Load UNIT group
        UNIT = tables['UNIT'].copy()

        unit_list = []

        for group in tables:
            # First make copy of group to avoid potential changes and side-effects
            df = tables[group].copy()

            unit_list += df.loc[df['HEADING'] == 'UNIT', :].values.flatten().tolist()

        try:
            # Check whether entries in the type_list are defined in the UNIT table
            for entry in set(unit_list):
                if entry not in UNIT.loc[UNIT['HEADING'] == 'DATA', 'UNIT_UNIT'].to_list() and entry not in ['', 'UNIT']:
                    add_error_msg(ags_errors, 'Rule 15', '-', '-', f'Unit "{entry}" not found in UNIT table.')

        except KeyError:
            # TYPE_TYPE column missing. Rule 10a and 10b should catch this error
            pass

    except KeyError:
        add_error_msg(ags_errors, 'Rule 15', '-', 'UNIT', 'UNIT table not found.')

    return ags_errors


def rule_16(tables, headings, dictionary, ags_errors={}):
    '''AGS4 Rule 16: Data file shall contain an ABBR group with definitions for all abbreviations used in the file.
    '''

    try:
        # Load ABBR group
        ABBR = tables['ABBR'].copy()

        for group in tables:
            # First make copy of group to avoid potential changes and side-effects
            df = tables[group].copy()

            for heading in headings[group]:
                # Check whether column is of data type PA
                if df.loc[df['HEADING'] == 'TYPE', heading].values[0] == 'PA':
                    # Convert entries in column to a set to drop duplicates
                    entries = set(df.loc[df['HEADING'] == 'DATA', heading].to_list())

                    try:
                        # Extract concatenated entries (if they exist) using TRAN_RCON (it it exists)
                        concatenator = tables['TRAN'].loc[tables['TRAN']['HEADING'] == 'DATA', 'TRAN_RCON'].values[0]
                        entries = [entry.split(concatenator) for entry in entries]

                        # The split operation will result in a list of lists that has to be flattened
                        entries = [item for sublist in entries for item in sublist]

                    except KeyError:
                        # KeyError will be raised if TRAN or TRAN_RCON does not exist
                        pass

                    try:
                        # Check whether entries in the column is defined in the ABBR table
                        for entry in entries:
                            if entry not in ABBR.loc[ABBR['ABBR_HDNG'] == heading, 'ABBR_CODE'].to_list() and entry not in ['']:
                                add_error_msg(ags_errors, 'Rule 16', '-', group, f'"{entry}" under {heading} in {group} not found in ABBR table.')

                    except KeyError:
                        # ABBR_HDNG and/or ABBR_CODE column missing. Rule 10a and 10b should catch this error.
                        pass

    except KeyError:
        # ABBR table is not required if no columns of data type PA are found
        for group in tables:
            # First make copy of group to avoid potential changes and side-effects
            df = tables[group].copy()

            for heading in headings[group]:
                # Check whether column is of data type PA
                if df.loc[df['HEADING'] == 'TYPE', heading].values[0] == 'PA':
                    add_error_msg(ags_errors, 'Rule 16', '-', 'ABBR', 'ABBR table not found.')

                    # Break out of function as soon as first column of data type PA is found to
                    # avoid duplicate error entries
                    return ags_errors

    return ags_errors


def rule_17(tables, headings, dictionary, ags_errors={}):
    '''AGS4 Rule 17: Data file shall contain a TYPE group with definitions for all data types used in the file.
    '''

    try:
        # Load TYPE group
        TYPE = tables['TYPE'].copy()

        type_list = []

        for group in tables:
            # First make copy of group to avoid potential changes and side-effects
            df = tables[group].copy()

            type_list += df.loc[tables[group]['HEADING'] == 'TYPE', :].values.flatten().tolist()

        try:
            # Check whether entries in the type_list are defined in the TYPE table
            for entry in set(type_list):
                if entry not in TYPE.loc[TYPE['HEADING'] == 'DATA', 'TYPE_TYPE'].to_list() and entry not in ['TYPE']:
                    add_error_msg(ags_errors, 'Rule 17', '-', '-', f'Data type "{entry}" not found in TYPE table.')

        except KeyError:
            # TYPE_TYPE column missing. Rule 10a and 10b should catch this error
            pass

    except KeyError:
        add_error_msg(ags_errors, 'Rule 17', '-', 'TYPE', 'TYPE table not found.')

    return ags_errors


def rule_18(tables, headings, ags_errors={}):
    '''AGS4 Rule 18: Data file shall contain a DICT group with definitions for all non-standard headings in the file.

    Note: Check is based on rule_9(). The 'ags_errors' input should be the output from rule_9() in order for this to work.
    '''

    if 'DICT' not in tables.keys() and 'Rule 9' in ags_errors.keys():
        # If Rule 9 has been violated that means a non-standard has been found
        msg = 'DICT table not found. See error log under Rule 9 for a list of non-standard headings that need to be defined in a DICT table.'
        add_error_msg(ags_errors, 'Rule 18', '-', 'DICT', f'{msg}')

    return ags_errors


def rule_19c(tables, headings, dictionary, ags_errors={}):
    '''AGS4 Rule 19b: HEADING names shall start with the group name followed by an underscore character.
    Where a HEADING referes to an existing HEADING within another GROUP, it shall bear the same name.
    '''

    for key in headings:

        for heading in headings[key][1:]:

            try:
                temp = heading.split('_')

                if (temp[0] != key) and heading not in dictionary.DICT_HDNG.to_list():
                    msg = f'{heading} does not start with the name of this group, nor is it defined in another group.'
                    add_error_msg(ags_errors, 'Rule 19b', '-', key, msg)

            except IndexError:
                # Heading does not have an underscore in it. Rule 19b should catch this error.
                pass

    return ags_errors