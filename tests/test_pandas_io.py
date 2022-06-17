import pytest
from .fixtures import *
from featherstore._utils import _sql_str_pattern_to_regexp


@pytest.mark.parametrize("index",
                         [default_index,
                          unsorted_int_index,
                          sorted_datetime_index,
                          unsorted_string_index])
@pytest.mark.parametrize("cols", [5, 1])
def test_pandas_io(store, index, cols):
    # Arrange
    original_df = make_table(index, cols=cols, astype='pandas').squeeze()
    expected = original_df.sort_index()
    partition_size = get_partition_size(original_df)
    table = store.select_table(TABLE_NAME)
    # Act
    table.write(original_df, partition_size=partition_size, warnings='ignore')
    df = table.read_pandas()
    # Assert
    assert df.equals(expected)


def test_that_rangeindex_is_converted_back(store):
    # Arrange
    original_df = make_table(astype="pandas")
    original_df = _convert_rangeindex_to_int64_index(original_df)
    store.write_table(TABLE_NAME, original_df)
    # Act
    df = store.read_pandas(TABLE_NAME)
    # Assert
    assert isinstance(df.index, pd.RangeIndex)
    assert df.index.name == original_df.index.name


def _convert_rangeindex_to_int64_index(df):
    INDEX_NAME = "index"
    int64index = list(df.index)
    df.index = int64index
    df.index.name = INDEX_NAME
    return df


@pytest.mark.parametrize("num_cols", [1, 15])
@pytest.mark.parametrize("cols", [['c0'], ["like", "c?"], ["like", "%1"], ["like", "?1%"]])
def test_filtering_cols(store, num_cols, cols):
    # Arrange
    original_df = make_table(cols=num_cols, astype='pandas')
    expected = _make_expected(original_df, cols=cols)

    partition_size = get_partition_size(original_df)
    table = store.select_table(TABLE_NAME)
    # Act
    table.write(original_df, partition_size=partition_size, warnings='ignore')
    df = table.read_pandas(cols=cols)
    # Assert
    assert df.equals(expected)


@pytest.mark.parametrize(["index", "rows"],
                         [(default_index, pd.Index([0, 1, 27])),
                          (default_index, ['before', 12]),
                          (default_index, ['after', 12]),
                          (default_index, ['between', 12, 27]),
                          (continuous_datetime_index, ["2021-01-07", "2021-01-20"]),
                          (continuous_datetime_index, ['before', pd.Timestamp("2022-02-02")]),
                          (continuous_datetime_index, ['after', pd.Timestamp("2021-01-12")]),
                          (continuous_datetime_index, ['between', "2021-01-12", "2021-01-20"]),
                          (continuous_string_index, ['aa', 'ba']),
                          (continuous_string_index, ["before", 'aj']),
                          (continuous_string_index, ["after", 'aj']),
                          (continuous_string_index, ["between", 'a', 'b']),
                          (continuous_string_index, ["between", 'aj', 'ba']),
                          (sorted_string_index, ["between", 'a', 'f']),
                          ])
def test_filtering_rows(store, index, rows):
    # Arrange
    original_df = make_table(index, astype='pandas')
    expected = _make_expected(original_df, rows=rows)

    partition_size = get_partition_size(original_df)
    table = store.select_table(TABLE_NAME)
    # Act
    table.write(original_df, partition_size=partition_size, warnings='ignore')
    df = table.read_pandas(rows=rows)
    # Assert
    assert df.equals(expected)


def test_filtering_rows_and_cols(store):
    # Arrange
    ROWS = ["between", "aj", "ba"]
    COLS = ["like", "c?"]
    original_df = make_table(continuous_string_index, cols=13, astype='pandas')
    expected = _make_expected(original_df, ROWS, COLS)

    partition_size = get_partition_size(original_df)
    table = store.select_table(TABLE_NAME)
    # Act
    table.write(original_df, partition_size=partition_size, warnings='ignore')
    df = table.read_pandas(rows=ROWS, cols=COLS)
    # Assert
    assert df.equals(expected)


def _make_expected(df, rows=None, cols=None):
    df = df.sort_index()
    df = _filter_cols(df, cols) if cols is not None else df
    df = _filter_rows(df, rows) if rows is not None else df
    return df


def _filter_rows(df, rows):
    keyword = rows[0]
    if keyword == 'before':
        high = rows[1]
        df = df.loc[:high]
    elif keyword == 'after':
        low = rows[1]
        df = df.loc[low:]
    elif keyword == 'between':
        low = rows[1]
        high = rows[2]
        df = df.loc[low:high]
    else:
        if isinstance(rows, pd.Index):
            rows = rows.tolist()
        df = df.loc[rows]
    return df


def _filter_cols(df, cols):
    if cols[0] == 'like':
        pattern = cols[1]
        pattern = _sql_str_pattern_to_regexp(pattern)
        cols_idx = df.columns.str.fullmatch(pattern)
        cols = df.columns[cols_idx]
    df = df[cols]
    return df.squeeze()


def _invalid_index():
    df = make_table(astype='pandas')
    index = np.random.random(size=30)
    df = df.set_index(index)

    args = [TABLE_NAME, df]
    kwargs = dict()
    return args, kwargs


def _duplicate_index():
    df = make_table(astype='pandas', rows=15)
    df1 = make_table(astype='pandas', rows=15)
    df = pd.concat([df, df1])

    args = [TABLE_NAME, df]
    kwargs = dict()
    return args, kwargs


def _index_not_in_cols():
    df = make_table(cols=2, astype='polars')
    df.column_names = ['c0', 'c1']

    args = [TABLE_NAME, df]
    kwargs = dict(index='c2')
    return args, kwargs


def _forbidden_col_name():
    df = make_table(cols=1, astype='pandas')
    df.columns = ['like']

    args = [TABLE_NAME, df]
    kwargs = dict()
    return args, kwargs


def _duplicate_col_names():
    df = make_table(cols=2, astype='pandas')
    df.columns = ['c0', 'c0']

    args = [TABLE_NAME, df]
    kwargs = dict()
    return args, kwargs


def _invalid_warnings_arg():
    df = make_table()
    args = [TABLE_NAME, df]
    kwargs = dict(warnings='abcd')
    return args, kwargs


def _invalid_errors_arg():
    df = make_table()
    args = [TABLE_NAME, df]
    kwargs = dict(errors='abcd')
    return args, kwargs


def _invalid_partition_size_arg():
    df = make_table()
    args = [TABLE_NAME, df]
    kwargs = dict(partition_size='abcd')
    return args, kwargs


@pytest.mark.parametrize(
    ("arguments", "exception"),
    [
        (_invalid_index(), TypeError),
        (_duplicate_index(), IndexError),
        (_index_not_in_cols(), IndexError),
        (_forbidden_col_name(), ValueError),
        (_duplicate_col_names(), IndexError),
        (_invalid_warnings_arg(), ValueError),
        (_invalid_errors_arg(), ValueError),
        (_invalid_partition_size_arg(), TypeError),
    ],
    ids=[
        "_invalid_index",
        "_duplicate_index",
        "_index_not_in_cols",
        "_forbidden_col_name",
        "_duplicate_col_names",
        "_invalid_warnings_arg",
        "_invalid_errors_arg",
        "_invalid_partition_size_arg",
    ],
)
def test_can_write(store, arguments, exception):
    # Arrange
    arguments, kwargs = arguments
    # Act
    with pytest.raises(exception) as e:
        store.write_table(*arguments, **kwargs)
    # Assert
    assert isinstance(e.type(), exception)
