import pytest
from .fixtures import *


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
    df = df.append(df1)

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
        (_duplicate_col_names(), ValueError),
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


@pytest.mark.parametrize(
    "original_df",
    [
        make_table(astype="pandas"),
        make_table(sorted_datetime_index, astype="pandas"),
        make_table(sorted_string_index, astype="pandas"),
    ],
    ids=["int index", "datetime index", "string index"],
)
def test_sorted_pandas_io(store, original_df):
    # Arrange
    partition_size = get_partition_size(original_df)
    store.write_table(TABLE_NAME,
                      original_df,
                      partition_size=partition_size)
    # Act
    df = store.read_pandas(TABLE_NAME)
    # Assert
    assert df.equals(original_df)


@pytest.mark.parametrize(
    "original_df",
    [
        make_table(unsorted_int_index, astype="pandas"),
        make_table(unsorted_datetime_index, astype="pandas"),
        make_table(unsorted_string_index, astype="pandas"),
    ],
    ids=["int index", "datetime index", "string index"],
)
def test_unsorted_pandas_io(store, original_df):
    # Arrange
    partition_size = get_partition_size(original_df)
    store.write_table(
        TABLE_NAME,
        original_df,
        partition_size=partition_size,
        warnings="ignore",
    )
    # Act
    df = store.read_pandas(TABLE_NAME)
    # Assert
    assert df.equals(original_df.sort_index())
    assert df.index.name == original_df.index.name


def convert_rangeindex_to_int64_index(df):
    INDEX_NAME = "index"
    int64index = list(df.index)
    df.index = int64index
    df.index.name = INDEX_NAME
    return df


def test_that_pandas_rangeindex_is_converted_back(store):
    # Arrange
    original_df = make_table(astype="pandas")
    original_df = convert_rangeindex_to_int64_index(original_df)
    store.write_table(TABLE_NAME, original_df)
    # Act
    df = store.read_pandas(TABLE_NAME)
    # Assert
    assert isinstance(df.index, pd.RangeIndex)
    assert df.index.name == original_df.index.name


def test_filter_columns(store):
    # Arrange
    original_df = make_table(cols=6, astype="pandas")
    cols = ["aapl", "MAST", "test", "4", "TSLA", "Åge"]
    original_df.columns = cols
    store.write_table(TABLE_NAME, original_df)
    # Act
    df = store.read_pandas(TABLE_NAME, cols=["LiKE", "%a%"])
    # Assert
    assert df.columns.tolist() == ["aapl", "MAST", "TSLA"]


@pytest.mark.parametrize(
    ("original_df", "rows"),
    [
        (make_table(astype="pandas"), [2, 6, 9]),
        (make_table(astype="pandas"), pd.Index([2, 6, 9])),
        (
            make_table(hardcoded_datetime_index, astype="pandas"),
            ["2021-01-07", "2021-01-20"],
        ),
        (make_table(hardcoded_string_index,
                    astype="pandas"), ["row00010", "row00003"]),
    ],
)
def test_filtering_rows_with_list(store, original_df, rows):
    # Arrange
    partition_size = get_partition_size(original_df)
    store.write_table(
        TABLE_NAME,
        original_df,
        warnings="ignore",
        partition_size=partition_size,
    )
    expected = original_df.loc[rows, :]
    # Act
    df = store.read_pandas(TABLE_NAME, rows=rows)
    # Assert
    assert df.equals(expected)


@pytest.mark.parametrize(
    ("low", "high"),
    [
        (0, 5),
        (5, 9),
        (7, 13),
        (6, 10),
        (3, 19),
    ],
)
def test_filtering_columns_and_rows_between(store, low, high):
    # Arrange
    COLUMNS = ["c0", "c1"]
    ROWS = ["between", low, high]
    original_df = make_table(astype="pandas")
    original_df.index.name = "index"
    partition_size = get_partition_size(original_df)
    store.write_table(TABLE_NAME,
                      original_df,
                      partition_size=partition_size)
    expected = original_df.loc[low:high, COLUMNS]
    # Act
    df = store.read_pandas(TABLE_NAME, cols=COLUMNS, rows=ROWS)
    # Assert
    assert df.equals(expected)


@pytest.mark.parametrize(
    "high",
    [
        "G",
        "lR",
        "T9est",
    ],
)
def test_filtering_rows_before_low_with_string_index(store, high):
    # Arrange
    ROWS = ["before", high]
    original_df = make_table(sorted_string_index, astype="pandas")
    partition_size = get_partition_size(original_df)
    store.write_table(TABLE_NAME,
                      original_df,
                      partition_size=partition_size)
    expected = original_df.loc[:high, :]
    # Act
    df = store.read_pandas(TABLE_NAME, rows=ROWS)
    # Assert
    assert df.equals(expected)


@pytest.mark.parametrize(
    "low",
    [
        "2021-01-02",
        pd.Timestamp("2021-01-02"),
        "2021-01-05",
        "2021-01-12",
    ],
)
def test_filtering_rows_after_low_with_datetime_index(store, low):
    # Arrange
    ROWS = ["after", low]
    original_df = make_table(hardcoded_datetime_index, astype="pandas")
    partition_size = get_partition_size(original_df)
    store.write_table(TABLE_NAME,
                      original_df,
                      partition_size=partition_size)
    expected = original_df.loc[low:, :]
    # Act
    df = store.read_pandas(TABLE_NAME, rows=ROWS)
    # Assert
    assert df.equals(expected)
